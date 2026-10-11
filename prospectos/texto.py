"""Sanitización de texto externo (sitios web, DENUE) para mostrarlo sin glifos rotos ni ruido de menús.

Lo que viene de la web puede traer íconos de fuentes (zona de uso privado U+E000+), espacios de ancho cero, símbolos ®©™,
flechas, puntuación de ancho completo (，：。) o entidades HTML sin decodificar. Todo eso se normaliza o se elimina.
"""
import html
import re
import unicodedata

_PERMITIDO = re.compile(r"[^\w\s.,;:¿?¡!()/%&+\-–—\"'’“”…@#°ºª·$|*=<>\[\]{}~^_\\]")
_BASURA_MENU = re.compile(
    r"\b(skip to (main )?content|saltar al contenido|ir al contenido( principal)?|toggle (navigation|menu)|open menu|close menu|menu toggle|"
    r"loading\.\.\.|cargando\.\.\.|aviso de privacidad|todos los derechos reservados|all rights reserved)\b", re.I)
_MARCAS = str.maketrans({"®": "", "©": "", "™": "", "℠": ""})


def limpiar(texto: str | None) -> str:
    """Decodifica entidades, normaliza (NFKC), quita caracteres no imprimibles/privados/símbolos y colapsa espacios."""
    if not texto:
        return ""
    t = html.unescape(str(texto)).translate(_MARCAS)
    t = unicodedata.normalize("NFKC", t)
    t = "".join(" " if unicodedata.category(c) in ("Zs", "Zl", "Zp") or c in "\t\n\r" else c for c in t
                if unicodedata.category(c) not in ("Cc", "Cf", "Co", "Cs", "Cn") or c in "\t\n\r")
    t = _PERMITIDO.sub(" ", t)
    return re.sub(r"\s+", " ", t).strip()


def sin_ruido_de_menu(texto: str) -> str:
    return re.sub(r"\s+", " ", _BASURA_MENU.sub(" ", texto)).strip()


def calidad_fragmento(frag: str) -> float:
    """Más alto = más parece una oración real y menos un menú de navegación (muchas Mayúsculas seguidas, pocas palabras en minúscula)."""
    palabras = re.findall(r"[^\W\d_]{2,}", frag)
    if len(palabras) < 5:
        return 0.0
    minus = sum(1 for p in palabras if p[0].islower())
    capitalizadas_seguidas = max((len(m.group(0).split()) for m in re.finditer(r"(?:\b[A-ZÁÉÍÓÚÑ][\wáéíóúñ]+\b\s*){3,}", frag)), default=0)
    return minus / len(palabras) + min(len(palabras), 14) / 28 - 0.15 * capitalizadas_seguidas
