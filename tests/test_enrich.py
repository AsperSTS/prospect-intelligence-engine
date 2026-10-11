import sys
from pathlib import Path

import httpx
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from prospectos import config, db, enrich, pipeline, senales  # noqa: E402
from tests.test_core import _fila_db, tmpdb  # noqa: E402,F401

PUBLICAS = {"publico.test": "8.8.8.8", "otro.test": "1.1.1.1"}
PRIVADAS = {"evil.test": "127.0.0.1", "interno.test": "192.168.1.5", "meta.test": "169.254.169.254", "diez.test": "10.0.0.7"}


@pytest.fixture(autouse=True)
def dns_falso(monkeypatch):
    tabla = {**PUBLICAS, **PRIVADAS}

    def resolver(host, _puerto):
        if host in tabla:
            return [(2, 1, 6, "", (tabla[host], 0))]
        import socket
        return socket.getaddrinfo(host, None) if host.replace(".", "").isdigit() or host == "localhost" else (_ for _ in ()).throw(OSError("sin dns"))

    monkeypatch.setattr(enrich, "_resolver", resolver)


def cliente(handler):
    return httpx.Client(transport=httpx.MockTransport(handler), timeout=5)


def html(cuerpo, ctype="text/html; charset=utf-8", status=200, headers=None):
    return httpx.Response(status, content=cuerpo.encode(), headers={"content-type": ctype, **(headers or {})})


# ------------------------------------------------------------ SSRF
@pytest.mark.parametrize("url", ["http://localhost/", "http://127.0.0.1/", "http://127.9.9.9/", "http://10.1.2.3/", "http://172.16.0.1/",
                                 "http://192.168.0.10/", "http://169.254.169.254/latest/meta-data", "http://[::1]/", "http://0.0.0.0/",
                                 "http://evil.test/", "http://interno.test/", "http://meta.test/", "ftp://publico.test/", "file:///etc/passwd"])
def test_destinos_privados_o_no_http_bloqueados(url):
    assert not enrich.host_seguro(url)


def test_publico_permitido_y_dns_inexistente_bloqueado():
    assert enrich.host_seguro("https://publico.test/")
    assert not enrich.host_seguro("https://no-existe.invalid/")


def test_redirect_a_ip_privada_bloqueado_sin_llegar_al_destino():
    visitados = []

    def h(req):
        visitados.append(req.url.host)
        return httpx.Response(302, headers={"location": "http://evil.test/admin"})

    assert enrich.descargar(cliente(h), "http://publico.test/") is None
    assert visitados == ["publico.test"]   # nunca se conectó a evil.test


def test_demasiados_redirects():
    def h(req):
        return httpx.Response(302, headers={"location": "http://otro.test/" if req.url.host == "publico.test" else "http://publico.test/"})

    assert enrich.descargar(cliente(h), "http://publico.test/") is None


def test_respuesta_demasiado_grande_se_aborta(monkeypatch):
    monkeypatch.setattr(config, "MAX_RESPONSE_BYTES", 1000)
    assert enrich.descargar(cliente(lambda r: html("x" * 5000)), "http://publico.test/") is None
    declarado = lambda r: html("ok", headers={"content-length": "999999"})  # noqa: E731
    assert enrich.descargar(cliente(declarado), "http://publico.test/") is None
    assert enrich.descargar(cliente(lambda r: html("pequeño")), "http://publico.test/")[1] == "pequeño"


def test_binarios_y_tipos_no_textuales_se_rechazan():
    assert enrich.descargar(cliente(lambda r: html("%PDF", ctype="application/pdf")), "http://publico.test/") is None
    assert enrich.descargar(cliente(lambda r: html("x", ctype="application/octet-stream")), "http://publico.test/") is None


