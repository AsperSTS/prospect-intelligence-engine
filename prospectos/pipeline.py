"""Orquesta pull → análisis (grupos, fit, prioridad, hipótesis) → enriquecimiento web sobre la base SQLite."""
import json
import sqlite3
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta

from . import acciones, config, contacto, db, enrich, giros, grupos, mensajes, scoring, senales, texto
from .config import ENTIDADES, ESTRATOS, SECTORES, get_token
from .denue import DenueClient, Establecimiento

LAT = (14.0, 33.5)     # límites razonables de México; fuera de rango -> NULL
LON = (-119.0, -86.0)


def _num(valor: str, rango: tuple[float, float]) -> float | None:
    try:
        x = float(valor)
    except (TypeError, ValueError):
        return None
    return x if rango[0] <= x <= rango[1] else None


def _fila(e: Establecimiento, entidad_cod: str) -> dict:
    partes = [p.strip() for p in e.ubicacion.split(",")]
    g = giros.clasificar(e.clase_id, e.clase_actividad)
    tel = contacto.telefono_mx(e.telefono)
    return {
        "id": e.id, "nombre": e.nombre.strip(), "razon_social": e.razon_social.strip(), "giro": g.giro,
        "clase_actividad": e.clase_actividad, "clase_id": e.clase_id, "rama_id": e.rama_id, "subrama_id": e.subrama_id,
        "estrato": e.estrato, "tipo_establecimiento": e.tipo_establecimiento.strip(),
        "corredor_nombre": e.corredor_nombre.strip(), "corredor_tipo": e.corredor_tipo.strip(),
        "entidad": ENTIDADES.get(entidad_cod, entidad_cod),
        "municipio": partes[-2].title() if len(partes) >= 2 else "", "localidad": partes[0].title() if partes and partes[0] else "",
        "direccion": " ".join(x for x in (e.tipo_vialidad, e.calle, e.num_exterior, e.colonia) if x).strip(),
        "calle": e.calle.strip(), "num_exterior": e.num_exterior.strip(), "num_interior": e.num_interior.strip(),
        "edificio": e.edificio.strip(), "numero_local": e.numero_local.strip(), "cp": e.cp,
        "telefono": tel or e.telefono.strip(), "correo": e.correo.strip().lower(), "sitio": e.sitio.strip(),
        "dominio": contacto.dominio(e.sitio), "latitud": _num(e.latitud, LAT), "longitud": _num(e.longitud, LON),
        "fecha_alta": e.fecha_alta,   # alta/incorporación reportada en DENUE; NO es fecha de fundación
    }


def pull(entidades: list[str], estratos: list[str] | None = None, limite: int | None = None, log=print) -> int:
    estratos = estratos or list(ESTRATOS)
    cliente = DenueClient(get_token())
    total_nuevos = 0
    try:
        with db.conectar() as con:
            for ent in entidades:
                for sector, sub in SECTORES:
                    for est in estratos:
                        filas = [_fila(e, ent) for e in cliente.buscar(ent, sector, sub, est, limite)]
                        nuevos, _ = db.upsert_denue(con, filas)
                        con.commit()
                        total_nuevos += nuevos
                        log(f"{ENTIDADES.get(ent, ent)} sector {sector}/{sub} estrato {ESTRATOS[est]}: {len(filas)} leídos, {nuevos} nuevos")
    finally:
        cliente.close()
    return total_nuevos


def _contexto(con: sqlite3.Connection):
    filas = [dict(r) for r in con.execute("SELECT * FROM prospectos")]
    sen = defaultdict(list)
    for s in con.execute("SELECT prospect_id, signal_type, signal_text, signal_source_url FROM web_signals"):
        sen[s["prospect_id"]].append(dict(s))
    return filas, sen


def analizar_todos() -> int:
    """Recalcula grupos, fit, prioridad, hipótesis, siguiente acción y mensaje sugerido de todos los registros."""
    with db.conectar() as con:
        for sid, t in con.execute("SELECT id, signal_text FROM web_signals").fetchall():   # normaliza evidencia guardada antes de la limpieza
            limpio = texto.sin_ruido_de_menu(texto.limpiar(t))
            if limpio != t:
                con.execute("UPDATE web_signals SET signal_text=? WHERE id=?", (limpio, sid))
        filas, sen = _contexto(con)
        gmap = grupos.agrupar(filas)
        contactados = {gmap[r["id"]]["group_key"] for r in filas if (r.get("etapa_max") or 0) >= 1 and gmap[r["id"]]["possible_chain"]}
        for r in filas:
            r.update(gmap[r["id"]])
            g = giros.clasificar(r["clase_id"] or "", r["clase_actividad"] or "")
            r["giro"], r["giro_display"] = g.giro, g.display
            tipos = [s["signal_type"] for s in sen[r["id"]]]
            fit_score, fit_items = scoring.fit(r, g, tipos)
            prio, prio_items, _ = scoring.priority(r, fit_score, tipos, r["group_key"] in contactados)
            hip, base, conf = giros.hipotesis(g, [senales.etiqueta(t) for t in senales.relacionadas(tipos)[:3]])
            accion = acciones.recommend_next_action(r, fit_score, bool(tipos))
            wa = mensajes.primer_contacto(r, "whatsapp", sen[r["id"]])
            db.guardar_analisis(
                con, r["id"], giro=g.giro, giro_display=g.display, fit_score=fit_score, fit_breakdown=fit_items,
                priority_score=prio, priority_breakdown=prio_items, hypothesis_text=hip, hypothesis_basis=base,
                hypothesis_confidence=conf, score=prio, canal=accion["action"], mensaje=wa.cuerpo, variante=wa.variante, **gmap[r["id"]])
        return len(filas)


