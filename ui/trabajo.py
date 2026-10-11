"""Mesa de trabajo de tres columnas hecha de islas: cola · contexto · acción.
Modos: 'hoy' (primer contacto), 'seg' (seguimientos), 'resp' (conversaciones).

- Cola: solo selecciona. Cada prospecto es una tarjeta separada con la información para elegir; sin tooltips ni efectos hover.
- Contexto (protagonista): nombre y puntajes arriba y 3 pestañas como máximo (Perfil · Evidencia · Puntajes e historial). Cada pestaña es una
  rejilla de islas que llena la altura disponible.
- Acción: el mensaje COMPLETO y editable ocupa el espacio sobrante (nunca se parte en páginas); el registro está siempre visible.
Las columnas miden la altura de la pantalla (CSS en theme.py); solo scrollea lo que de verdad no cabe.
"""
import json
from collections.abc import Callable
from html import escape

import pandas as pd
import streamlit as st

from prospectos import acciones, config, contacto, db, enrich, mensajes, senales
from . import copiar, datos, theme

PROPORCIONES = [0.8, 2.7, 1.5]   # solo referencia: el ancho real lo fija la rejilla CSS (cola ≈ 15 % · contexto ≈ 56 % · acción ≈ 29 %)
PAGE_SIZE = 60

RESPUESTA_ROTULOS = {"interesado": "Interesado", "redirigido": "Me redirigió a otra persona", "pregunta": "Hizo una pregunta",
                     "no_interesado": "No le interesa", "ya_tienen_solucion": "Ya tienen solución", "no_es_prioridad": "No es prioridad",
                     "numero_incorrecto": "Número incorrecto", "correo_rebotado": "Correo rebotado", "otro": "Otra respuesta"}
ESTADO_ROTULOS = {"nuevo": "Nuevo", "revisado": "Revisado", "contactado": "Contactado", "respondio": "Respondió",
                  "respuesta_positiva": "Respuesta positiva", "reunion": "Reunión", "propuesta": "Propuesta", "cliente": "Cliente",
                  "no_interesado": "No interesado", "sin_respuesta": "Sin respuesta", "descartado": "Descartado"}
v = datos.vacio
GIRO_CORTO = {"Constructora / contratista": "Constructora", "Comercializadora B2B": "Comercializadora", "Equipo de transporte": "Eq. transporte"}


def _mutar(fn, *a, **k):
    with db.conectar() as con:
        fn(con, *a, **k)
    datos.limpiar()
    st.rerun()


def _md(html: str) -> None:
    st.html(html)


def _contactos_cola(r) -> str:
    c = []
    if contacto.email_valido(v(r["correo_web"])) or contacto.email_valido(v(r["correo"])):
        c.append("Correo")
    if contacto.telefono_mx(v(r["telefono"])) or contacto.telefono_mx(v(r["whatsapp"])):
        c.append("Tel")
    if v(r["sitio"]):
        c.append("Web")
    return " · ".join(c) or "Sin contacto"


def _item_cola(r, seleccionado: bool, prefijo: str) -> bool:
    """Tarjeta: nombre · giro y municipio · FIT/PRIO (y grupo) · canales disponibles. Sin tooltip."""
    nombre = mensajes.limpiar_nombre(v(r["nombre"]))
    giro = GIRO_CORTO.get(v(r["giro"]), v(r["giro"]))
    grupo = " · grupo" if r["possible_chain"] else ""
    etiqueta = (f"**{nombre}**\n\n{giro} · {v(r['municipio'])}\n\n"
                f"FIT {int(r['fit_score'] or 0)} · PRIO {int(r['priority_score'] or 0)}{grupo}\n\n{_contactos_cola(r)}")
    return st.button(etiqueta, key=f"{prefijo}_sel_{r['id']}", type="primary" if seleccionado else "secondary", width="stretch")


def _porque_si(fit_items: list[dict]) -> str:
    textos = {"giro": "Giro", "estrato": "Tamaño", "tipo": "Fijo", "corredor": "Corredor", "complejidad": "Complejidad", "senales": "Señales web"}
    filas = [f'<div><span class="ok">✓</span> {escape(textos.get(i["clave"], i["etiqueta"]))}</div>' for i in fit_items if i["max"] and i["pts"] >= 0.6 * i["max"]]
    return f'<div class="lista">{"".join(filas) or "<div class=sub>Sin motivos fuertes</div>"}</div>'


