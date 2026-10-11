"""Panel Streamlit local: streamlit run app.py. Pensado para un solo usuario."""
from datetime import date

import pandas as pd
import streamlit as st

from prospectos import contacto, db
from ui import base, datos, debug, metricas, theme, trabajo

st.set_page_config(page_title="Prospectos", layout="wide", initial_sidebar_state="collapsed")

tema_ui = st.session_state.get("tema", theme.tema_guardado())
modo_iframe = theme.aplicar(tema_ui)

ETIQUETAS_META = {"investigado": "Revisados", "contacto": "Contactos", "seguimiento": "Seguimientos", "publicacion": "Publicación"}

df, inter, sen = datos.cargar()
hoy = date.today().isoformat()

abiertos = df["estado"].isin(["nuevo", "revisado"]) & (df["priority_score"] > 0) & (df["snooze_until"].fillna("") <= hoy)
seg_due = df["estado"].eq("contactado") & (df["proximo_seguimiento"].fillna("9999") <= hoy)

with st.container(key="isla_barra"):
    fila_sup = st.columns([8, 2.5, 1.8, 0.8], vertical_alignment="center", gap="small")
    with db.conectar() as con:
        progreso = db.progreso_hoy(con)
    fila_sup[0].html(f'<div class="strip"><span class="marca">Prospectos<span class="marca-sub">Mesa de trabajo · {hoy}</span></span>{theme.metas_html(progreso, db.META_DIARIA, ETIQUETAS_META)}</div>')
    with fila_sup[1]:
        st.segmented_control("Tema", theme.TEMAS, default=tema_ui, key="tema", selection_mode="single",
                             label_visibility="collapsed", on_change=lambda: theme.guardar_tema(st.session_state.get("tema") or "Auto"))
    if fila_sup[2].button("Registrar publicación", width="stretch", help="Suma 1 a la meta de publicaciones de hoy"):
        with db.conectar() as con:
            db.registrar_actividad(con, "publicacion")
        st.rerun()
    with fila_sup[3]:
        debug.interruptor()
        debug.inyectar()

if df.empty:
    st.info("Base vacía. Ejecuta en terminal: python -m prospectos run")
    st.stop()

n_conv = int(df["estado"].isin(["respondio", "respuesta_positiva", "reunion", "propuesta"]).sum())
# Los conteos viven en las etiquetas de las pestañas. Como Streamlit identifica cada pestaña por su etiqueta, al cambiar un conteo
# (p. ej. «Seguimientos · 4» → «· 3») reiniciaba la vista a «Hoy». Se guarda la pestaña por su nombre base y se restaura como `default`.
BASES = ["Hoy", "Seguimientos", "Conversaciones", "Métricas", "Base"]
etiquetas = {"Hoy": f"Hoy · {int(abiertos.sum()):,}", "Seguimientos": f"Seguimientos · {int(seg_due.sum())}", "Conversaciones": f"Conversaciones · {n_conv}",
             "Métricas": "Métricas", "Base": "Base"}


def _recordar_pestana() -> None:
    st.session_state["pestana_base"] = str(st.session_state.get("pestana_principal") or "Hoy").split(" · ")[0]


activa = st.session_state.get("pestana_base", "Hoy")
tab_hoy, tab_seg, tab_conv, tab_met, tab_base = st.tabs([etiquetas[b] for b in BASES], default=etiquetas.get(activa, etiquetas["Hoy"]),
                                                         key="pestana_principal", on_change=_recordar_pestana)


def filtros_hoy(cand: pd.DataFrame) -> pd.DataFrame:
    """Filtros dentro de un popover de la cola (no consumen altura de página)."""
    with st.popover("Filtros", width="stretch"):
        giros = st.multiselect("Giro", sorted(df["giro"].dropna().unique()), placeholder="Todos los giros")
        munis = st.multiselect("Municipio", sorted(df["municipio"].dropna().unique()), placeholder="Todos los municipios")
        fit_min = st.slider("Fit mínimo", 0, 100, 0)
        solo_contacto = st.toggle("Solo con contacto", value=True)
    if solo_contacto:
        con_contacto = (cand["correo"].fillna("").map(contacto.email_valido) | cand["correo_web"].fillna("").map(contacto.email_valido)
                        | cand["telefono"].fillna("").map(lambda t: bool(contacto.telefono_mx(t)))
                        | cand["whatsapp"].fillna("").map(lambda t: bool(contacto.telefono_mx(t))))
        cand = cand[con_contacto & cand["canal"].ne("skip")]
    if giros:
        cand = cand[cand["giro"].isin(giros)]
    if munis:
        cand = cand[cand["municipio"].isin(munis)]
    return cand[cand["fit_score"] >= fit_min]


# Solo se construye la pestaña abierta: la cola de «Hoy» (60 tarjetas) no se recalcula mientras trabajas en otra vista.
with tab_hoy:
    if tab_hoy.open:
        trabajo.vista(df[abiertos].sort_values("priority_score", ascending=False), inter, sen, "hoy",
                      "No hay prospectos con estos filtros. Ajusta los filtros o descarga más datos en la pestaña Base.", df, modo_iframe, filtros_hoy)

with tab_seg:
    if tab_seg.open:
        trabajo.vista(df[seg_due].sort_values("proximo_seguimiento"), inter, sen, "seg",
                      "Sin seguimientos vencidos. Aparecen aquí a los 3, 7 y 14 días de cada contacto, y se cancelan si responden.", df, modo_iframe)

with tab_conv:
    if tab_conv.open:
        trabajo.vista(df[df["estado"].isin(["respondio", "respuesta_positiva", "reunion", "propuesta"])].sort_values("priority_score", ascending=False),
                      inter, sen, "resp", "Aún no hay conversaciones abiertas. Registra aquí las respuestas que recibas.", df, modo_iframe)

with tab_met:
    if tab_met.open:
        metricas.vista(df, inter)

with tab_base:
    if tab_base.open:
        base.vista(df)
