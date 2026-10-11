import sqlite3
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from prospectos import config, contacto, db, giros  # noqa: E402
from prospectos.denue import Establecimiento  # noqa: E402
from prospectos.pipeline import _fila  # noqa: E402


@pytest.fixture
def tmpdb(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "DATA_DIR", tmp_path)
    monkeypatch.setattr(config, "DB_PATH", tmp_path / "t.db")
    monkeypatch.setattr(config, "BACKUP_DIR", tmp_path / "backups")
    return tmp_path


def _fila_db(i="1", **kw):
    base = {"id": i, "nombre": f"EMPRESA {i}", "razon_social": "", "giro": "Autopartes", "clase_actividad": "Fabricación de partes",
            "clase_id": "336360", "rama_id": "3363", "subrama_id": "33636", "estrato": "31 a 50 personas", "tipo_establecimiento": "Fijo",
            "corredor_nombre": "", "corredor_tipo": "", "entidad": "Puebla", "municipio": "Puebla", "localidad": "Puebla", "direccion": "",
            "calle": "", "num_exterior": "", "num_interior": "", "edificio": "", "numero_local": "", "cp": "", "telefono": "2221234567",
            "correo": "", "sitio": "", "dominio": None, "latitud": None, "longitud": None, "fecha_alta": "2020-01"}
    base.update(kw)
    return base


_fila = _fila_db  # compat con otros tests


def test_esquema_denue_tolera_campos_extra_y_exige_id():
    e = Establecimiento.model_validate({"Id": "1", "Nombre": "X", "Extra": "y", "Tipo": "Fijo", "nom_corredor_industrial": "FINSA"})
    assert (e.id, e.tipo_establecimiento, e.corredor_nombre) == ("1", "Fijo", "FINSA")
    with pytest.raises(Exception):
        Establecimiento.model_validate({"Nombre": "X"})


def test_campos_faltantes_no_rompen_importacion():
    f = _fila_denue({"Id": "9", "Nombre": "Solo nombre"})
    assert f["nombre"] == "Solo nombre" and f["telefono"] == "" and f["latitud"] is None and f["dominio"] is None


def _fila_denue(raw):
    import prospectos.pipeline as p
    return p._fila(Establecimiento.model_validate(raw), "21")


def test_coordenadas_invalidas_quedan_null_y_nombre_se_conserva():
    f = _fila_denue({"Id": "1", "Nombre": " ACEROS DEL TORO SA DE CV ", "Latitud": "0.0", "Longitud": "abc"})
    assert f["latitud"] is None and f["longitud"] is None and f["nombre"] == "ACEROS DEL TORO SA DE CV"
    ok = _fila_denue({"Id": "2", "Nombre": "X", "Latitud": "19.04", "Longitud": "-98.2"})
    assert (ok["latitud"], ok["longitud"]) == (19.04, -98.2)


def test_fecha_alta_se_guarda_tal_cual_sin_convertir_a_edad():
    f = _fila_denue({"Id": "1", "Nombre": "X", "Fecha_Alta": "2018-03"})
    assert f["fecha_alta"] == "2018-03" and "antig" not in " ".join(f)


def test_clasificar_giros_y_display():
    assert giros.clasificar("336360", "x").giro == "Autopartes"
    assert giros.clasificar("332710", "x").giro == "Metalmecánica"
    assert giros.clasificar("484110", "x").display == "transporte de carga"
    assert giros.clasificar("999999", "Servicios de algo raro").giro == "Otro"
    assert giros.clasificar("431110", "Comercio al por mayor de abarrotes").display == "distribución de abarrotes"


def test_hipotesis_confianza_sube_solo_con_evidencia():
    g = giros.clasificar("332710", "")
    assert giros.hipotesis(g, [])[2] == "baja"
    assert giros.hipotesis(g, ["cotizaciones"])[2] == "media"
    assert giros.hipotesis(g, ["cotizaciones", "inventario"])[2] == "media"
    texto, _, conf = giros.hipotesis(g, ["cotizaciones", "inventario", "almacén"])
    assert conf == "alta" and "podría" in texto and "sé que" not in texto


def test_telefono_y_whatsapp_apunta_al_prospecto_no_a_yael():
    assert contacto.telefono_mx("(222) 123-4567") == "2221234567"
    assert contacto.telefono_mx("52 222 123 4567") == "2221234567"
    assert contacto.telefono_mx("123") == ""
    url = contacto.whatsapp_url("2221234567", "hola ñ")
    assert url.startswith("https://wa.me/522221234567?text=hola%20") and config.OWNER_WHATSAPP not in url
    assert contacto.whatsapp_url("12345", "x") == ""


def test_dominio_ignora_genericos():
    assert contacto.dominio("WWW.ACME.COM.MX") == "acme.com.mx"
    assert contacto.dominio("https://facebook.com/acme") is None
    assert contacto.dominio("acme.wixsite.com/x") is None
    assert contacto.dominio("192.168.0.1") is None


