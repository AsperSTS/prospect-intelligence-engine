"""Interfaz de línea de comandos: python -m prospectos <comando>."""
import argparse
from datetime import date

import pandas as pd

from . import acciones, db, pipeline
from .config import ENTIDADES, ESTRATOS, EXPORT_DIR, SECTORES, get_token
from .denue import DenueClient

COLS_EXPORT = ["nombre", "razon_social", "municipio", "entidad", "giro", "giro_display", "estrato", "tipo_establecimiento", "corredor_nombre",
               "fecha_alta", "fit_score", "priority_score", "canal", "telefono", "correo", "correo_web", "sitio", "possible_chain",
               "possible_chain_count", "group_reason", "hypothesis_text", "hypothesis_confidence", "estado", "proximo_seguimiento", "notas", "mensaje"]


def cmd_cuantificar(_):
    c = DenueClient(get_token())
    try:
        for ent, nom in ENTIDADES.items():
            if ent not in ("21", "29"):
                continue
            for sec, sub in SECTORES:
                print(f"{nom:9} sector {sec}/{sub}  " + "  ".join(f"{ESTRATOS[e]}:{c.cuantificar(sec, ent, e)}" for e in ESTRATOS))
    finally:
        c.close()


def cmd_pull(a):
    print(f"nuevos: {pipeline.pull(a.entidades, a.estratos, a.limite)}")


def cmd_analizar(_):
    print(f"analizados: {pipeline.analizar_todos()}")


def cmd_enriquecer(a):
    pipeline.enriquecer_pendientes(a.dominios, a.forzar)
    print(f"analizados: {pipeline.analizar_todos()}")


def cmd_run(a):
    pipeline.pull(a.entidades, None, a.limite)
    pipeline.analizar_todos()
    pipeline.enriquecer_pendientes(a.enriquecer)
    print(f"analizados: {pipeline.analizar_todos()}")


def cmd_daily(_):
    with db.conectar() as con:
        df = pd.read_sql_query("SELECT * FROM prospectos WHERE estado IN ('nuevo','revisado') ORDER BY priority_score DESC LIMIT 5", con)
        seg = db.seguimientos_pendientes(con)
    print(f"== {date.today()} · top 5 por prioridad · {len(seg)} seguimientos vencidos ==")
    for _, r in df.iterrows():
        print(f"\n[FIT {r['fit_score']} · PRIORIDAD {r['priority_score']}] {r['nombre'].title()} · {r['municipio']} · {r['giro']} · {r['estrato']}")
        print(f"  acción: {acciones.ROTULOS.get(r['canal'], r['canal'])} · {r['hypothesis_text']}")
        if r["possible_chain"]:
            print(f"  aviso: posible grupo ({r['possible_chain_count']}): {r['group_reason']}")
    for r in seg:
        print(f"\nSEGUIMIENTO {r['nombre'].title()} (toque {r['toques']}, desde {r['contactado_en']})")


def cmd_export(_):
    EXPORT_DIR.mkdir(exist_ok=True)
    with db.conectar() as con:
        df = pd.read_sql_query("SELECT * FROM prospectos ORDER BY priority_score DESC", con)
    ruta = EXPORT_DIR / f"prospectos_{date.today()}.xlsx"
    df[[c for c in COLS_EXPORT if c in df.columns]].to_excel(ruta, index=False)
    print(ruta)


def main():
    p = argparse.ArgumentParser(prog="prospectos")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("cuantificar").set_defaults(f=cmd_cuantificar)
    sub.add_parser("analizar", help="recalcula grupos, scores, hipótesis y mensajes").set_defaults(f=cmd_analizar)
    e = sub.add_parser("enriquecer", help="visita sitios web (máx. 5 páginas/dominio, caché de 30 días)")
    e.add_argument("--dominios", type=int, default=100)
    e.add_argument("--forzar", action="store_true", help="ignora la caché de 30 días")
    e.set_defaults(f=cmd_enriquecer)
    for nombre, f in (("pull", cmd_pull), ("run", cmd_run)):
        s = sub.add_parser(nombre)
        s.add_argument("--entidades", nargs="+", default=["21", "29"], choices=sorted(ENTIDADES))
        s.add_argument("--limite", type=int, default=None, help="máx. registros por consulta (pruebas)")
        if nombre == "pull":
            s.add_argument("--estratos", nargs="+", default=None, choices=sorted(ESTRATOS))
        else:
            s.add_argument("--enriquecer", type=int, default=100, help="dominios a visitar")
        s.set_defaults(f=f)
    sub.add_parser("daily").set_defaults(f=cmd_daily)
    sub.add_parser("export").set_defaults(f=cmd_export)
    a = p.parse_args()
    a.f(a)


main()