def _historial_html(hist: list[dict]) -> str:
    if not hist:
        return '<div class="sub">Sin interacciones registradas todavía.</div>'
    filas = []
    for h in reversed(hist):
        tipo = {"contacto": "Primer contacto", "seguimiento": f"Seguimiento {h['sequence_step']}", "respuesta": "Respuesta"}.get(h["interaction_type"], h["interaction_type"])
        extra = f" · {RESPUESTA_ROTULOS.get(h['response_type'], h['response_type'])}" if v(h["response_type"]) else ""
        cuerpo = f'<br><span class="sub">{escape(v(h["message_rendered"])[:200])}</span>' if v(h["message_rendered"]) else ""
        nota = f'<br><span class="sub">Nota: {escape(v(h["notes"]))}</span>' if v(h["notes"]) else ""
        filas.append(f'<div class="dato"><span class="k">{escape(str(h["created_at"])[:16])}</span>'
                     f'<span class="v">{escape(tipo)} · {escape(v(h["channel"]))} {escape(v(h["template_variant"]))}{escape(extra)}{cuerpo}{nota}</span></div>')
    return "".join(filas)


def _medidor(etiqueta: str, valor: int, ayuda: str) -> str:
    _, tono = theme.nivel(valor)
    return (f'<div class="medidor {tono}" title="{escape(ayuda)}"><div class="t">{escape(etiqueta)}</div><div class="n">{int(valor)}</div>'
            f'<div class="bar"><i style="width:{max(0, min(100, int(valor)))}%"></i></div></div>')


def _enlace_sitio(sitio: str) -> str:
    url = enrich.normalizar_url(sitio)
    if not url:
        return escape(sitio) if sitio else "—"
    return f'<a href="{escape(url)}" target="_blank" rel="noopener noreferrer">{escape(sitio.lower())}</a>'


def _contactos_html(r) -> str:
    tel, wa = contacto.telefono_legible(v(r["telefono"])), contacto.telefono_legible(v(r["whatsapp"]))
    correos = []
    for campo, origen in (("correo", "DENUE"), ("correo_web", "sitio web")):
        c = v(r[campo])
        if c and c not in [x[0] for x in correos]:
            correos.append((c, origen))
    email = "<br>".join(f'{escape(c)} <span class="origen">{escape(o)}</span>' for c, o in correos) or "—"
    filas = theme.dato("Teléfono", tel or "Sin dato")
    if wa and wa != tel:
        filas += theme.dato("WhatsApp web", wa)
    filas += f'<div class="dato"><span class="k">Correo</span><span class="v">{email}</span></div>'
    filas += f'<div class="dato"><span class="k">Sitio web</span><span class="v">{_enlace_sitio(v(r["sitio"]))}</span></div>'
    return f'<div class="contactos">{filas}</div>'


def _cita_html(s: dict, max_chars: int = 170) -> str:
    """Cita con la evidencia recortada y la fuente abreviada (el enlace completo sigue siendo clicable)."""
    texto = v(s["signal_text"])
    texto = texto if len(texto) <= max_chars else texto[: max_chars - 1].rsplit(" ", 1)[0] + "…"
    url = v(s["signal_source_url"])
    corto = url.removeprefix("https://").removeprefix("http://").removeprefix("www.")
    corto = corto if len(corto) <= 38 else corto[:37] + "…"
    return (f'<div class="cita">“{escape(texto)}”<div class="hip-meta">{escape(_etiqueta_senal(s["signal_type"]))} · '
            f'<a href="{escape(url)}" target="_blank" rel="noopener noreferrer" title="{escape(url)}">{escape(corto)}</a></div></div>')


def _etiqueta_senal(tipo: str) -> str:
    return senales.SENALES.get(tipo, (None, tipo))[1]


