"""Agrupación probable de establecimientos (posible cadena/grupo). Reglas deterministas y explicables.

DENUE lista establecimientos, no empresas. La agrupación es una ayuda para revisión humana:
nunca se afirma que existan sucursales, solo "posible grupo" con su motivo visible.
"""
import re
import unicodedata
from collections import Counter, defaultdict

from . import contacto

_LEGAL = re.compile(r"\b(sapi de cv|sapi|sa de cv|sa|s de rl de cv|s de rl|sc de rl|sc|ac|sas)$")
_SUCURSAL = re.compile(r"\b(sucursal|suc)\b.*$")
_GENERICAS = {"", "sin razon social", "no disponible", "ninguna", "ninguno", "na", "n a"}
PRIORIDAD = ("rs", "web", "tel")  # fuerza de la llave: razón social > dominio > teléfono
ROTULO = {"rs": "misma razón social", "web": "mismo dominio web", "tel": "mismo teléfono"}


def normalizar(texto: str) -> str:
    """Solo para comparar (el nombre original nunca se sobrescribe): minúsculas, sin acentos ni puntuación ni sufijo legal."""
    s = unicodedata.normalize("NFKD", texto or "").encode("ascii", "ignore").decode().lower()
    s = s.replace(".", "")
    s = re.sub(r"[^a-z0-9 ]", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    s = _SUCURSAL.sub("", s).strip()
    for _ in range(3):
        nuevo = _LEGAL.sub("", s).strip()
        if nuevo == s:
            break
        s = nuevo
    return s


def _llaves(r: dict) -> dict[str, str | None]:
    rs = normalizar(r.get("razon_social", ""))
    tel = contacto.telefono_mx(r.get("telefono", ""))
    return {
        "rs": rs if rs not in _GENERICAS and len(rs) >= 5 else None,
        "web": contacto.dominio(r.get("sitio", "")),
        "tel": tel or None,
    }


def agrupar(filas: list[dict]) -> dict[str, dict]:
    """filas: dicts con id, nombre, razon_social, sitio, telefono, entidad. Devuelve id -> campos de grupo."""
    padre = {r["id"]: r["id"] for r in filas}

    def raiz(x):
        while padre[x] != x:
            padre[x] = padre[padre[x]]
            x = padre[x]
        return x

    llaves = {r["id"]: _llaves(r) for r in filas}
    for tipo in PRIORIDAD:
        por_llave = defaultdict(list)
        for pid, k in llaves.items():
            if k[tipo]:
                por_llave[k[tipo]].append(pid)
        for miembros in por_llave.values():
            for otro in miembros[1:]:
                padre[raiz(otro)] = raiz(miembros[0])

    comps = defaultdict(list)
    for r in filas:
        comps[raiz(r["id"])].append(r["id"])

    nombre_estado = Counter()
    nom_de = {}
    for r in filas:
        nom_de[r["id"]] = f"{normalizar(r.get('nombre', ''))}|{r.get('entidad', '')}"
        nombre_estado[nom_de[r["id"]]] += 1

    salida = {}
    for miembros in comps.values():
        n = len(miembros)
        if n >= 2:
            # solo cuentan las llaves que realmente enlazan a ≥2 miembros del componente
            vinculos = {}
            for tipo in PRIORIDAD:
                c = Counter(llaves[m][tipo] for m in miembros if llaves[m][tipo])
                comunes = [v for v, k in c.items() if k >= 2]
                if comunes:
                    vinculos[tipo] = comunes[0]
            motivo = " + ".join(ROTULO[t] for t in PRIORIDAD if t in vinculos)
            fuerte = next(t for t in PRIORIDAD if t in vinculos)
            for m in miembros:
                salida[m] = {"group_key": f"{fuerte}:{vinculos[fuerte]}", "possible_chain": 1, "possible_chain_count": n, "group_reason": motivo}
        else:
            m = miembros[0]
            nk = nom_de[m]
            veces = nombre_estado[nk]
            if veces >= 3 and not nk.startswith("|"):   # nombre repetido sin otra evidencia: indicio débil
                salida[m] = {"group_key": f"nom:{nk}", "possible_chain": 1, "possible_chain_count": veces,
                             "group_reason": f"mismo nombre en {veces} establecimientos del estado (indicio débil)"}
            else:
                salida[m] = {"group_key": f"id:{m}", "possible_chain": 0, "possible_chain_count": 1, "group_reason": ""}
    return salida