def test_migracion_respalda_y_conserva(tmpdb):
    con = sqlite3.connect(config.DB_PATH)
    con.execute("CREATE TABLE prospectos (id TEXT PRIMARY KEY, nombre TEXT NOT NULL, estado TEXT DEFAULT 'nuevo', toques INTEGER DEFAULT 0)")
    con.execute("INSERT INTO prospectos (id, nombre, estado, toques) VALUES ('a','A','contactar',0), ('b','B','ganado',2)")
    con.commit(); con.close()
    with db.conectar() as c:
        assert c.execute("PRAGMA user_version").fetchone()[0] == db.SCHEMA_VERSION
        assert {r["id"]: r["estado"] for r in c.execute("SELECT id, estado FROM prospectos")} == {"a": "revisado", "b": "cliente"}
        assert c.execute("SELECT count(*) FROM interactions WHERE prospect_id='b'").fetchone()[0] == 1  # contacto previo migrado
    assert len(list(config.BACKUP_DIR.glob("*.db"))) == 1
    with db.conectar():
        pass
    assert len(list(config.BACKUP_DIR.glob("*.db"))) == 1  # no respalda de nuevo


def test_upsert_no_pisa_crm(tmpdb):
    with db.conectar() as con:
        assert db.upsert_denue(con, [_fila_db()]) == (1, 0)
        db.registrar_contacto(con, "1", "email", "EM-con-A", "texto", "nota")
        assert db.upsert_denue(con, [_fila_db(nombre="NUEVO")]) == (0, 1)
        r = con.execute("SELECT nombre, estado, notas, proximo_seguimiento FROM prospectos").fetchone()
        assert (r["nombre"], r["estado"], r["notas"]) == ("NUEVO", "contactado", "nota") and r["proximo_seguimiento"]


def test_contactar_crea_interaccion_y_programa_d3(tmpdb):
    from datetime import date, timedelta
    with db.conectar() as con:
        db.upsert_denue(con, [_fila_db()])
        db.registrar_contacto(con, "1", "whatsapp", "WA-A", "hola")
        h = db.historial(con, "1")
        assert len(h) == 1 and (h[0]["interaction_type"], h[0]["sequence_step"], h[0]["template_variant"], h[0]["message_rendered"]) == ("contacto", 0, "WA-A", "hola")
        assert con.execute("SELECT proximo_seguimiento FROM prospectos").fetchone()[0] == (date.today() + timedelta(days=3)).isoformat()


def test_secuencia_d3_d7_d14_y_cierre(tmpdb):
    from datetime import date, timedelta
    with db.conectar() as con:
        db.upsert_denue(con, [_fila_db()])
        db.registrar_contacto(con, "1", "email", "EM", "x")
        prox = lambda: con.execute("SELECT proximo_seguimiento FROM prospectos").fetchone()[0]  # noqa: E731
        assert db.registrar_seguimiento(con, "1", "email", "FU-d3", "x") == "contactado"
        assert prox() == (date.today() + timedelta(days=4)).isoformat()      # D+7 desde el primer contacto
        assert db.registrar_seguimiento(con, "1", "email", "FU-d7", "x") == "contactado"
        assert prox() == (date.today() + timedelta(days=7)).isoformat()      # D+14
        assert db.registrar_seguimiento(con, "1", "email", "FU-d14", "x") == "sin_respuesta"
        r = con.execute("SELECT estado, proximo_seguimiento FROM prospectos").fetchone()
        assert r["estado"] == "sin_respuesta" and r["proximo_seguimiento"] is None


@pytest.mark.parametrize("tipo,estado", [("interesado", "respuesta_positiva"), ("redirigido", "respondio"), ("no_interesado", "no_interesado"),
                                         ("ya_tienen_solucion", "no_interesado"), ("correo_rebotado", "revisado")])
def test_respuesta_cancela_seguimientos(tmpdb, tipo, estado):
    with db.conectar() as con:
        db.upsert_denue(con, [_fila_db()])
        db.registrar_contacto(con, "1", "email", "EM", "x")
        assert db.registrar_respuesta(con, "1", tipo, "nota") == estado
        r = con.execute("SELECT proximo_seguimiento FROM prospectos").fetchone()
        assert r[0] is None
        assert db.seguimientos_pendientes(con) == []
        assert con.execute("SELECT response_type FROM interactions WHERE interaction_type='respuesta'").fetchone()[0] == tipo


def test_estado_invalido_y_respuesta_invalida(tmpdb):
    with db.conectar() as con:
        db.upsert_denue(con, [_fila_db()])
        with pytest.raises(ValueError):
            db.cambiar_estado(con, "1", "hackeado")
        with pytest.raises(ValueError):
            db.registrar_respuesta(con, "1", "inventada")


def test_actividad_y_progreso(tmpdb):
    with db.conectar() as con:
        db.upsert_denue(con, [_fila_db("1"), _fila_db("2")])
        db.registrar_contacto(con, "1", "email", "EM", "x")      # investigado + contacto
        db.cambiar_estado(con, "2", "descartado")                  # investigado
        db.registrar_seguimiento(con, "1", "email", "FU", "x")
        db.registrar_actividad(con, "publicacion")
        assert db.progreso_hoy(con) == {"investigado": 2, "contacto": 1, "publicacion": 1, "seguimiento": 1}
        db.cambiar_estado(con, "1", "respondio")                   # ya no es nuevo: no duplica
        assert db.progreso_hoy(con)["investigado"] == 2
