"""Normalización y validación de datos de contacto. No infere fijo/móvil: solo valida formato."""
import re
from urllib.parse import quote, urlparse

from . import config

EMAIL_OK = re.compile(r"^[a-z0-9._%+-]+@[a-z0-9-]+(?:\.[a-z0-9-]+)*\.[a-z]{2,}$")
EMAIL_BASURA = ("ejemplo", "example", "correo.com", "email.com", "tudominio", "sentry", "wixpress", "domain.com", "sitio.com",
                "tuempresa", "yourdomain", "nombre@", "usuario@", "godaddy", "@2x", "noreply", "no-reply")
EXT_NO_EMAIL = (".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg", ".css", ".js")

# dominios que no identifican a una empresa (redes, constructores, correo gratuito): no sirven para agrupar ni enriquecer
DOMINIOS_GENERICOS = {
    "facebook.com", "instagram.com", "linktr.ee", "wa.me", "google.com", "sites.google.com", "linkedin.com", "twitter.com", "x.com",
    "youtube.com", "tiktok.com", "wixsite.com", "wordpress.com", "blogspot.com", "weebly.com", "godaddysites.com", "mercadolibre.com.mx",
    "gmail.com", "hotmail.com", "outlook.com", "yahoo.com", "yahoo.com.mx", "prodigy.net.mx", "live.com", "icloud.com",
}


def telefono_mx(raw: str) -> str:
    """Devuelve 10 dígitos si el formato es razonable (quita 52 / 044 / 045 / 01); si no, ''."""
    d = re.sub(r"\D", "", raw or "")
    for pref in ("0052", "52", "044", "045", "01"):
        if d.startswith(pref) and len(d) > 10:
            d = d[len(pref):]
            break
    return d if len(d) == 10 else ""


def telefono_legible(raw: str) -> str:
    t = telefono_mx(raw)
    return f"{t[:3]} {t[3:6]} {t[6:]}" if t else (raw or "").strip()


def whatsapp_url(telefono_prospecto: str, texto: str) -> str:
    """Enlace wa.me al teléfono DEL PROSPECTO (nunca al del remitente). '' si el número es dudoso."""
    t = telefono_mx(telefono_prospecto)
    return f"https://wa.me/{config.COUNTRY_CODE}{t}?text={quote(texto)}" if t else ""


def email_valido(e: str) -> bool:
    e = (e or "").strip().lower()
    return bool(EMAIL_OK.match(e)) and not e.endswith(EXT_NO_EMAIL) and not any(b in e for b in EMAIL_BASURA)


def dominio(url: str) -> str | None:
    """Host sin www; None si es vacío, IP o un dominio genérico (redes sociales, constructores)."""
    url = (url or "").strip()
    if not url or " " in url:
        return None
    if "://" not in url:
        url = "http://" + url
    host = (urlparse(url).hostname or "").lower().removeprefix("www.")
    if not host or "." not in host or re.fullmatch(r"[\d.]+", host):
        return None
    if host in DOMINIOS_GENERICOS or any(host.endswith("." + g) for g in DOMINIOS_GENERICOS):
        return None
    return host
