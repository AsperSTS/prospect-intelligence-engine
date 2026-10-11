"""Clasificación por SCIAN: giro interno, nombre natural (giro_corto), puntos de ajuste e hipótesis base.

Todo es regla interna y determinista. La hipótesis es una suposición por giro, nunca un hecho sobre la empresa.
"""
import re
from dataclasses import dataclass

# giro -> (fit 0-25, complejidad base 0-14, hipótesis base). La hipótesis empieza con minúscula: se antepone "Por el giro ..., ".
GIRO_INFO = {
    "Autopartes": (25, 14, "podría haber fricción al consolidar información de producción y calidad para sus reportes."),
    "Equipo de transporte": (23, 13, "podría haber fricción al dar seguimiento al avance de cada orden durante la producción."),
    "Metalmecánica": (24, 13, "podría haber fricción al dar seguimiento a cotizaciones, órdenes de trabajo y costos de cada trabajo."),
    "Taller industrial": (22, 11, "podría haber fricción al dar seguimiento a órdenes de servicio y refacciones."),
    "Transporte": (20, 12, "podría haber fricción al controlar viajes, gastos y rentabilidad por unidad."),
    "Logística": (20, 12, "podría haber fricción al concentrar el estado de las entregas y los costos de cada ruta."),
    "Almacén": (18, 11, "podría haber fricción al registrar entradas, salidas y existencias."),
    "Constructora / contratista": (17, 11, "podría haber fricción al comparar el gasto real de cada obra contra su presupuesto."),
    "Comercializadora B2B": (15, 9, "podría haber fricción al conectar pedidos, existencias y seguimiento a clientes."),
    "Manufactura": (12, 11, "podría haber fricción al consolidar reportes de producción e inventario."),
    "Otro": (8, 5, "podría haber trabajo manual al consolidar reportes o procesos repetitivos."),
}

# prefijo SCIAN -> (giro, giro_display o None para derivarlo del nombre de la clase). Gana el prefijo más largo.
PREFIJOS = {
    "3363": ("Autopartes", "autopartes"),
    "336": ("Equipo de transporte", "equipo de transporte"),
    "3323": ("Metalmecánica", "estructuras metálicas y herrería"),
    "3327": ("Metalmecánica", "maquinado de piezas metálicas"),
    "332": ("Metalmecánica", "productos metálicos"),
    "331": ("Metalmecánica", "industria metálica básica"),
    "333": ("Metalmecánica", "maquinaria y equipo"),
    "31": ("Manufactura", None), "32": ("Manufactura", None), "33": ("Manufactura", None),
    "43": ("Comercializadora B2B", None),
    "484": ("Transporte", "transporte de carga"),
    "488": ("Logística", "servicios para el transporte"),
    "492": ("Logística", "mensajería y paquetería"),
    "493": ("Almacén", "almacenamiento y logística"),
    "23": ("Constructora / contratista", "construcción"),
    "811": ("Taller industrial", "reparación y mantenimiento"),
}
_ORDENADOS = sorted(PREFIJOS, key=len, reverse=True)

# bono de complejidad operativa por SCIAN (0-6), regla interna
BONO_COMPLEJIDAD = {"3363": 6, "332": 5, "333": 5, "336": 5, "484": 4, "493": 4, "811": 4, "488": 3, "23": 3, "43": 2}


@dataclass(frozen=True)
class Giro:
    giro: str
    display: str
    fit: int
    complejidad: int
    hipotesis: str


def display_desde_clase(nombre_clase: str, giro: str) -> str:
    """'Comercio al por mayor de abarrotes' -> 'distribución de abarrotes'; 'Fabricación de X' -> 'X' (máx. 6 palabras)."""
    s = re.sub(r"\s+", " ", (nombre_clase or "").strip()).lower()
    s = re.sub(r"^comercio al por mayor (de|a)\s+", "distribución de ", s)
    s = re.sub(r"^(fabricación|elaboración|servicios?) de\s+", "", s)
    s = " ".join(s.split(" ")[:6]).strip(" ,.;")
    return s or giro.lower()


def clasificar(clase_id: str, nombre_clase: str = "") -> Giro:
    giro, display = "Otro", None
    for pref in _ORDENADOS:
        if clase_id and clase_id.startswith(pref):
            giro, display = PREFIJOS[pref]
            break
    fit, base, hip = GIRO_INFO[giro]
    bono = next((BONO_COMPLEJIDAD[p] for p in sorted(BONO_COMPLEJIDAD, key=len, reverse=True) if clase_id and clase_id.startswith(p)), 0)
    return Giro(giro, display or display_desde_clase(nombre_clase, giro), fit, min(base + bono, 20), hip)


def hipotesis(g: Giro, evidencias: list[str]) -> tuple[str, str, str]:
    """(texto, base, confianza). La confianza solo sube con evidencia web concreta: 1-2 menciones = media, 3+ = alta.
    Las menciones prueban el vocabulario del sitio, no el problema: por eso la hipótesis nunca se presenta como dato."""
    if evidencias:
        quees = ", ".join(evidencias[:3])
        texto = f"Por el giro ({g.display}) y porque el sitio menciona {quees}, {g.hipotesis}"
        base = f"Giro SCIAN + evidencia web: {quees}"
        conf = "alta" if len(evidencias) >= 3 else "media"
    else:
        texto = f"Por el giro ({g.display}), {g.hipotesis}"
        base = "Solo giro SCIAN; sin evidencia web"
        conf = "baja"
    return texto, base, conf
