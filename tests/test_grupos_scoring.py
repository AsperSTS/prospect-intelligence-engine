import sys
from datetime import date, timedelta
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from prospectos import acciones, giros, grupos, scoring  # noqa: E402


def f(i, **kw):
    base = {"id": str(i), "nombre": f"EMPRESA {i}", "razon_social": "", "sitio": "", "telefono": "", "entidad": "Puebla"}
    base.update(kw)
    return base


def test_normalizar_quita_sufijos_y_acentos_solo_para_comparar():
    assert grupos.normalizar("Aceros del Tóro, S.A. de C.V.") == "aceros del toro"
    assert grupos.normalizar("MAQUINAS DIESEL SUC. PUEBLA") == "maquinas diesel"
    assert grupos.normalizar("Metales S. de R.L. de C.V.") == "metales"


def test_misma_razon_social_y_dominio_agrupan_con_motivo():
    filas = [f(1, razon_social="ACEROS DEL TORO SA DE CV", sitio="www.toro.mx"), f(2, razon_social="Aceros del Toro, S.A. de C.V.", sitio="toro.mx"),
             f(3, razon_social="OTRA SA", sitio="otra.mx")]
    g = grupos.agrupar(filas)
    assert g["1"]["possible_chain"] == 1 and g["1"]["possible_chain_count"] == 2 and g["1"]["group_key"] == g["2"]["group_key"]
    assert "misma razón social" in g["1"]["group_reason"] and "mismo dominio web" in g["1"]["group_reason"]
    assert g["3"]["possible_chain"] == 0 and g["3"]["group_reason"] == ""


def test_nombres_parecidos_sin_evidencia_no_agrupan_fuerte():
    filas = [f(1, nombre="MAQUINAS DIESEL"), f(2, nombre="MAQUINAS DIESEL", entidad="Tlaxcala")]
    g = grupos.agrupar(filas)
    assert all(v["possible_chain"] == 0 for v in g.values())


def test_mismo_nombre_tres_veces_es_indicio_debil_visible():
    g = grupos.agrupar([f(i, nombre="BODEGA CENTRO") for i in range(3)])
    assert g["0"]["possible_chain"] == 1 and "débil" in g["0"]["group_reason"] and g["0"]["possible_chain_count"] == 3


def test_dominios_genericos_y_razon_social_vacia_no_agrupan():
    filas = [f(1, sitio="facebook.com/a"), f(2, sitio="facebook.com/b"), f(3, razon_social="SIN RAZON SOCIAL"), f(4, razon_social="SIN RAZON SOCIAL")]
    assert all(v["possible_chain"] == 0 for v in grupos.agrupar(filas).values())


def test_telefono_repetido_agrupa():
    g = grupos.agrupar([f(1, telefono="2221112233"), f(2, telefono="(222) 111-2233")])
    assert g["1"]["possible_chain"] == 1 and "mismo teléfono" in g["1"]["group_reason"]


def row(**kw):
    base = {"estrato": "31 a 50 personas", "tipo_establecimiento": "Fijo", "corredor_nombre": "", "corredor_tipo": "", "correo": "", "correo_web": "",
            "telefono": "", "whatsapp": "", "sitio": "", "estado": "nuevo", "possible_chain": 0, "proximo_seguimiento": None,
            "website_checked_at": None, "creado_en": "2020-01-01"}
    base.update(kw)
    return base


def test_fit_rango_y_desglose_suma():
    g = giros.clasificar("336360", "x")
    pts, items = scoring.fit(row(corredor_nombre="FINSA"), g, ["sobre_pedido", "cotizacion"])
    assert 0 <= pts <= 100 and pts == sum(i["pts"] for i in items)
    assert all(0 <= i["pts"] <= i["max"] for i in items) and sum(i["max"] for i in items) == 100


def test_fit_tipo_reglas():
    g = giros.clasificar("332710", "")
    pts = lambda **kw: {i["clave"]: i["pts"] for i in scoring.fit(row(**kw), g, [])[1]}  # noqa: E731
    assert (pts(tipo_establecimiento="")["tipo"], pts(tipo_establecimiento="Semifijo")["tipo"], pts()["tipo"]) == (4, 0, 10)


@pytest.mark.parametrize("nombre,tipo,esperado", [
    ("PARQUE INDUSTRIAL FINSA PUEBLA", "PARQUE INDUSTRIAL", 15),      # industrial identificado
    ("ZONA INDUSTRIAL SANCTORUM", "ZONA INDUSTRIAL", 15),
    ("SIN NOMBRE", "PARQUE INDUSTRIAL", 10),                          # tipo industrial sin nombre = zona compatible
    ("PARQUE INDUSTRIAL FINSA PUEBLA", "HOTELES", 10),                # dato ruidoso: el nombre delata zona industrial
    ("PLAZA COMERCIAL CAPU", "CENTRO Y PLAZA COMERCIAL", 0),          # comercial no es industrial
    ("EDIFICIO COMERCIAL SIN NOMBRE", "MERCADO PUBLICO", 0),
    ("LA GRAN BODEGA", "CENTRAL DE ABASTO", 0),
    ("", "", 0),
])
def test_corredor_solo_suma_si_es_industrial(nombre, tipo, esperado):
    g = giros.clasificar("332710", "")
    d = {i["clave"]: i["pts"] for i in scoring.fit(row(corredor_nombre=nombre, corredor_tipo=tipo), g, [])[1]}
    assert d["corredor"] == esperado