def _contexto(r, sen: list[dict], hist: list[dict], df: pd.DataFrame, modo: str) -> None:
    nombre = mensajes.limpiar_nombre(v(r["nombre"]))
    fit_s, pri_s = int(r["fit_score"] or 0), int(r["priority_score"] or 0)
    fit_items = json.loads(v(r["fit_breakdown"]) or "[]")
    pri_items = json.loads(v(r["priority_breakdown"]) or "[]")
    with st.container(key=f"isla_id_{modo}"):
        pills = theme.pill(v(r["giro"]), "info") + theme.pill(ESTADO_ROTULOS.get(v(r["estado"]), v(r["estado"]))) + theme.pill(v(r["estrato"]) or "Tamaño n/d")
        medidores = (_medidor("FIT", fit_s, "Compatibilidad con tus servicios. Regla interna, no probabilidad de compra.")
                     + _medidor("PRIORIDAD", pri_s, "Conveniencia de contactarlo hoy. Regla interna, no probabilidad de compra."))
        _md(f'<div class="cab"><div class="cab-i"><p class="titulo">{escape(nombre)}</p>{pills}'
            f'<div class="porque-linea"><span class="k">¿Por qué sí?</span>{_porque_si(fit_items)}</div></div><div class="medidores">{medidores}</div></div>')

    with st.container(key=f"vistas_estira_{modo}"):
        perfil, evidencia, puntajes = st.tabs(["Perfil", f"Evidencia ({len(sen)})", f"Puntajes e historial ({len(hist)})"])
        with perfil:
            if r["possible_chain"]:
                otros = datos.miembros_grupo(df, r)
                lista = "".join(f'<div>{escape(mensajes.limpiar_nombre(v(o["nombre"])))} · {escape(v(o["municipio"]))}</div>' for _, o in otros.head(4).iterrows())
                mas = f'<div class="origen">+{len(otros) - 4} más: filtra por motivo en Base</div>' if len(otros) > 4 else ""
                with st.container(key=f"isla_aviso_sxfull_{modo}"):
                    _md(theme.aviso(f'<b>Posible grupo · {int(r["possible_chain_count"])} establecimientos</b> · {escape(v(r["group_reason"]))}. '
                                    f'<span class="origen">Ayuda de revisión; no confirma sucursales.</span><div class="lista" style="display:block">{lista}{mas}</div>', "warn"))
            with st.container(key=f"isla_ficha_sxfull_{modo}"):
                ubic = " ".join(p for p in (v(r["direccion"]).title(), f'CP {v(r["cp"])}' if v(r["cp"]) else "") if p)
                muni = v(r["municipio"]) + (f' ({v(r["localidad"])})' if v(r["localidad"]) and v(r["localidad"]) != v(r["municipio"]) else "")
                corredor = " · ".join(p for p in (v(r["corredor_tipo"]).title(), v(r["corredor_nombre"]).title()) if p)
                celdas = (theme.ficha_item("Razón social", v(r["razon_social"])) + theme.ficha_item("Tipo", v(r["tipo_establecimiento"])) + theme.ficha_item("Personal", v(r["estrato"]))
                          + theme.ficha_item("Dirección", f"{ubic} · {muni}" if ubic else muni, 2)
                          + theme.ficha_item("Alta en DENUE", v(r["fecha_alta"]), 1, "Incorporación al directorio; no es la fecha de fundación.")
                          + theme.ficha_item("SCIAN", f'{v(r["clase_id"])} · {v(r["clase_actividad"])}', 2) + theme.ficha_item("Corredor / zona", corredor))
                _md(theme.titulo_isla("Ficha", "publico") + f'<div class="ficha">{celdas}</div>')
            with st.container(key=f"isla_contacto_{modo}"):
                _md(theme.titulo_isla("Contacto", "publico") + _contactos_html(r))
            with st.container(key=f"isla_hipotesis_{modo}"):
                conf = v(r["hypothesis_confidence"]) or "baja"
                _md(theme.titulo_isla("Hipótesis de trabajo", "hipotesis") + f'<div>{escape(v(r["hypothesis_text"]) or "Sin hipótesis generada.")}</div>'
                    + f'<div class="hip-meta">Sin verificar · Confianza {escape(conf)} · {escape(v(r["hypothesis_basis"]))}</div>')
            with st.container(key=f"isla_evidencia1_sxfull_{modo}"):
                if sen:
                    citas = "".join(_cita_html(s, 130) for s in sen[:2])
                    _md(theme.titulo_isla(f"Evidencia web · {min(2, len(sen))} de {len(sen)}", "senal") + f'<div class="citas">{citas}</div>')
                else:
                    _md(theme.titulo_isla("Evidencia web", "senal") + '<div class="sub">Sin señales registradas. Un sitio disponible no demuestra un problema interno.</div>')
        with evidencia:
            with st.container(key=f"isla_citas_sxfull_{modo}"):
                if sen:
                    citas = "".join(_cita_html(s, 260) for s in sen)
                    _md(theme.titulo_isla(f"Citas del sitio ({len(sen)})", "senal") + f'<div class="citas">{citas}</div>')
                else:
                    _md(theme.titulo_isla("Citas del sitio", "senal") + '<div class="sub">Sin señales registradas. Un sitio disponible no demuestra un problema interno.</div>')
            with st.container(key=f"isla_baseh_sxfull_{modo}"):
                _md(theme.titulo_isla("Cómo leer la evidencia", "hipotesis")
                    + f'<div>{escape(v(r["hypothesis_text"]) or "Sin hipótesis generada.")}</div>'
                    + f'<div class="hip-meta">Base: {escape(v(r["hypothesis_basis"]))}. Confirma que el sitio corresponde al establecimiento: una mención demuestra vocabulario, no un problema interno.</div>')
        with puntajes:
            with st.container(key=f"isla_fit_{modo}"):
                _md(theme.desglose("FIT", fit_s, fit_items, "Compatibilidad con tus servicios. Regla interna, no probabilidad."))
            with st.container(key=f"isla_prio_{modo}"):
                _md(theme.desglose("PRIORIDAD", pri_s, pri_items, "Conveniencia de contactarlo hoy. Regla interna, no probabilidad."))
            with st.container(key=f"isla_historial_sxfull_{modo}"):
                _md(theme.titulo_isla("Historial de interacciones", "manual") + _historial_html(hist))