def test_timeout_y_errores_de_red_no_rompen():
    def h(req):
        raise httpx.ReadTimeout("lento")

    assert enrich.descargar(cliente(h), "http://publico.test/") is None
    assert enrich.enriquecer_dominio(cliente(h), "publico.test", pausa=lambda s: None)["status"] == "error"
    assert enrich.enriquecer_dominio(cliente(h), "evil.test", pausa=lambda s: None)["status"] == "bloqueado"


# ------------------------------------------------------------ extracción
HOME = """<html><body><a href="/nosotros">Nosotros</a><a href="/servicios.html">Servicios</a><a href="/productos">Productos</a>
<a href="/contacto">Contacto</a><a href="/blog">Blog</a><a href="/catalogo.pdf">PDF</a><a href="http://externo.test/servicios">ext</a>
<script>var x='cotización falsa en script';</script><p>Fabricamos sobre pedido. Escríbanos a ventas@publico.test o info@gmail.com</p></body></html>"""


def test_maximo_5_paginas_enlaces_internos_y_pausa_por_dominio(monkeypatch):
    pedidos, pausas = [], []

    def h(req):
        pedidos.append(req.url.path)
        return html(HOME if req.url.path == "/" else f"<p>Página {req.url.path}. Solicite su cotización. Control de inventario.</p>")

    res = enrich.enriquecer_dominio(cliente(h), "publico.test", pausa=pausas.append)
    assert res["pages"] <= config.MAX_PAGES_PER_DOMAIN == 5 and set(pedidos) <= {"/", "/nosotros", "/servicios.html", "/productos", "/contacto"}
    assert "/blog" not in pedidos and "/catalogo.pdf" not in pedidos
    assert len(pausas) == res["pages"] - 1 and all(p == config.MIN_DELAY_PER_DOMAIN_SECONDS for p in pausas)


def test_senales_con_evidencia_url_y_correo_propio():
    def h(req):
        return html(HOME if req.url.path == "/" else "<p>Servicios de mantenimiento industrial</p>")

    res = enrich.enriquecer_dominio(cliente(h), "publico.test", pausa=lambda s: None)
    por_tipo = {s["signal_type"]: s for s in res["signals"]}
    assert "sobre_pedido" in por_tipo and "sobre pedido" in por_tipo["sobre_pedido"]["signal_text"].lower()
    assert por_tipo["sobre_pedido"]["signal_source_url"].startswith("https://publico.test") or por_tipo["sobre_pedido"]["signal_source_url"].startswith("http://publico.test")
    assert "cotizacion" not in por_tipo                      # el texto dentro de <script> se ignora
    assert res["email"] == "ventas@publico.test"             # prioriza el dominio propio sobre gmail


def test_detectar_no_inventa():
    assert senales.detectar("Venta de abarrotes al menudeo", "http://x") == []
    assert senales.observacion([]) is None
    assert senales.observacion(["fabricacion"]) is None      # señal no relacionada no genera observación
    assert senales.observacion(["sobre_pedido"])[1] == "Vi en su sitio que fabrican sobre pedido."


# ------------------------------------------------------------ caché 30 días
def test_cache_evita_volver_a_descargar(tmpdb, monkeypatch):
    llamadas = []
    monkeypatch.setattr(enrich, "enriquecer_dominio", lambda c, d, **k: llamadas.append(d) or
                        {"status": "ok", "pages": 1, "email": "a@publico.test", "whatsapp": "", "signals": [
                            {"signal_type": "cotizacion", "signal_text": "…cotización…", "signal_source_url": "http://publico.test/"}]})
    with db.conectar() as con:
        db.upsert_denue(con, [_fila_db("1", sitio="publico.test", dominio="publico.test"), _fila_db("2", sitio="www.publico.test", dominio="publico.test")])
    assert pipeline.enriquecer_pendientes(10, log=lambda *_: None) == 1       # una visita para dos establecimientos
    assert pipeline.enriquecer_pendientes(10, log=lambda *_: None) == 0       # caché vigente
    assert llamadas == ["publico.test"]
    with db.conectar() as con:
        assert con.execute("SELECT count(*) FROM web_signals").fetchone()[0] == 2
        assert con.execute("SELECT source_website, correo_web FROM prospectos WHERE id='1'").fetchone()[:] == (1, "a@publico.test")
        con.execute("UPDATE web_cache SET checked_at='2000-01-01T00:00:00'")  # caché vencida
    assert pipeline.enriquecer_pendientes(10, log=lambda *_: None) == 1
    assert pipeline.enriquecer_pendientes(10, forzar=True, log=lambda *_: None) == 1
    assert len(llamadas) == 3


