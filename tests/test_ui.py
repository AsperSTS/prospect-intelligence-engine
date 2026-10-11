"""Flujo de la UI contra una base temporal (nunca toca data/prospectos.db)."""
import sys
from datetime import date, timedelta
from pathlib import Path

import pytest
import streamlit as st

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from streamlit.testing.v1 import AppTest  # noqa: E402

from prospectos import db, pipeline  # noqa: E402
from tests.test_core import _fila_db, tmpdb  # noqa: E402,F401


@pytest.fixture
def base(tmpdb):
    filas = [_fila_db(str(i), nombre=f"EMPRESA {i} SA DE CV", correo=f"v{i}@empresa{i}.mx", telefono="2221234567",
                      sitio=f"empresa{i}.mx", dominio=f"empresa{i}.mx") for i in range(1, 4)]
    with db.conectar() as con:
        db.upsert_denue(con, filas)
        db.guardar_senales(con, "1", [{"signal_type": "cotizacion", "signal_text": "…solicite su cotización…", "signal_source_url": "https://empresa1.mx/"}])
    pipeline.analizar_todos()
    return tmpdb


def _app(pestana: str | None = None):
    """Renderiza la app. Solo se construye la pestaña abierta, así que las pruebas indican cuál (la misma preferencia que guarda la UI)."""
    st.cache_data.clear()  # la caché de cargar() persiste entre AppTest en el mismo proceso
    at = AppTest.from_file(str(ROOT / "app.py"), default_timeout=90)
    if pestana:
        at.session_state["pestana_base"] = pestana
    return at.run()


def _btn(at, prefijo):
    return next(b for b in at.button if (b.key or "").startswith(prefijo))


def test_render_sin_errores_y_estructura(base):
    at = _app()
    assert not at.exception, [e.value for e in at.exception]
    etiquetas = [t.label for t in at.tabs]
    principales = [e.split(" · ")[0] for e in etiquetas if e.split(" · ")[0] in ("Hoy", "Seguimientos", "Conversaciones", "Métricas", "Base")]
    assert principales == ["Hoy", "Seguimientos", "Conversaciones", "Métricas", "Base"]
    assert any(e.startswith("Hoy · 3") for e in etiquetas)   # el conteo vive en la pestaña
    assert len([b for b in at.button if "hoy_sel_" in (b.key or "")]) == 3


def test_contactar_registra_interaccion_variante_y_mensaje(base):
    at = _app()
    seleccionado = at.session_state["sel_hoy"]
    _btn(at, "hoy_ok_").click().run()
    assert not at.exception, [e.value for e in at.exception]
    with db.conectar() as con:
        r = con.execute("SELECT estado, toques, proximo_seguimiento FROM prospectos WHERE id=?", (seleccionado,)).fetchone()
        assert (r["estado"], r["toques"]) == ("contactado", 1)
        assert r["proximo_seguimiento"] == (date.today() + timedelta(days=3)).isoformat()
        h = db.historial(con, seleccionado)
        assert len(h) == 1 and h[0]["interaction_type"] == "contacto" and h[0]["template_variant"] and len(h[0]["message_rendered"]) > 40
        assert db.progreso_hoy(con)["contacto"] == 1
    assert at.session_state["sel_hoy"] != seleccionado   # avanzó al siguiente


def test_descartar_y_posponer_sacan_de_la_cola(base):
    at = _app()
    primero = at.session_state["sel_hoy"]
    _btn(at, "hoy_pos_").click().run()
    with db.conectar() as con:
        assert con.execute("SELECT snooze_until FROM prospectos WHERE id=?", (primero,)).fetchone()[0] is not None
    assert primero not in [b.key.split("hoy_sel_")[1] for b in at.button if "hoy_sel_" in (b.key or "")]
    segundo = at.session_state["sel_hoy"]
    _btn(at, "hoy_no_").click().run()
    with db.conectar() as con:
        assert con.execute("SELECT estado FROM prospectos WHERE id=?", (segundo,)).fetchone()[0] == "descartado"


def _contactar_vencido(pid="1"):
    with db.conectar() as con:
        db.registrar_contacto(con, pid, "email", "EM-con-A", "x")
        con.execute("UPDATE prospectos SET proximo_seguimiento=? WHERE id=?", ((date.today() - timedelta(days=1)).isoformat(), pid))


def test_seguimiento_vencido_se_registra_y_avanza_la_secuencia(base):
    _contactar_vencido()
    at = _app("Seguimientos")
    _btn(at, "seg_ok_1").click().run()
    assert not at.exception, [e.value for e in at.exception]
    with db.conectar() as con:
        r = con.execute("SELECT toques, estado FROM prospectos WHERE id='1'").fetchone()
        assert (r["toques"], r["estado"]) == (2, "contactado")
        ult = db.historial(con, "1")[-1]
        assert (ult["interaction_type"], ult["sequence_step"], ult["template_variant"]) == ("seguimiento", 1, "FU-d3")
        assert db.progreso_hoy(con)["seguimiento"] == 1


def test_registrar_respuesta_cancela_seguimientos_y_pasa_a_conversaciones(base):
    _contactar_vencido()
    at = _app("Seguimientos")
    next(s for s in at.selectbox if (s.key or "").startswith("seg_rt_1")).select("interesado")
    _btn(at, "seg_rr_1").click().run()
    assert not at.exception, [e.value for e in at.exception]
    with db.conectar() as con:
        r = con.execute("SELECT estado, proximo_seguimiento FROM prospectos WHERE id='1'").fetchone()
        assert (r["estado"], r["proximo_seguimiento"]) == ("respuesta_positiva", None)
        assert db.seguimientos_pendientes(con) == []
    at2 = _app("Conversaciones")
    assert any((b.key or "") == "resp_sel_1" for b in at2.button)           # aparece en Conversaciones
    assert not any((b.key or "") == "seg_ok_1" for b in at2.button)         # ya no se le ofrece seguimiento


