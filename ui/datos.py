"""Carga de datos para la UI (con caché corta). Refresca prioridades porque dependen de la fecha y del estado."""
import pandas as pd
import streamlit as st

from prospectos import db, pipeline, texto


@st.cache_data(ttl=10)
def cargar() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    pipeline.refrescar_prioridades()
    with db.conectar() as con:
        df = pd.read_sql_query("SELECT * FROM prospectos", con)
        inter = pd.read_sql_query("SELECT * FROM interactions ORDER BY id", con)
        sen = pd.read_sql_query("SELECT * FROM web_signals ORDER BY id", con)
    return df, inter, sen


def limpiar() -> None:
    st.cache_data.clear()


def senales_de(sen: pd.DataFrame, pid: str) -> list[dict]:
    return sen[sen["prospect_id"] == pid].to_dict("records")


def historial_de(inter: pd.DataFrame, pid: str) -> list[dict]:
    return inter[inter["prospect_id"] == pid].to_dict("records")


def miembros_grupo(df: pd.DataFrame, r) -> pd.DataFrame:
    if not r.get("possible_chain"):
        return df.iloc[0:0]
    return df[(df["group_key"] == r["group_key"]) & (df["id"] != r["id"])]


def vacio(x) -> str:
    """Valor de celda como texto seguro para mostrar: sin NaN, sin glifos raros ni entidades HTML."""
    return "" if x is None or (isinstance(x, float) and pd.isna(x)) else texto.limpiar(str(x))
