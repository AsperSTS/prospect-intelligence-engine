"""Fit Score y Priority Score, ambos explicables (cada punto tiene motivo).

FIT        ¿Qué tan compatible es el establecimiento con lo que Yael puede vender?  (0-100, cambia poco)
PRIORIDAD  ¿Qué tan conveniente es revisarlo/contactarlo HOY?                        (0-100, cambia con el estado)

Son reglas internas de priorización, NO probabilidades de compra. Hasta tener contactos reales no hay calibración.
"""
from datetime import date, datetime

from . import contacto, giros, senales
from .db import CERRADOS

ESTRATO_PTS = {"11 a 30 personas": 14, "31 a 50 personas": 20, "51 a 100 personas": 20}
FIT_PESO_EN_PRIORIDAD = 0.35


def _item(clave: str, etiqueta: str, pts: int, maximo: int, nota: str = "") -> dict:
    return {"clave": clave, "etiqueta": etiqueta, "pts": pts, "max": maximo, "nota": nota}


INDUSTRIALES = ("parque industrial", "zona industrial", "ciudad industrial", "corredor industrial")
GENERICOS = ("sin nombre", "sin nombre.", "")


def _corredor(nombre: str, tipo: str) -> tuple[int, str]:
    """DENUE usa 'corredor' también para plazas, mercados, hoteles y hospitales: solo lo industrial suma.
    15 = corredor industrial identificado (tipo industrial + nombre) · 10 = zona/parque compatible · 0 = sin dato o no industrial."""
    n, t = nombre.strip().lower(), tipo.strip().lower()
    tipo_ind = t in INDUSTRIALES
    nombre_ind = "industrial" in n or n.startswith("parque ") or "ciudad industrial" in n
    nombre_ok = n not in GENERICOS
    if tipo_ind and nombre_ok:
        return 15, f"{tipo.title()}: {nombre.title()}"
    if tipo_ind or nombre_ind:
        return 10, f"{tipo.title() or 'Zona industrial'} (sin nombre específico)" if not nombre_ok else f"{nombre.title()} ({tipo.title() or 'nombre indica zona industrial'})"
    if t or n:
        return 0, f"{(tipo or nombre).title()}: no industrial"
    return 0, "sin dato"


def fit(r: dict, g: giros.Giro, tipos_senal: list[str]) -> tuple[int, list[dict]]:
    estrato = ESTRATO_PTS.get(r.get("estrato", ""), 4)
    tipo = (r.get("tipo_establecimiento") or "").strip().lower()
    tipo_pts, tipo_nota = (10, "fijo") if tipo == "fijo" else (4, "sin dato") if not tipo else (0, f"{tipo}: poco compatible")
    corr_pts, corr_nota = _corredor(r.get("corredor_nombre") or "", r.get("corredor_tipo") or "")
    rel = senales.relacionadas(tipos_senal)
    sen_pts = min(10, 3 * len(set(rel)))
    items = [
        _item("giro", "Giro", g.fit, 25, g.giro),
        _item("estrato", "Tamaño (estrato)", estrato, 20, r.get("estrato", "sin dato")),
        _item("tipo", "Tipo de establecimiento", tipo_pts, 10, tipo_nota),
        _item("corredor", "Corredor industrial", corr_pts, 15, corr_nota),
        _item("complejidad", "Complejidad operativa probable", g.complejidad, 20, "regla por giro/SCIAN, no un hecho"),
        _item("senales", "Señales web relacionadas", sen_pts, 10, ", ".join(senales.etiqueta(t) for t in sorted(set(rel))) or "ninguna"),
    ]
    return sum(i["pts"] for i in items), items


def _dias_desde(valor: str | None, hoy: date) -> int | None:
    if not valor:
        return None
    try:
        return (hoy - datetime.fromisoformat(str(valor)[:19]).date()).days
    except ValueError:
        return None


def _canales(r: dict) -> tuple[bool, bool, bool]:
    email = contacto.email_valido(r.get("correo") or "") or contacto.email_valido(r.get("correo_web") or "")
    tel = bool(contacto.telefono_mx(r.get("telefono") or "") or contacto.telefono_mx(r.get("whatsapp") or ""))
    web = bool((r.get("sitio") or "").strip())
    return email, tel, web


def priority(r: dict, fit_score: int, tipos_senal: list[str], grupo_contactado: bool = False, hoy: date | None = None) -> tuple[int, list[dict], bool]:
    """Devuelve (puntaje, desglose, excluido). `excluido` = cerrado/descartado: no debe aparecer en la cola."""
    hoy = hoy or date.today()
    estado = r.get("estado") or "nuevo"
    if estado in CERRADOS:
        return 0, [_item("estado", "Estado", 0, 0, f"{estado}: fuera de la cola")], True

    email, tel, web = _canales(r)
    n_canales = sum((email, tel, web))
    contactabilidad = [
        _item("email", "Email válido", 10 if email else 0, 10),
        _item("telefono", "Teléfono con formato válido", 10 if tel else 0, 10, "formato, no implica móvil"),
        _item("web", "Sitio web", 5 if web else 0, 5),
        _item("multi", "Más de un canal útil", 5 if n_canales >= 2 else 0, 5),
    ]
    cont = sum(i["pts"] for i in contactabilidad)

    tipos = set(tipos_senal)
    ev1 = 10 if tipos else 0
    ev2 = 10 if senales.relacionadas(tipos) else 0

    # estado operativo (se acota a [-20, +15])
    est, motivos = 0, []
    due = r.get("proximo_seguimiento") and str(r["proximo_seguimiento"]) <= hoy.isoformat()
    if estado == "nuevo":
        est += 5; motivos.append("nuevo, sin revisar")
    elif estado == "contactado":
        if due:
            est += 15; motivos.append("seguimiento vencido")
        else:
            est -= 8; motivos.append("contactado, en secuencia")
    elif estado in ("respondio", "respuesta_positiva"):
        est += 15; motivos.append("respondió: requiere acción")
    elif estado in ("reunion", "propuesta"):
        est += 10; motivos.append(f"{estado}: requiere acción")
    if estado in ("nuevo", "revisado") and r.get("possible_chain") and grupo_contactado:
        est -= 15; motivos.append("posible grupo ya contactado")
    if n_canales == 0:
        est -= 10; motivos.append("sin canal de contacto")
    est = max(-20, min(15, est))

    dias_web = _dias_desde(r.get("website_checked_at"), hoy)
    dias_reg = _dias_desde(r.get("creado_en"), hoy)
    fresc = (3 if dias_web is not None and dias_web <= 30 else 0) + (2 if dias_reg is not None and dias_reg <= 14 else 0)

    pond = round(fit_score * FIT_PESO_EN_PRIORIDAD)
    items = [
        _item("fit", "Fit ponderado", pond, 35, f"fit {fit_score} × {FIT_PESO_EN_PRIORIDAD}"),
        _item("contacto", "Contacto", cont, 30, "email · teléfono · web · multicanal"),
        _item("contexto", "Contexto web", ev1 + ev2, 20, "señal concreta + señal relacionada"),
        _item("estado", "Estado operativo", est, 15, "; ".join(motivos) or "sin ajuste"),
        _item("frescura", "Frescura", fresc, 5, "enriquecimiento ≤30 días / registro ≤14 días"),
    ]
    bruto = sum(i["pts"] for i in items)
    total = max(0, min(100, bruto))
    if total != bruto:
        items.append(_item("limite", "Límite de la escala", total - bruto, abs(total - bruto),
                           f"Ajuste del subtotal {bruto} al rango 0–100"))
    return total, items, False
