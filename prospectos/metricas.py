"""Métricas de funnel. Solo lo que sirve para decidir: qué giro, tamaño, canal, apertura y segmento llegan más lejos.

Cohorte = prospectos con al menos un contacto (etapa_max ≥ 1). Las tasas se calculan sobre contactados.
No se declara ganadora ninguna variante con menos de MIN_SAMPLE_PER_VARIANT contactos.
"""
import pandas as pd

from . import config

ETAPAS = [("contactados", 1), ("respondieron", 2), ("respuesta_positiva", 3), ("reuniones", 4), ("propuestas", 5), ("clientes", 6)]
RATIOS = {"response_rate": "respondieron", "positive_response_rate": "respuesta_positiva", "meeting_rate": "reuniones",
          "proposal_rate": "propuestas", "win_rate": "clientes"}
CORTES = {"giro": "Giro", "clase_id": "Clase SCIAN", "estrato": "Estrato", "municipio": "Municipio", "canal_contacto": "Canal",
          "variante_usada": "Variante de mensaje", "fit_bucket": "Rango de fit", "priority_bucket": "Rango de prioridad"}


def _bucket(s: pd.Series, cortes: list[int], etiquetas: list[str]) -> pd.Series:
    return pd.cut(s.fillna(0), bins=[-1, *cortes, 101], labels=etiquetas)


def preparar(df: pd.DataFrame, interacciones: pd.DataFrame) -> pd.DataFrame:
    """Une el primer contacto (canal y variante realmente usados) y crea los rangos de fit/prioridad."""
    d = df.copy()
    d["etapa_max"] = d["etapa_max"].fillna(0).astype(int)
    if interacciones.empty:
        d["canal_contacto"], d["variante_usada"] = None, None
    else:
        primero = (interacciones[interacciones["interaction_type"] == "contacto"].sort_values("id")
                   .drop_duplicates("prospect_id")[["prospect_id", "channel", "template_variant"]]
                   .rename(columns={"prospect_id": "id", "channel": "canal_contacto", "template_variant": "variante_usada"}))
        d = d.merge(primero, on="id", how="left")
    d["fit_bucket"] = _bucket(d["fit_score"], [49, 59, 69], ["<50", "50-59", "60-69", "70+"])
    d["priority_bucket"] = _bucket(d["priority_score"], [29, 49, 69], ["<30", "30-49", "50-69", "70+"])
    return d


def funnel(d: pd.DataFrame) -> dict:
    """Conteos y tasas globales. d = resultado de preparar()."""
    out = {"revisados": int((d["estado"] != "nuevo").sum())}
    for nombre, etapa in ETAPAS:
        out[nombre] = int((d["etapa_max"] >= etapa).sum())
    base = out["contactados"]
    for ratio, col in RATIOS.items():
        out[ratio] = round(100 * out[col] / base, 1) if base else None
    return out


def corte(d: pd.DataFrame, por: str) -> pd.DataFrame:
    """Funnel por una dimensión. Incluye `lectura` con la advertencia de muestra pequeña."""
    if por not in CORTES:
        raise ValueError(por)
    c = d[d["etapa_max"] >= 1].dropna(subset=[por])
    if c.empty:
        return pd.DataFrame(columns=[por, *[n for n, _ in ETAPAS], *RATIOS, "lectura"])
    filas = []
    for valor, g in c.groupby(por, observed=True):
        fila = {por: valor}
        for nombre, etapa in ETAPAS:
            fila[nombre] = int((g["etapa_max"] >= etapa).sum())
        for ratio, col in RATIOS.items():
            fila[ratio] = round(100 * fila[col] / fila["contactados"], 1)
        fila["lectura"] = lectura(fila["contactados"])
        filas.append(fila)
    return pd.DataFrame(filas).sort_values("contactados", ascending=False).reset_index(drop=True)


def lectura(contactados: int) -> str:
    if contactados < config.MIN_SAMPLE_PER_VARIANT:
        return "Muestra pequeña — todavía no concluir"
    if contactados < 30:
        return "Señal débil: ideal 30+ antes de decisiones fuertes"
    return "Muestra suficiente para una primera lectura"
