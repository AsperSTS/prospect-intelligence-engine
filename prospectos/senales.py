"""Taxonomía de señales web públicas. Una señal es un texto que el sitio muestra; nunca un hecho interno de la empresa."""
import re

from . import texto as texto_mod

# tipo -> (regex, etiqueta para "menciona X", ¿relacionada directamente con lo que se vende?)
SENALES = {
    "sobre_pedido": (r"(?:sobre|bajo) pedido|(?:fabric\w+|manufactur\w+|producci[oó]n|maquinad\w+)\s+(?:a|bajo)\s+(?:la\s+)?(?:medida|dise[ñn]o|especificaci\w+)", "fabricación sobre pedido", True),
    "cotizacion": (r"cotizaci[oó]n|cotizar|cotiza\b|solicita(?:r)? (?:tu |su )?cotizaci", "cotizaciones", True),
    "servicio_tecnico": (r"servicio t[eé]cnico|soporte t[eé]cnico", "servicio técnico", True),
    "inventario": (r"inventarios?", "inventario", True),
    "almacen": (r"almac[eé]n(?:es)?\b|almacenamiento", "almacén", True),
    "logistica": (r"log[ií]stica", "logística", True),
    "distribucion": (r"distribuci[oó]n|distribuidor", "distribución", True),
    "flotilla": (r"flotilla|unidades de carga|transporte de carga", "flotilla o transporte de carga", True),
    "mantenimiento": (r"mantenimiento", "mantenimiento", True),
    "entregas": (r"entregas? (?:a|en|nacional|puntual|a tiempo)|env[ií]os? (?:a|en|nacional)", "entregas", True),
    "calidad": (r"control de calidad|aseguramiento de (?:la )?calidad|gesti[oó]n de (?:la )?calidad|sistema de (?:gesti[oó]n de )?calidad|inspecci[oó]n de calidad|metrolog[ií]a", "control de calidad", True),
    "iso": (r"\biso[ -]?(?:9001|14001|45001|\d{4,5})\b", "certificación ISO", True),
    "produccion": (r"producci[oó]n|manufactura", "producción", True),
    "fabricacion": (r"fabricaci[oó]n|fabricamos|fabricantes?", "fabricación", False),
    "proveedores": (r"proveedores", "proveedores", False),
    "proyectos": (r"proyectos", "proyectos", False),
    "sucursales": (r"sucursales", "sucursales", False),
}
_COMPILADAS = {t: re.compile(rx, re.I) for t, (rx, _, _) in SENALES.items()}

# orden de preferencia para citar una observación en un mensaje (las más concretas primero)
ORDEN_OBS = ["sobre_pedido", "cotizacion", "servicio_tecnico", "inventario", "logistica", "almacen", "flotilla", "mantenimiento",
             "distribucion", "entregas", "iso", "calidad", "produccion"]


def relacionadas(tipos) -> list[str]:
    return [t for t in tipos if SENALES.get(t, (None, None, False))[2]]


def etiqueta(tipo: str) -> str:
    return SENALES[tipo][1]


def observacion(tipos) -> tuple[str, str] | None:
    """(tipo, oración) para insertar en un mensaje; None si no hay señal relacionada con evidencia."""
    rel = set(relacionadas(tipos))
    for t in ORDEN_OBS:
        if t in rel:
            if t == "sobre_pedido":
                return t, "Vi en su sitio que fabrican sobre pedido."
            if t == "cotizacion":
                return t, "Vi en su sitio que atienden por cotización."
            if t == "servicio_tecnico":
                return t, "Vi en su sitio que ofrecen servicio técnico."
            return t, f"Vi en su sitio que mencionan {etiqueta(t)}."
    return None


def detectar(texto: str, url: str, ya: set[str] | None = None) -> list[dict]:
    """Mejor coincidencia por tipo (la que más parece una oración y menos un menú) con ±70 caracteres de contexto como evidencia.
    El texto se sanitiza: sin glifos raros, sin ruido de navegación. `ya` evita repetir tipos ya encontrados."""
    ya = ya if ya is not None else set()
    texto = texto_mod.limpiar(texto)
    out = []
    for tipo, rx in _COMPILADAS.items():
        if tipo in ya:
            continue
        mejor, mejor_q = None, -1.0
        for m in list(rx.finditer(texto))[:8]:
            ini, fin = max(0, m.start() - 70), min(len(texto), m.end() + 70)
            while 0 < ini < m.start() and texto[ini - 1] != " ":      # no cortar palabras a la mitad
                ini += 1
            while m.end() < fin < len(texto) and texto[fin] != " ":
                fin -= 1
            frag = texto_mod.sin_ruido_de_menu(texto[ini:fin])
            q = texto_mod.calidad_fragmento(frag)
            if q > mejor_q:
                mejor, mejor_q = (frag, ini > 0, fin < len(texto)), q
        if mejor:
            frag, corta_ini, corta_fin = mejor
            out.append({"signal_type": tipo, "signal_text": ("…" if corta_ini else "") + frag + ("…" if corta_fin else ""), "signal_source_url": url})
            ya.add(tipo)
    return out