def test_fit_senales_tope_10():
    g = giros.clasificar("336360", "")
    items = {i["clave"]: i["pts"] for i in scoring.fit(row(), g, ["sobre_pedido", "cotizacion", "inventario", "logistica", "almacen"])[1]}
    assert items["senales"] == 10


def prio(r, fit=80, tipos=(), grupo=False, hoy=None):
    return scoring.priority(r, fit, list(tipos), grupo, hoy)


def test_prioridad_rango_desglose_y_pesos():
    r = row(correo="v@acme.mx", telefono="2221234567", sitio="acme.mx")
    pts, items, excl = prio(r, 80, ["sobre_pedido"])
    assert not excl and 0 <= pts <= 100 and pts == sum(i["pts"] for i in items)
    d = {i["clave"]: i["pts"] for i in items}
    assert d["fit"] == 28 and d["contacto"] == 30 and d["contexto"] == 20 and d["estado"] == 5


@pytest.mark.parametrize("estado", ["no_interesado", "descartado", "sin_respuesta", "cliente"])
def test_cerrados_quedan_fuera(estado):
    pts, _, excl = prio(row(estado=estado, correo="v@acme.mx"))
    assert excl and pts == 0


def test_seguimiento_vencido_sube_y_contactado_reciente_baja():
    base = dict(correo="v@acme.mx", telefono="2221234567")
    ayer = (date.today() - timedelta(days=1)).isoformat()
    manana = (date.today() + timedelta(days=1)).isoformat()
    nuevo = prio(row(**base))[0]
    vencido = prio(row(estado="contactado", proximo_seguimiento=ayer, **base))[0]
    reciente = prio(row(estado="contactado", proximo_seguimiento=manana, **base))[0]
    assert vencido > nuevo > reciente


def test_posible_grupo_ya_contactado_penaliza_y_sin_canal_penaliza():
    base = dict(correo="v@acme.mx", possible_chain=1)
    assert prio(row(**base), grupo=True)[0] == prio(row(**base), grupo=False)[0] - 15
    assert {i["clave"]: i["pts"] for i in prio(row())[1]}["estado"] == -5  # +5 nuevo, -10 sin canal


def test_respondio_requiere_accion():
    d = {i["clave"]: i["pts"] for i in prio(row(estado="respondio", correo="v@acme.mx"))[1]}
    assert d["estado"] == 15


@pytest.mark.parametrize("r,fit,tipos", [
    (row(estado="revisado"), 0, []),
    (row(estado="respondio", correo="v@acme.mx", telefono="2221234567", sitio="acme.mx",
         website_checked_at=date.today().isoformat(), creado_en=date.today().isoformat()), 100, ["sobre_pedido"]),
])
def test_limites_de_prioridad_mantienen_desglose_explicable(r, fit, tipos):
    pts, items, excl = prio(r, fit, tipos)
    assert not excl and pts in (0, 100)
    assert sum(i["pts"] for i in items) == pts
    assert any(i["clave"] == "limite" for i in items)


def nba(r, fit=70, senal=False):
    return acciones.recommend_next_action({"nombre": "Metales del Centro", "giro": "Metalmecánica", "toques": 1, **r}, fit, senal)


def test_email_si_hay_email_y_fit_alto():
    a = nba(row(correo="v@acme.mx"), senal=True)
    assert a["action"] == "email" and a["confidence"] == "alta" and "contexto web" in a["reason"]


def test_telefono_si_no_hay_email():
    a = nba(row(telefono="2221234567"))
    assert a["action"] == "telefono" and "whatsapp_or_copy" in a["alternativas"]


def test_revision_manual_por_cadena_giro_dudoso_o_fit_sin_contacto():
    assert nba(row(correo="v@acme.mx", possible_chain=1, group_reason="mismo dominio web"))["action"] == "manual_review"
    assert nba(row(correo="v@acme.mx"), fit=70)["action"] == "email"
    assert nba(row(), fit=80)["action"] == "manual_review"                       # score alto sin contacto claro
    assert nba(row(correo="v@acme.mx", giro="Otro"))["action"] == "manual_review"
    assert nba(row(correo="v@acme.mx"), fit=20)["action"] == "skip"


def test_follow_up_vencido_y_cerrados():
    ayer = (date.today() - timedelta(days=1)).isoformat()
    assert nba(row(estado="contactado", proximo_seguimiento=ayer, correo="v@acme.mx"))["action"] == "follow_up"
    assert nba(row(estado="contactado", proximo_seguimiento=(date.today() + timedelta(days=2)).isoformat()))["action"] == "skip"
    assert nba(row(estado="descartado"))["action"] == "skip"
    assert nba(row(estado="respondio"))["action"] == "manual_review"