def refrescar_prioridades() -> int:
    """Recalcula solo prioridad y siguiente acción (dependen del estado y de la fecha: un seguimiento vence sin que nadie escriba).
    Escribe únicamente las filas que cambiaron. Devuelve cuántas."""
    with db.conectar() as con:
        filas, sen = _contexto(con)
        contactados = {r["group_key"] for r in filas if (r.get("etapa_max") or 0) >= 1 and r.get("possible_chain")}
        cambios = []
        for r in filas:
            tipos = [x["signal_type"] for x in sen[r["id"]]]
            fit_score = r.get("fit_score") or 0
            prio, items, _ = scoring.priority(r, fit_score, tipos, r.get("group_key") in contactados)
            accion = acciones.recommend_next_action(r, fit_score, bool(tipos))["action"]
            items_json = json.dumps(items, ensure_ascii=False)
            if prio != r.get("priority_score") or accion != r.get("canal") or items_json != r.get("priority_breakdown"):
                cambios.append((prio, items_json, prio, accion, r["id"]))
        con.executemany("UPDATE prospectos SET priority_score=?, priority_breakdown=?, score=?, canal=? WHERE id=?", cambios)
        return len(cambios)


def _aplicar(con: sqlite3.Connection, dominio: str, res: dict) -> int:
    ahora = datetime.now().isoformat(timespec="seconds")
    if res["status"] != "ok":   # fallo de red/bloqueo: se cachea el intento pero no se pierden datos previos
        con.execute("INSERT OR REPLACE INTO web_cache (domain, checked_at, status, pages_fetched) VALUES (?,?,?,0)", (dominio, ahora, res["status"]))
        return 0
    ids = [r[0] for r in con.execute("SELECT id FROM prospectos WHERE dominio=?", (dominio,))]
    for pid in ids:
        db.guardar_senales(con, pid, res["signals"])
        con.execute("UPDATE prospectos SET source_website=1, website_checked_at=?, enriquecido_en=date('now'),"
                    " correo_web=CASE WHEN ?<>'' THEN ? ELSE correo_web END, whatsapp=CASE WHEN ?<>'' THEN ? ELSE whatsapp END WHERE id=?",
                    (ahora, res["email"], res["email"], res["whatsapp"], res["whatsapp"], pid))
    con.execute("INSERT OR REPLACE INTO web_cache (domain, checked_at, status, pages_fetched, email, whatsapp) VALUES (?,?,?,?,?,?)",
                (dominio, ahora, res["status"], res["pages"], res["email"], res["whatsapp"]))
    return len(ids)


def enriquecer_pendientes(limite: int = 100, forzar: bool = False, log=print) -> int:
    """Visita hasta `limite` dominios con último chequeo de más de REENRICH_AFTER_DAYS (o nunca). Una visita por dominio."""
    corte = (datetime.now() - timedelta(days=config.REENRICH_AFTER_DAYS)).isoformat(timespec="seconds")
    with db.conectar() as con:
        q = ("SELECT p.dominio, max(p.fit_score) f FROM prospectos p LEFT JOIN web_cache c ON c.domain=p.dominio"
             " WHERE p.dominio IS NOT NULL AND p.estado NOT IN ('descartado','no_interesado','sin_respuesta','cliente')")
        if not forzar:
            q += " AND (c.checked_at IS NULL OR c.checked_at < ?)"
        q += " GROUP BY p.dominio ORDER BY f DESC LIMIT ?"
        dominios = [r[0] for r in con.execute(q, ([corte] if not forzar else []) + [limite])]
        if not dominios:
            log("sin dominios pendientes")
            return 0
        with enrich.nuevo_cliente() as http, ThreadPoolExecutor(max_workers=8) as ex:
            resultados = list(ex.map(lambda d: (d, enrich.enriquecer_dominio(http, d)), dominios))
        for dominio, res in resultados:
            _aplicar(con, dominio, res)
        con.commit()
        ok = sum(1 for _, r in resultados if r["status"] == "ok")
        log(f"dominios visitados: {len(resultados)} · con respuesta: {ok} · señales: {sum(len(r['signals']) for _, r in resultados)}")
        return len(resultados)