def _canales_disponibles(r) -> dict[str, str]:
    c = {}
    correo = v(r["correo_web"]) if contacto.email_valido(v(r["correo_web"])) else v(r["correo"])
    tel = contacto.telefono_mx(v(r["telefono"]))
    wa = contacto.telefono_mx(v(r["whatsapp"]))
    if contacto.email_valido(correo):
        c["Correo"] = correo
    if tel:
        c["Teléfono"] = tel
    if wa or tel:
        c["WhatsApp"] = wa or tel  # probar el canal es una decisión explícita; el formato no prueba disponibilidad
    return c


def _accion(r, sen: list[dict], hist: list[dict], modo: str, tema: str) -> None:
    pid = r["id"]
    fila = {k: (None if pd.isna(x) else x) if not isinstance(x, (list, dict)) else x for k, x in r.items()}
    rec = acciones.recommend_next_action(fila, int(r["fit_score"] or 0), bool(sen))
    tono = {"alta": "ok", "media": "warn", "baja": "mute"}[rec["confidence"]]
    with st.container(key=f"isla_accion_{modo}"):
        _md(f'<div class="accion-t"><span class="isla-t">Siguiente acción</span><span class="valor">{escape(acciones.ROTULOS[rec["action"]])}</span>'
            f'{theme.pill("Confianza " + rec["confidence"], tono)}</div><div class="sub">{escape(rec["reason"])}</div>')

    disp = _canales_disponibles(r)
    primer = next((h for h in hist if h["interaction_type"] == "contacto"), None)
    prefer = {"email": "Correo", "telefono": "Teléfono", "whatsapp": "WhatsApp"}.get(v(primer["channel"]) if primer else rec["action"])
    opciones = list(disp)
    canal_ui, texto, asunto, variante, canal_db, graves = None, "", "", "", "manual", []
    fila_msg = {"id": pid, "nombre": v(r["nombre"]), "giro": v(r["giro"]), "giro_display": v(r["giro_display"])}

    with st.container(key=f"isla_msg_estira_{modo}"):
        if not opciones:
            _md(theme.titulo_isla("Mensaje") + theme.aviso("Sin correo ni teléfono válido. Revisa los datos de contacto antes de registrar un envío.", "warn"))
        else:
            fila_canal, fila_info = st.columns([3.2, 1], gap="small", vertical_alignment="center")
            canal_ui = fila_canal.segmented_control("Canal de contacto", opciones, default=prefer if prefer in opciones else opciones[0],
                                                    key=f"{modo}_canal_{pid}", label_visibility="collapsed") or opciones[0]
            canal_db = {"Correo": "email", "Teléfono": "telefono", "WhatsApp": "whatsapp"}[canal_ui]
            if modo == "resp":
                variante = "manual"
            elif modo == "seg":
                m = mensajes.seguimiento(fila_msg, int(r["toques"] or 1))
                texto, variante = m.cuerpo, m.variante
                if canal_db == "email":
                    asunto = "Re: " + mensajes.primer_contacto(fila_msg, "email", sen).asunto
            else:
                m = mensajes.primer_contacto(fila_msg, "email" if canal_db == "email" else "whatsapp", sen)
                asunto, texto, variante = m.asunto, m.cuerpo, m.variante
                if canal_db == "telefono":
                    variante = "Guion-" + variante
            clave = f"{pid}_{canal_db}_{variante}_{int(r['toques'] or 0)}"
            if canal_db == "email":
                asunto = st.text_input("Asunto", asunto, key=f"{modo}_asu_{clave}", label_visibility="collapsed", placeholder="Asunto")
            texto = st.text_area("Mensaje", texto, height=200, key=f"{modo}_txt_{clave}", label_visibility="collapsed",
                                 placeholder="Escribe tu respuesta; las conversaciones se responden manualmente.")
            problemas = [] if modo == "resp" else mensajes.validate_message(
                texto, "seguimiento" if modo == "seg" else "email" if canal_db == "email" else "whatsapp",
                asunto if canal_db == "email" else "", evidencia=mensajes.obs_con_evidencia(sen) is not None)
            graves = [p for p in problemas if not p.startswith("Aviso:")]
            avisos = [p for p in problemas if p.startswith("Aviso:")]
            if graves:
                _md(theme.aviso("<b>Plantilla inválida</b> · " + " · ".join(escape(p) for p in graves), "warn"))
            nota_envio = "Formato válido; disponibilidad de WhatsApp sin confirmar" if canal_db == "whatsapp" else "Guion para llamada" if canal_db == "telefono" else "envío manual"
            fila_info.html(f'<div class="meta-msg" title="{escape(nota_envio)}">{escape(variante)}<br>{mensajes.palabras(texto)} palabras{"<br>" + escape(avisos[0]) if avisos else ""}</div>')
            if canal_db == "email":
                copiar.fila([{"label": "Email", "texto": disp["Correo"], "titulo": "Copiar email"}, {"label": "Asunto", "texto": asunto, "titulo": "Copiar asunto"},
                             {"label": "Cuerpo", "texto": texto, "titulo": "Copiar cuerpo"},
                             {"label": "Gmail ↗", "url": config.GMAIL_URL, "primary": True, "titulo": "Abrir Gmail; pega y revisa antes de enviar"}], tema)
            else:
                tel = disp[canal_ui]
                items = [{"label": "Teléfono", "texto": contacto.telefono_legible(tel), "titulo": "Copiar teléfono"}, {"label": "Mensaje", "texto": texto, "titulo": "Copiar mensaje"}]
                if canal_db == "whatsapp" and texto:
                    items.append({"label": "WhatsApp ↗", "url": contacto.whatsapp_url(tel, texto), "titulo": "Probar WhatsApp; no todo teléfono DENUE tiene WhatsApp"})
                copiar.fila(items, tema)

    with st.container(key=f"isla_estado_{modo}"):
        notas = st.text_input("Notas", v(r["notas"]), key=f"{modo}_nota_{pid}", label_visibility="collapsed", placeholder="Tus notas: quién contestó, qué dijo, próximo paso")
        if modo == "hoy":
            if st.button("Marcar contactado", type="primary", key=f"hoy_ok_{pid}", width="stretch", disabled=not canal_ui or bool(graves)):
                _mutar(db.registrar_contacto, pid, canal_db, variante or None, texto or None, notas or None)
            a, b, c, d = st.columns(4, gap="small")
            if a.button("Revisado", key=f"hoy_rev_{pid}", width="stretch"):
                st.session_state.setdefault("al_final", [])
                if pid not in st.session_state["al_final"]:
                    st.session_state["al_final"].append(pid)      # lo revisado pasa al final de la cola de esta sesión: la lista avanza
                _mutar(db.cambiar_estado, pid, "revisado", notas or None)
            if b.button("Posponer", key=f"hoy_pos_{pid}", width="stretch"):
                _mutar(db.posponer, pid, 3)
            if c.button("Saltar", key=f"hoy_skip_{pid}", width="stretch"):
                st.session_state.setdefault("saltados", set()).add(pid)
                st.rerun()
            if d.button("Descartar", key=f"hoy_no_{pid}", width="stretch"):
                _mutar(db.cambiar_estado, pid, "descartado", notas or "Descartado en revisión")
        else:
            if modo == "seg":
                a, b = st.columns([2, 1], gap="small")
                if a.button("Envié el seguimiento", type="primary", key=f"seg_ok_{pid}", width="stretch", disabled=not canal_ui or bool(graves)):
                    _mutar(db.registrar_seguimiento, pid, canal_db, variante or None, texto or None)
                if b.button("Descartar", key=f"seg_no_{pid}", width="stretch"):
                    _mutar(db.cambiar_estado, pid, "descartado", notas or "Descartado en seguimiento")
            a, b = st.columns([2, 1], gap="small", vertical_alignment="bottom")
            tipo = a.selectbox("Tipo de respuesta", list(RESPUESTA_ROTULOS), format_func=RESPUESTA_ROTULOS.get, key=f"{modo}_rt_{pid}", label_visibility="collapsed")
            if b.button("Registrar", key=f"{modo}_rr_{pid}", width="stretch", help="Registra la respuesta y cancela todos los seguimientos"):
                _mutar(db.registrar_respuesta, pid, tipo, notas or None)
            if modo == "resp":
                cols = st.columns(4, gap="small")
                for col, (rot, est) in zip(cols, (("Reunión", "reunion"), ("Propuesta", "propuesta"), ("Cliente", "cliente"), ("Cerrar", "no_interesado"))):
                    if col.button(rot, key=f"resp_{est}_{pid}", width="stretch"):
                        _mutar(db.cambiar_estado, pid, est, notas or None)