def test_metricas_y_base_renderizan_con_datos(base):
    import pandas as pd
    from prospectos import metricas
    from ui import metricas as vista_metricas
    _contactar_vencido()
    with db.conectar() as con:
        db.registrar_respuesta(con, "1", "interesado")
        df = pd.read_sql_query("SELECT * FROM prospectos", con)
        inter = pd.read_sql_query("SELECT * FROM interactions", con)
    at = _app()
    assert not at.exception, [e.value for e in at.exception]
    f = metricas.funnel(metricas.preparar(df, inter))
    assert (f["contactados"], f["respondieron"], f["respuesta_positiva"]) == (1, 1, 1)
    html = vista_metricas._embudo_html(f)
    assert "Contactados" in html and "Respondieron" in html and 'class="embudo"' in html
    assert "100 % de contactados" in html          # el único contactado respondió


def test_tema_persistente_sin_recarga(base, monkeypatch):
    from ui import theme
    from prospectos import config
    monkeypatch.setattr(config, "PREFS_PATH", base / "preferencias.json")
    at = _app()
    seleccionado = at.session_state["sel_hoy"]
    for tema in ("Oscuro", "Claro", "Auto"):
        at.button_group(key="tema").set_value(tema).run()
        assert not at.exception
        assert at.session_state["sel_hoy"] == seleccionado
        assert theme.tema_guardado() == tema


def test_copiar_escapa_y_filtra_urls():
    from ui import copiar
    h = copiar.html([{"label": "Copiar", "texto": "</script><img src=x onerror=alert(1)> & más"}, {"label": "Mal", "url": "javascript:alert(1)"},
                     {"label": "Gmail", "url": "https://mail.google.com/mail/u/1/#inbox?compose=new"}])
    assert "</script><img" not in h and "javascript:alert" not in h and "mail.google.com" in h and "\\u003c/script" in h


def test_copiar_color_scheme_coincide_con_el_modo():
    from ui import copiar
    item = [{"label": "x", "texto": "t"}]
    assert "color-scheme:light;" in copiar.html(item, "light") and "color-scheme:dark;" in copiar.html(item, "dark") and "color-scheme:light dark;" in copiar.html(item, "auto")


def test_cola_scroll_permite_llegar_mas_alla_de_60_y_buscar_literalmente(base):
    with db.conectar() as con:
        db.upsert_denue(con, [_fila_db(str(i), nombre=f"EMPRESA {i}", correo=f"v{i}@empresa{i}.mx") for i in range(4, 67)])
    pipeline.analizar_todos()
    at = _app()
    next(b for b in at.button if b.key == "hoy_mas").click().run()
    assert not at.exception
    assert len([b for b in at.button if (b.key or "").startswith("hoy_sel_")]) == 66
    next(t for t in at.text_input if t.key == "hoy_buscar").set_value("[").run()
    assert not at.exception  # los caracteres de regex son texto; la página se vacía sin error
    next(t for t in at.text_input if t.key == "hoy_buscar").set_value("EMPRESA 65").run()
    assert not at.exception and at.session_state["sel_hoy"] == "65"


def test_mensaje_editado_invalido_impide_registrar_contacto(base):
    at = _app()
    next(t for t in at.text_area if (t.key or "").startswith("hoy_txt_")).set_value("{nombre}").run()
    assert not at.exception and _btn(at, "hoy_ok_").disabled
    with db.conectar() as con:
        assert con.execute("SELECT count(*) FROM interactions").fetchone()[0] == 0


def test_llamada_se_registra_como_telefono_y_whatsapp_es_decision_explicita(base):
    at = _app()
    seleccionado = at.session_state["sel_hoy"]
    at.button_group(key=f"hoy_canal_{seleccionado}").set_value("Teléfono").run()
    assert not at.exception
    _btn(at, "hoy_ok_").click().run()
    with db.conectar() as con:
        h = db.historial(con, seleccionado)[-1]
        assert h["channel"] == "telefono" and h["template_variant"].startswith("Guion-")


def test_conversacion_no_sugiere_otro_primer_contacto(base):
    _contactar_vencido()
    with db.conectar() as con:
        db.registrar_respuesta(con, "1", "interesado")
    at = _app("Conversaciones")
    respuesta = next(t for t in at.text_area if (t.key or "").startswith("resp_txt_"))
    assert not at.exception and respuesta.value == ""


def test_la_pestana_activa_sobrevive_al_cambio_de_contadores(base):
    """Regresión: al enviar un seguimiento cambia «Seguimientos · N» y Streamlit reiniciaba la vista a «Hoy»."""
    _contactar_vencido("1")
    _contactar_vencido("2")
    at = _app("Seguimientos")
    assert any("Seguimientos · 2" in t.label for t in at.tabs)
    _btn(at, "seg_ok_").click().run()
    assert not at.exception, [e.value for e in at.exception]
    assert at.session_state["pestana_base"] == "Seguimientos" or any("Seguimientos · 1" in t.label for t in at.tabs)
    # tras la acción sigue construida la pestaña de seguimientos (hay un botón de envío del prospecto restante)
    assert any((b.key or "").startswith("seg_ok_") for b in at.button)
