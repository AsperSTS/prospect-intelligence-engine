import re
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from prospectos import config, mensajes as m  # noqa: E402

GIROS = list(m.plantillas()["giros"])
NOMBRES = ["MAQUINAS DIESEL SUC. PUEBLA LIB. MEX.VER", "ACEROS DEL TORO S.A. DE C.V.", "GLOBALIZACION METAL MECANICA PCMI",
           "LOGISTICA Y TRANSPORTES DEL CENTRO SA DE CV"]
EVIDENCIA = [{"signal_type": "sobre_pedido", "signal_text": "…fabricamos sobre pedido…", "signal_source_url": "https://acme.mx/servicios"}]


def r(giro="Metalmecánica", nombre=NOMBRES[1], pid="42", display="estructuras metálicas"):
    return {"id": pid, "nombre": nombre, "giro": giro, "giro_display": display}


def test_limpiar_nombre():
    assert m.limpiar_nombre("MAQUINAS DIESEL SUC. PUEBLA LIB. MEX.VER") == "Maquinas Diesel"
    assert m.limpiar_nombre("ACEROS DEL TORO S.A. DE C.V.") == "Aceros del Toro"
    assert m.limpiar_nombre("GLOBALIZACION METAL MECANICA PCMI") == "Globalizacion Metal Mecanica PCMI"


def test_plantillas_cargan_y_se_validan(tmp_path, monkeypatch):
    assert {"whatsapp", "email", "seguimiento", "giros"} <= set(m.plantillas())
    malo = tmp_path / "t.toml"
    malo.write_text('[whatsapp]\nA = "x"\n')
    monkeypatch.setattr(config, "TEMPLATES_PATH", malo)
    with pytest.raises(m.PlantillaInvalida):
        m.plantillas()


@pytest.mark.parametrize("giro", GIROS)
@pytest.mark.parametrize("nombre", NOMBRES)
@pytest.mark.parametrize("pid", [str(i) for i in range(12)])
def test_whatsapp_valido_para_todos_los_giros_y_variantes(giro, nombre, pid):
    for rows in ([], EVIDENCIA):
        msg = m.primer_contacto(r(giro, nombre, pid), "whatsapp", rows)
        assert msg.valido, (msg.variante, msg.problemas, msg.cuerpo)
        assert m.palabras(msg.cuerpo) <= 65 and msg.cuerpo.count("?") == 1 and "{" not in msg.cuerpo
        assert not re.search(r"\b[A-ZÁÉÍÓÚ]{5,}\b", msg.cuerpo)            # nombres en MAYÚSCULAS


def test_whatsapp_no_menciona_audi_salvo_variante_d():
    for pid in map(str, range(40)):
        msg = m.primer_contacto(r(pid=pid), "whatsapp", [])
        assert ("Audi" in msg.cuerpo) == (msg.variante == "WA-D")


def test_variante_c_solo_con_evidencia_y_obs_citada():
    sin = {m.primer_contacto(r(pid=str(i)), "whatsapp", []).variante for i in range(80)}
    con = {m.primer_contacto(r(pid=str(i)), "whatsapp", EVIDENCIA).variante for i in range(80)}
    assert "WA-C" not in sin and sin == {"WA-A", "WA-B", "WA-D"}
    assert con == {"WA-A", "WA-B", "WA-C", "WA-D"}
    c = next(x for x in (m.primer_contacto(r(pid=str(i)), "whatsapp", EVIDENCIA) for i in range(80)) if x.variante == "WA-C")
    assert "Vi en su sitio que fabrican sobre pedido." in c.cuerpo


def test_evidencia_incompleta_no_genera_observacion():
    sin_url = [{"signal_type": "sobre_pedido", "signal_text": "t", "signal_source_url": ""}]
    sin_texto = [{"signal_type": "sobre_pedido", "signal_text": "", "signal_source_url": "http://x"}]
    for rows in (sin_url, sin_texto):
        assert m.obs_con_evidencia(rows) is None
        assert all("Vi en su sitio" not in m.primer_contacto(r(pid=str(i)), "whatsapp", rows).cuerpo for i in range(30))