def vista(df: pd.DataFrame, inter: pd.DataFrame, sen: pd.DataFrame, modo: str, vacio: str, df_todo: pd.DataFrame, tema: str = "auto",
          filtros: Callable[[pd.DataFrame], pd.DataFrame] | None = None) -> None:
    """`filtros` (opcional) dibuja los controles de filtro dentro de la isla de la cola y devuelve el DataFrame filtrado."""
    clave = f"sel_{modo}"
    c1, c2, c3 = st.columns(PROPORCIONES, gap="small")
    with c1, st.container(key=f"isla_cola_{modo}"):
        _md(theme.titulo_isla("Seleccionar prospecto"))
        q = st.text_input("Buscar en la cola", key=f"{modo}_buscar", placeholder="Buscar prospecto", label_visibility="collapsed")
        if filtros:
            df = filtros(df)
        if q.strip():
            df = df[df[["nombre", "razon_social", "municipio"]].fillna("").apply(lambda c: c.str.contains(q.strip(), case=False, regex=False)).any(axis=1)]
        saltados = st.session_state.get("saltados", set())
        if modo == "hoy":
            df = df[~df["id"].isin(saltados)]
            al_final = st.session_state.get("al_final", [])
            if al_final:
                df = pd.concat([df[~df["id"].isin(al_final)], df[df["id"].isin(al_final)]])
        if df.empty:
            with c2:
                st.info(vacio)
            if modo == "hoy" and saltados and st.button("Limpiar saltados"):
                st.session_state["saltados"] = set()
                st.rerun()
            return
        limite_key = f"{modo}_limite"
        limite = st.session_state.get(limite_key, PAGE_SIZE)
        st.caption(f"{len(df):,} prospectos")
        ids = list(df["id"])
        if st.session_state.get(clave) not in ids:
            st.session_state[clave] = ids[0]
        with st.container(key=f"lista_{modo}", border=False):
            for _, r in df.head(limite).iterrows():
                if _item_cola(r, r["id"] == st.session_state[clave], modo):
                    st.session_state[clave] = r["id"]
                    st.rerun()
            if len(df) > limite and st.button("Mostrar más", key=f"{modo}_mas", width="stretch"):
                st.session_state[limite_key] = limite + PAGE_SIZE
                st.rerun()
    sel = df[df["id"] == st.session_state[clave]].iloc[0]
    senales_sel, hist = datos.senales_de(sen, sel["id"]), datos.historial_de(inter, sel["id"])
    with c2, st.container(key=f"col_ctx_{modo}", border=False):
        _contexto(sel, senales_sel, hist, df_todo, modo)
    with c3, st.container(key=f"col_acc_{modo}", border=False):
        _accion(sel, senales_sel, hist, modo, tema)
