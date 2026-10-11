"""Pestaña Métricas: embudo visual + cortes. Solo cifras que ayudan a decidir; sin conclusiones con muestras pequeñas.
Ocupa toda la altura: el embudo reparte el espacio y la tabla de cortes llena su isla."""
from html import escape

import pandas as pd
import streamlit as st

from prospectos import config, metricas
from . import theme

NOMBRES = {"revisados": "Revisados", "contactados": "Contactados", "respondieron": "Respondieron", "respuesta_positiva": "Resp. positiva",
           "reuniones": "Reuniones", "propuestas": "Propuestas", "clientes": "Clientes"}
TASAS = {"response_rate": "Respuesta", "positive_response_rate": "Resp. positiva", "meeting_rate": "Reunión", "proposal_rate": "Propuesta", "win_rate": "Cierre"}


def _embudo_html(f: dict) -> str:
    tope = max(f["revisados"], 1)
    filas = []
    for k, nombre in NOMBRES.items():
        n = f[k]
        pct = round(100 * n / tope)
        extra = f' · {round(100 * n / f["contactados"])} % de contactados' if k not in ("revisados", "contactados") and f["contactados"] else ""
        filas.append(f'<div class="f"><span class="k">{escape(nombre)}</span><span class="b"><i style="width:{pct}%"></i></span><span class="n" title="{escape(nombre + extra)}">{n:,}</span></div>')
    return f'<div class="embudo">{"".join(filas)}</div>'


def _tasas_html(f: dict) -> str:
    if not f["contactados"]:
        return theme.aviso("Aún no hay contactos. Las tasas aparecen al marcar los primeros contactados.", "info")
    celdas = "".join(f'<div class="dato"><span class="k">Tasa de {escape(n.lower())}</span><span class="v"><b>{f[k]} %</b></span></div>' for k, n in TASAS.items())
    return f'<div class="contactos">{celdas}</div>'


def _tabla_html(tabla: pd.DataFrame, por: str) -> str:
    """Tabla propia (HTML) para que respete tema, tipografía y estados del resto del panel. Cabecera fija y scroll interno solo si hace falta."""
    cols = [por, "contactados", "respondieron", "respuesta_positiva", "reuniones", "propuestas", "clientes", *TASAS, "lectura"]
    nombres = {por: metricas.CORTES[por], **NOMBRES, **{k: f"{v} %" for k, v in TASAS.items()}, "lectura": "Lectura"}
    cab = "".join(f'<th class="{"n" if c not in (por, "lectura") else ""}">{escape(nombres[c])}</th>' for c in cols)
    filas = []
    for _, r in tabla.iterrows():
        celdas = "".join(f'<td class="{"n" if c not in (por, "lectura") else ""}">{escape(str(r[c]))}</td>' for c in cols)
        filas.append(f"<tr>{celdas}</tr>")
    return f'<div class="tabla-wrap"><table class="tabla"><thead><tr>{cab}</tr></thead><tbody>{"".join(filas)}</tbody></table></div>'


def _vista(df: pd.DataFrame, inter: pd.DataFrame) -> None:
    d = metricas.preparar(df, inter)
    f = metricas.funnel(d)
    izq, der = st.columns([1, 1.6], gap="small")
    with izq, st.container(key="col_metricas_a"):
        with st.container(key="isla_embudo_estira"):
            st.html('<div class="llena">' + theme.titulo_isla("Embudo") + _embudo_html(f) + "</div>")
        with st.container(key="isla_tasas"):
            st.html(theme.titulo_isla("Tasas sobre contactados") + _tasas_html(f))
    with der, st.container(key="col_metricas_b"):
        with st.container(key="isla_cortes"):
            st.html(theme.titulo_isla("Cortes") + f'<div class="sub">Cambia <b>una</b> variable por prueba. Con menos de {config.MIN_SAMPLE_PER_VARIANT} contactos por grupo no se concluye; '
                    f'ideal 30+ antes de decisiones fuertes. Hasta entonces los scores son reglas razonables, no conocimiento del mercado.</div>')
            por = st.selectbox("Cortar por", list(metricas.CORTES), format_func=metricas.CORTES.get, key="metricas_corte", label_visibility="collapsed")
            tabla = metricas.corte(d, por)
            st.html(_tabla_html(tabla, por) if not tabla.empty else '<div class="sub">Sin datos para este corte todavía: aparecerán al marcar contactos y respuestas.</div>')
        with st.container(key="isla_mensajes_estira"):
            partes = [theme.titulo_isla("Qué mensaje y qué canal funcionan")]
            for clave, titulo in (("variante_usada", "Por variante de mensaje"), ("canal_contacto", "Por canal")):
                t = metricas.corte(d, clave)
                partes.append(f'<div class="etq">{escape(titulo)}</div>' + (_tabla_html(t, clave) if not t.empty else '<div class="sub">Sin datos todavía.</div>'))
            st.html("".join(partes))


def vista(df: pd.DataFrame, inter: pd.DataFrame) -> None:
    _vista(df, inter)
