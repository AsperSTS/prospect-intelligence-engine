"""Enriquecimiento web prudente y determinista.

Los sitios vienen de datos externos (no confiables). Controles: solo http(s); DNS resuelto y validado ANTES de cada petición y
tras cada redirect; sin IPs privadas/loopback/link-local/metadata; límite de redirects, de bytes y de tiempo; solo contenido
textual; sin JavaScript; máximo de páginas por dominio con pausa entre peticiones al mismo dominio.
Riesgo residual documentado: entre la validación de DNS y la conexión podría cambiar la resolución (DNS rebinding).
"""
import html as _html
import ipaddress
import re
import socket
import time
from urllib.parse import urljoin, urlparse

import httpx

from . import config, contacto, senales

_resolver = socket.getaddrinfo  # inyectable en pruebas
WA_RE = re.compile(r"(?:wa\.me/|api\.whatsapp\.com/send\?phone=|wa\.me/send\?phone=)\+?(\d{10,13})")
EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)+")
HREF_RE = re.compile(r"""href\s*=\s*["']([^"'#]+)["']""", re.I)
TIPOS_OK = ("text/html", "application/xhtml+xml", "text/plain")
BINARIOS = (".pdf", ".zip", ".rar", ".exe", ".dmg", ".jpg", ".jpeg", ".png", ".gif", ".webp", ".svg", ".mp4", ".mp3", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx")
# grupos de páginas razonables, en orden de preferencia
PAGINAS = [("nosotros", ("nosotros", "quienes", "empresa", "about")), ("servicios", ("servicios", "services")),
           ("productos", ("productos", "products", "catalogo")), ("contacto", ("contacto", "contact"))]


def normalizar_url(raw: str) -> str:
    raw = (raw or "").strip()
    if not raw or " " in raw:
        return ""
    if not raw.lower().startswith(("http://", "https://")):
        raw = "http://" + raw
    p = urlparse(raw)
    return raw if p.scheme in ("http", "https") and p.hostname else ""


def host_seguro(url: str) -> bool:
    """Resuelve el host y rechaza cualquier IP no pública (incluye metadata cloud 169.254.169.254)."""
    host = urlparse(url).hostname
    if not host or urlparse(url).scheme not in ("http", "https"):
        return False
    try:
        for info in _resolver(host, None):
            ip = ipaddress.ip_address(info[4][0])
            if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved or ip.is_multicast or ip.is_unspecified:
                return False
        return True
    except (socket.gaierror, ValueError, TypeError, OSError):
        return False


def descargar(client: httpx.Client, url: str) -> tuple[str, str] | None:
    """(url_final, texto) o None. Redirects manuales revalidados; aborta si el cuerpo excede MAX_RESPONSE_BYTES."""
    try:
        for _ in range(config.MAX_REDIRECTS + 1):
            if not host_seguro(url):
                return None
            with client.stream("GET", url, follow_redirects=False) as r:
                if r.status_code in (301, 302, 303, 307, 308) and r.headers.get("location"):
                    url = str(httpx.URL(url).join(r.headers["location"]))
                    continue
                if r.status_code != 200:
                    return None
                tipo = r.headers.get("content-type", "").split(";")[0].strip().lower()
                if tipo not in TIPOS_OK:
                    return None
                declarado = r.headers.get("content-length")
                if declarado and declarado.isdigit() and int(declarado) > config.MAX_RESPONSE_BYTES:
                    return None
                buf = bytearray()
                for chunk in r.iter_bytes():
                    buf.extend(chunk)
                    if len(buf) > config.MAX_RESPONSE_BYTES:
                        return None  # demasiado grande: se descarta, no se procesa truncado
                return url, buf.decode("utf-8", errors="ignore")
        return None  # demasiados redirects
    except httpx.HTTPError:
        return None


def a_texto(html: str) -> str:
    html = re.sub(r"(?is)<(script|style|noscript|svg|nav|header|footer|aside|form|button|select|iframe)\b.*?</\1>", " ", html)   # sin menús ni cabeceras
    html = re.sub(r"(?s)<!--.*?-->", " ", html)
    return re.sub(r"\s+", " ", _html.unescape(re.sub(r"<[^>]+>", " ", html))).strip()


def enlaces_internos(base_url: str, html: str) -> list[str]:
    """Hasta MAX_PAGES_PER_DOMAIN-1 enlaces internos equivalentes a nosotros/servicios/productos/contacto. No se inventan rutas."""
    host = (urlparse(base_url).hostname or "").removeprefix("www.")
    elegidos: dict[str, str] = {}
    for href in HREF_RE.findall(html):
        if href.lower().startswith(("mailto:", "tel:", "javascript:")):
            continue
        url = urljoin(base_url, href.strip())
        p = urlparse(url)
        if p.scheme not in ("http", "https") or (p.hostname or "").removeprefix("www.") != host or p.path.lower().endswith(BINARIOS):
            continue
        ruta = p.path.lower()
        for grupo, claves in PAGINAS:
            if grupo not in elegidos and any(c in ruta for c in claves):
                elegidos[grupo] = f"{p.scheme}://{p.netloc}{p.path}"
    return [elegidos[g] for g, _ in PAGINAS if g in elegidos][: config.MAX_PAGES_PER_DOMAIN - 1]


def extraer_contactos(html: str, texto: str, dominio: str) -> tuple[str, str]:
    correos = [e.lower() for e in EMAIL_RE.findall(html + " " + texto)]
    correos = [e for e in dict.fromkeys(correos) if contacto.email_valido(e)]
    correos.sort(key=lambda e: dominio not in e.split("@")[1])  # prioriza correos del propio dominio
    wa = WA_RE.findall(html)
    return (correos[0] if correos else ""), (wa[0][-10:] if wa else "")


def enriquecer_dominio(client: httpx.Client, dominio: str, pausa=time.sleep) -> dict:
    """Visita hasta MAX_PAGES_PER_DOMAIN páginas de un dominio. Devuelve status, correo, whatsapp y señales con evidencia."""
    inicio = f"https://{dominio}/"
    vacio = {"status": "error", "pages": 0, "email": "", "whatsapp": "", "signals": []}
    if not host_seguro(inicio):
        return {**vacio, "status": "bloqueado"}
    primera = descargar(client, inicio) or descargar(client, f"http://{dominio}/")
    if not primera:
        return vacio
    url0, html0 = primera
    paginas = [(url0, html0)]
    for u in enlaces_internos(url0, html0):
        pausa(config.MIN_DELAY_PER_DOMAIN_SECONDS)
        r = descargar(client, u)
        if r:
            paginas.append(r)
    email, wa, signals, vistas = "", "", [], set()
    for url, html in paginas:
        texto = a_texto(html)
        e, w = extraer_contactos(html, texto, dominio)
        email, wa = email or e, wa or w
        signals += senales.detectar(texto, url, vistas)
    return {"status": "ok", "pages": len(paginas), "email": email, "whatsapp": wa, "signals": signals}


def nuevo_cliente() -> httpx.Client:
    return httpx.Client(timeout=config.REQUEST_TIMEOUT_SECONDS, headers={"User-Agent": "Mozilla/5.0 (compatible; prospectos-privado/1.0)"})