def test_fallo_de_red_no_borra_datos_previos(tmpdb, monkeypatch):
    with db.conectar() as con:
        db.upsert_denue(con, [_fila_db("1", sitio="publico.test", dominio="publico.test")])
        db.guardar_senales(con, "1", [{"signal_type": "cotizacion", "signal_text": "t", "signal_source_url": "http://publico.test/"}])
    monkeypatch.setattr(enrich, "enriquecer_dominio", lambda c, d, **k: {"status": "error", "pages": 0, "email": "", "whatsapp": "", "signals": []})
    pipeline.enriquecer_pendientes(10, forzar=True, log=lambda *_: None)
    with db.conectar() as con:
        assert con.execute("SELECT count(*) FROM web_signals").fetchone()[0] == 1


@pytest.mark.parametrize("texto,tipo,esperado", [
    ("Soluciones a medida para cada cliente", "sobre_pedido", False),     # marketing genérico, no es fabricación sobre pedido
    ("Fabricamos a la medida de su proyecto", "sobre_pedido", True),
    ("Fabricación sobre pedido de estructuras", "sobre_pedido", True),
    ("Productos de calidad para su hogar", "calidad", False),             # 'calidad' suelta es ruido
    ("Contamos con control de calidad en cada lote", "calidad", True),
    ("La Gran Bodega - abarrotes y más", "almacen", False),               # nombre de empresa, no un almacén
    ("Contamos con almacén propio en Puebla", "almacen", True),
])
def test_senales_sin_falsos_positivos(texto, tipo, esperado):
    assert (tipo in {s["signal_type"] for s in senales.detectar(texto, "http://x")}) is esperado


def test_evidencia_sin_glifos_raros():
    ev = senales.detectar("Servicios \u25a0 de almacén \u2022 con entrega a domicilio \ufffd", "http://x")
    assert all("\u25a0" not in e["signal_text"] and "\ufffd" not in e["signal_text"] and "\u2022" not in e["signal_text"] for e in ev)


def test_texto_limpiar_quita_glifos_y_normaliza():
    from prospectos import texto
    sucio = "Servicios  de almacén​ ® con entrega → rápida，hoy：&amp; más &#209;oño 。"
    limpio = texto.limpiar(sucio)
    assert limpio == "Servicios de almacén con entrega rápida,hoy:& más Ñoño"
    assert not any(ord(c) >= 0xE000 or c in "​�®©→™" for c in limpio)
    assert texto.limpiar(None) == "" and texto.limpiar("  a \n\t b ") == "a b"
    assert texto.sin_ruido_de_menu("Skip to content Home Servicios") == "Home Servicios"


def test_html_sin_nav_header_footer_y_cita_sin_palabras_cortadas():
    html = ("<header>Skip to content Menu Home Inicio</header><nav><a>Servicios</a><a>Cotizar</a></nav>"
            "<p>Ofrecemos servicios de almacenamiento y distribución para empresas de la región con control de inventarios y entregas puntuales.</p>"
            "<footer>Todos los derechos reservados © 2026</footer>")
    t = enrich.a_texto(html)
    assert "Skip to content" not in t and "derechos reservados" not in t and "Cotizar" not in t
    for e in senales.detectar(t, "http://x"):
        assert not e["signal_text"].lstrip("…").startswith(("macenamiento", "istribución")) and "�" not in e["signal_text"]
