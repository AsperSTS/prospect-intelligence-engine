"""Base completa: búsqueda, edición de estado/notas, exportación y actualización de datos. Todo en una fila + tabla de altura completa."""
import pandas as pd
import streamlit as st

from prospectos import db, pipeline
from prospectos.config import ENTIDADES
from . import datos

COLS = ["nombre", "municipio", "giro", "estrato", "fit_score", "priority_score", "canal", "telefono", "correo", "correo_web", "sitio",
        "possible_chain_count", "group_reason", "estado", "proximo_seguimiento", "notas"]
RO = [c for c in COLS if c not in ("estado", "notas")]


def _vista(df: pd.DataFrame) -> None:
    f = st.columns([3, 1.4, 1.4, 1.4, 1.1, 1.1, 1.3], vertical_alignment="center", gap="small")
    q = f[0].text_input("Buscar", placeholder="Buscar nombre, razón social o municipio", label_visibility="collapsed")
    estados = f[1].multiselect("Estado", db.ESTADOS, placeholder="Estado", label_visibility="collapsed")
    giros = f[2].multiselect("Giro", sorted(df["giro"].dropna().unique()), placeholder="Giro", label_visibility="collapsed")
    acc = f[3].multiselect("Acción", ["email", "telefono", "manual_review", "follow_up", "skip"], placeholder="Acción sugerida", label_visibility="collapsed")
    vista_df = df
    if q:
        m = (vista_df["nombre"].str.contains(q, case=False, na=False) | vista_df["municipio"].str.contains(q, case=False, na=False)
             | vista_df["razon_social"].str.contains(q, case=False, na=False))
        vista_df = vista_df[m]
    for col, vals in (("estado", estados), ("giro", giros), ("canal", acc)):
        if vals:
            vista_df = vista_df[vista_df[col].isin(vals)]
    vista_df = vista_df.sort_values("priority_score", ascending=False)
    guardar = f[4].button("Guardar", type="primary", width="stretch", help="Guarda los cambios de estado y notas hechos en la tabla")
    f[5].download_button("CSV", vista_df[COLS].to_csv(index=False).encode("utf-8-sig"), "prospectos.csv", "text/csv", width="stretch", help="Exporta lo filtrado")

    with f[6].popover("Actualizar datos", width="stretch"):
        ent = st.multiselect("Entidades", list(ENTIDADES), default=["21", "29"], format_func=lambda k: f"{ENTIDADES[k]} ({k})")
        dom = st.number_input("Dominios web a visitar", 10, 500, 100, 10, help="Caché de 30 días: no se vuelve a visitar un dominio reciente.")
        if st.button("Descargar, analizar y enriquecer", disabled=not ent, width="stretch"):
            with st.status("Trabajando…", expanded=True) as estado:
                nuevos = pipeline.pull(ent, log=lambda m: estado.write(m))
                pipeline.analizar_todos()
                pipeline.enriquecer_pendientes(int(dom), log=lambda m: estado.write(m))
                pipeline.analizar_todos()
                estado.update(label=f"Listo: {nuevos} establecimientos nuevos", state="complete")
            datos.limpiar()
        if st.button("Recalcular scores y mensajes", width="stretch"):
            pipeline.analizar_todos()
            datos.limpiar()
            st.rerun()

    st.caption(f"{len(vista_df):,} de {len(df):,} establecimientos (no necesariamente empresas distintas) · se muestran los 500 de mayor prioridad")
    with st.container(key="col_base", border=False):
        ed = st.data_editor(
            vista_df[["id"] + COLS].head(500), hide_index=True, width="stretch", height="stretch", disabled=RO,
            column_config={"id": None, "estado": st.column_config.SelectboxColumn("Estado", options=db.ESTADOS, required=True),
                           "fit_score": st.column_config.ProgressColumn("Fit", min_value=0, max_value=100, format="%d"),
                           "priority_score": st.column_config.ProgressColumn("Prioridad", min_value=0, max_value=100, format="%d"),
                           "canal": "Acción", "possible_chain_count": "Grupo", "group_reason": "Motivo de grupo", "sitio": st.column_config.LinkColumn("Sitio")},
        )
    if guardar:
        base = df.set_index("id")
        with db.conectar() as con:
            for _, r in ed.iterrows():
                if r["estado"] != base.at[r["id"], "estado"]:
                    db.cambiar_estado(con, r["id"], r["estado"], r["notas"] or None)
                elif (r["notas"] or "") != (base.at[r["id"], "notas"] or ""):
                    con.execute("UPDATE prospectos SET notas=? WHERE id=?", (r["notas"], r["id"]))
        datos.limpiar()
        st.rerun()


def vista(df: pd.DataFrame) -> None:
    with st.container(key="isla_base"):
        _vista(df)
