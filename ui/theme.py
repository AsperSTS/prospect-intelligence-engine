"""Sistema visual de islas: tokens, tipografía única, estados de interacción y helpers de HTML.

Reglas de diseño:
- UNA familia tipográfica (la del sistema; SF Pro en Mac) y SOLO cuatro tamaños: 12 (etiquetas/auxiliar) · 14 (cuerpo y controles) ·
  16 (énfasis) · 20 (nombre y cifras). Solo dos pesos: 400 y 600. Interlineado 1.5.
- Espaciado en múltiplos de 4 px. Radios: 8 px controles, 14 px islas, 99 px pastillas.
- Un solo acento (azul). Verde/ámbar solo para estado semántico; todo lo demás es neutro.
- Hover = velo, presionado = velo más fuerte y escala .98, foco = anillo de 2 px, deshabilitado = 45 %. El mismo juego en TODOS los controles.
- Contraste de texto ≥ 4.5:1 en claro y oscuro.
- Espacio: cada columna mide la altura de la pantalla; las islas marcadas «estira» (clave con «estira») reparten el espacio sobrante.
  Solo scrollea lo que lo necesita de verdad (la lista de la cola y, en pantallas pequeñas, el contenido que ya no cabe).
"""
import json
from html import escape
from pathlib import Path

import streamlit as st

from prospectos import config

TEMAS = ["Claro", "Oscuro", "Auto"]

_CLARO = """color-scheme:light; --bg:#F5F5F7; --isla:#FFFFFF; --relleno:#F2F2F7; --linea:rgba(0,0,0,.10); --txt:#1D1D1F; --txt2:#6E6E73;
  --acento:#0B63CE; --acento-txt:#0B63CE; --ok:#1B7F3B; --warn:#9A5B00; --velo:rgba(0,0,0,.05); --velo2:rgba(0,0,0,.10); --sel:rgba(11,99,206,.10);"""
_OSCURO = """color-scheme:dark; --bg:#101114; --isla:#1C1C1E; --relleno:#2C2C2E; --linea:rgba(255,255,255,.14); --txt:#F5F5F7; --txt2:#A1A1A6;
  --acento:#0B63CE; --acento-txt:#64A8FF; --ok:#30D158; --warn:#FFB340; --velo:rgba(255,255,255,.07); --velo2:rgba(255,255,255,.13); --sel:rgba(100,168,255,.16);"""

CSS_PATH = Path(__file__).with_name("theme.css")   # se lee en cada ejecución: los cambios de estilo no requieren reiniciar el servidor


def _css() -> str:
    return CSS_PATH.read_text(encoding="utf-8")

_AUTO = "@media (prefers-color-scheme: dark) { :root { " + _OSCURO + " } }"


def aplicar(tema: str = "Auto") -> str:
    """Aplica colores propios + CSS. Devuelve 'light' | 'dark' | 'auto' (los iframes de componentes necesitan saberlo)."""
    tema = tema if tema in TEMAS else "Auto"
    tokens, auto = {"Claro": (_CLARO, ""), "Oscuro": (_OSCURO, ""), "Auto": (_CLARO, _AUTO)}[tema]
    st.html(_css().replace("__TOKENS__", tokens).replace("__AUTO__", auto))
    return {"Claro": "light", "Oscuro": "dark", "Auto": "auto"}[tema]


def tema_guardado() -> str:
    try:
        t = json.loads(config.PREFS_PATH.read_text(encoding="utf-8")).get("tema", "Auto")
        return t if t in TEMAS else "Auto"
    except (OSError, ValueError):
        return "Auto"


def guardar_tema(tema: str) -> None:
    if tema in TEMAS and tema != tema_guardado():
        try:
            config.DATA_DIR.mkdir(exist_ok=True)
            config.PREFS_PATH.write_text(json.dumps({"tema": tema}), encoding="utf-8")
        except OSError:
            pass


NIVELES = [(70, "Alta", "ok"), (50, "Media", "warn"), (0, "Baja", "mute")]
FUENTES = {"publico": "Dato público", "senal": "Señal detectada", "hipotesis": "Hipótesis", "manual": "Ingresado por ti"}


def pill(texto: str, tono: str = "mute") -> str:
    return f'<span class="pill {tono}">{escape(texto)}</span>'


def nivel(score: float) -> tuple[str, str]:
    for minimo, nombre, tono in NIVELES:
        if score >= minimo:
            return nombre, tono
    return "Baja", "mute"


def fuente(tipo: str) -> str:
    return f'<span class="fte">{escape(FUENTES[tipo])}</span>'


def titulo_isla(texto: str, fuente_tipo: str | None = None) -> str:
    return f'<div class="isla-t"><span>{escape(texto)}</span>{fuente(fuente_tipo) if fuente_tipo else ""}</div>'


def aviso(html_interno: str, tono: str = "warn") -> str:
    """html_interno debe venir ya escapado por quien llama. tono: warn | info | accion."""
    return f'<div class="nota {tono}">{html_interno}</div>'


def dato(k: str, v: str, ayuda: str = "") -> str:
    t = f' title="{escape(ayuda)}"' if ayuda else ""
    return f'<div class="dato"{t}><span class="k">{escape(k)}</span><span class="v">{escape(v) if v else "—"}</span></div>'


def ficha_item(k: str, v: str, ancho: int = 1, ayuda: str = "") -> str:
    """Celda de la ficha: etiqueta pequeña arriba y valor debajo. `ancho` = columnas que ocupa (1 o 2)."""
    t = f' title="{escape(ayuda)}"' if ayuda else ""
    return f'<div class="fi s{ancho}"{t}><span class="k">{escape(k)}</span><span class="v">{escape(v) if v else "—"}</span></div>'


def desglose(titulo: str, total: int, items: list[dict], ayuda: str) -> str:
    """Tabla explicable: etiqueta, barra relativa al máximo, puntos y el motivo visible (sin depender de hover)."""
    filas = []
    for i in items:
        mx = max(i.get("max", 0), 1)
        ancho = min(100, round(100 * abs(i["pts"]) / mx))
        signo = f'{i["pts"]:+d}' if i["pts"] else "0"
        nota = escape(i.get("nota", ""))
        sub = f'<br><span class="n">{nota}</span>' if nota else ""
        clase = "neg" if i["pts"] < 0 else ""
        filas.append(f'<div class="desg-f"><span>{escape(i["etiqueta"])}{sub}</span>'
                     f'<span class="b"><i class="{clase}" style="width:{ancho}%"></i></span><span class="p">{signo}</span></div>')
    return f'<div class="desg"><div class="desg-t" title="{escape(ayuda)}"><span>{escape(titulo)}</span><span>{total}</span></div>{"".join(filas)}</div>'


def metas_html(progreso: dict[str, int], meta: dict[str, int], etiquetas: dict[str, str]) -> str:
    celdas = []
    for k, objetivo in meta.items():
        hecho = progreso.get(k, 0)
        pct = min(100, round(100 * hecho / objetivo))
        clase = "meta done" if hecho >= objetivo else "meta"
        celdas.append(f'<div class="{clase}"><div class="t">{escape(etiquetas[k])}</div>'
                      f'<div class="n">{hecho}<small> / {objetivo}</small></div><div class="bar"><i style="width:{pct}%"></i></div></div>')
    return f'<div class="metas">{"".join(celdas)}</div>'