def test_whatsapp_no_incluye_numero_de_yael_en_enlaces():
    from prospectos import contacto
    msg = m.primer_contacto(r(), "whatsapp", [])
    assert config.OWNER_WHATSAPP not in contacto.whatsapp_url("2221234567", msg.cuerpo)


@pytest.mark.parametrize("giro", GIROS)
@pytest.mark.parametrize("nombre", NOMBRES)
@pytest.mark.parametrize("pid", [str(i) for i in range(10)])
def test_correo_valido(giro, nombre, pid):
    msg = m.primer_contacto(r(giro, nombre, pid), "email")
    assert msg.valido, (msg.problemas, msg.asunto)
    assert m.palabras(msg.cuerpo) <= 120 and len(msg.asunto) <= 70 and "{" not in msg.cuerpo + msg.asunto
    assert msg.cuerpo.rstrip().endswith("WhatsApp: 220 570 4385") and config.OWNER_NAME in msg.cuerpo
    assert ("Audi" in msg.cuerpo) == msg.variante.startswith("EM-con")


def test_correo_reparte_credencial_y_asunto():
    v = {m.primer_contacto(r("Manufactura", "ACME SA", str(i)), "email").variante for i in range(80)}
    assert v == {"EM-con-A", "EM-con-B", "EM-sin-A", "EM-sin-B"}
    largo = m.primer_contacto(r(nombre="LOGISTICA Y TRANSPORTES INTEGRALES DEL CENTRO DE MEXICO SA DE CV"), "email")
    assert len(largo.asunto) <= 60 and largo.valido and largo.variante.endswith("-S")


@pytest.mark.parametrize("giro", GIROS)
def test_seguimientos_distintos_y_validos(giro):
    msgs = [m.seguimiento(r(giro), n) for n in (1, 2, 3)]
    assert all(x.valido for x in msgs) and len({x.cuerpo for x in msgs}) == 3
    assert [x.variante for x in msgs] == ["FU-d3", "FU-d7", "FU-d14"]
    assert "Cierro el tema" in msgs[2].cuerpo and "insistente" not in " ".join(x.cuerpo for x in msgs)


@pytest.mark.parametrize("texto,fragmento", [
    ("Hola {nombre}, ¿cómo están?", "variables sin renderizar"),
    ("Hola. Somos una empresa líder en soluciones. ¿Les interesa?", "prohibida"),
    ("Hola. Hacemos esto sin sistemas caros. ¿Les interesa?", "prohibida"),
    ("Hola, sé que usan Excel para todo. ¿Les interesa?", "no sustentada"),
    ("Hola. ¿Cómo están? ¿Les interesa?", "exactamente 1 pregunta"),
    ("Hola, mira https://yael.mx ¿Les interesa?", "enlaces"),
    ("Hola. Vi en su sitio que fabrican. ¿Les interesa?", "sin evidencia"),
    ("palabra " * 80 + "¿Les interesa?", "Demasiado largo"),
])
def test_validador_whatsapp_detecta(texto, fragmento):
    assert any(fragmento in p for p in m.validate_message(texto, "whatsapp", evidencia=False))


def test_validador_correo_exige_asunto_y_firma_y_avisa_asunto_largo():
    assert any("Falta el asunto" in p for p in m.validate_message("Hola\nYael de los Santos", "email", ""))
    assert any("firma" in p for p in m.validate_message("Hola", "email", "Asunto"))
    largo = m.validate_message("Hola\nYael de los Santos", "email", "a" * 65)
    assert largo == ["Aviso: asunto de 65 caracteres (ideal ≤ 60)"]
    assert m.Mensaje("email", "x", "c", "a", largo).valido
    assert any("Asunto largo" in p for p in m.validate_message("Hola\nYael de los Santos", "email", "a" * 80))
