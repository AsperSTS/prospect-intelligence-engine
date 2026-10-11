"""Renderizado y validación de mensajes. Determinista, sin LLM. Los textos viven en config/templates.toml.

Receta RAPID: un Reconocimiento real, Autoridad mínima, una Pregunta, Intervención pequeña, Descompresión.
El primer mensaje busca información, no cerrar una venta. Solo se afirma lo verificable: {obs} exige evidencia pública con URL.
"""
import hashlib
import re
import tomllib
from dataclasses import dataclass, field

from . import config, senales

REQUERIDOS = {"whatsapp": ["A", "B", "C", "D"], "email": ["asunto_A", "asunto_B", "cuerpo_con_credencial", "cuerpo_sin_credencial"],
              "seguimiento": ["d3", "d7", "d14"]}
CAMPOS_GIRO = ("cosa", "pregunta", "ejemplo")
PALABRAS_MAX = {"whatsapp": 65, "email": 120, "seguimiento": 80}
ASUNTO_MAX = 70      # límite duro; el ideal (≤ 60) genera solo un aviso
ASUNTO_IDEAL = 60

PROHIBIDAS = [
    "espero que se encuentre muy bien", "me pongo en contacto con usted para", "somos una empresa líder", "empresa líder",
    "soluciones innovadoras de vanguardia", "transformación digital integral", "sin sistemas caros", "ahorre tiempo y dinero",
    "tiene 15 minutos mañana", "última oportunidad", "sé que está ocupado", "no quiero ser insistente", "solo quería dar seguimiento",
    "solo doy seguimiento", "vio mi mensaje", "somos expertos", "amplia experiencia", "aproveche esta oportunidad", "solo esta semana",
    "llamada urgente", "estuve investigando mucho", "increíble trayectoria",
]
# afirmaciones sobre la empresa que no podemos sustentar
CLAIMS_NO_SUSTENTADOS = [r"\bsé que\b", r"\bsabemos que\b", r"\bsabía que\b", r"\busan excel\b", r"\bpierden (horas|tiempo)\b",
                         r"\btienen problemas\b", r"\bhacen reportes manuales\b", r"\btodavía (usan|pierden)\b"]


class PlantillaInvalida(Exception):
    pass


_cache: dict = {"mtime": None, "datos": None}


def plantillas() -> dict:
    """Carga config/templates.toml (se recarga al detectar cambios) y verifica que estén todas las claves."""
    try:
        mtime = config.TEMPLATES_PATH.stat().st_mtime
    except FileNotFoundError:
        raise PlantillaInvalida(f"No existe {config.TEMPLATES_PATH}") from None
    if _cache["mtime"] != mtime:
        datos = tomllib.loads(config.TEMPLATES_PATH.read_text(encoding="utf-8"))
        for seccion, claves in REQUERIDOS.items():
            faltan = [k for k in claves if k not in datos.get(seccion, {})]
            if faltan:
                raise PlantillaInvalida(f"Faltan en [{seccion}]: {', '.join(faltan)}")
        for giro, c in datos.get("giros", {}).items():
            faltan = [k for k in CAMPOS_GIRO if k not in c]
            if faltan:
                raise PlantillaInvalida(f"Giro '{giro}' sin: {', '.join(faltan)}")
        if "Otro" not in datos.get("giros", {}):
            raise PlantillaInvalida("Falta el giro 'Otro' (respaldo)")
        _cache.update(mtime=mtime, datos=datos)
    return _cache["datos"]


# ----------------------------------------------------------------------------- nombres
_MINUSCULAS = {"de", "del", "la", "las", "los", "el", "y", "e", "en", "para", "por", "con", "al"}
_CORTAS_NORMALES = {"san", "sur", "luz", "oro", "rio", "gas", "sol", "mar", "pan", "uno", "dos", "sin", "mas", "una", "ver", "mex", "don", "doña"}
_ONSETS = {"pl", "pr", "bl", "br", "cl", "cr", "dr", "fl", "fr", "gl", "gr", "tr", "ch", "ll", "rr"}
_LEGAL = re.compile(
    r"[\s,.]+(S\.?\s?A\.?\s?P\.?\s?I\.?(\s?DE\s?C\.?\s?V\.?)?|S\.?\s?A\.?(\s?DE\s?C\.?\s?V\.?)?|S\.?\s?DE\s?R\.?\s?L\.?(\s?DE\s?C\.?\s?V\.?)?|S\.?\s?C\.?|A\.?\s?C\.?)\s*$",
    re.I)


def _es_sigla(w: str, base: str) -> bool:
    if not (w.isalpha() and w.isupper()) or base in _CORTAS_NORMALES:
        return False
    if len(w) <= 3:
        return True
    return len(w) == 4 and w[0] not in "AEIOU" and w[1] not in "AEIOU" and base[:2] not in _ONSETS


def limpiar_nombre(raw: str) -> str:
    """'MAQUINAS DIESEL SUC. PUEBLA S.A. DE C.V.' → 'Maquinas Diesel'. Solo para mostrar: el nombre original no se modifica."""
    s = re.split(r"\b(?:SUCURSAL|SUC\.?)(?=\s|$)", raw, flags=re.I)[0]
    s = re.sub(r"\s+", " ", s).strip(" ,.-")
    for _ in range(3):
        nuevo = _LEGAL.sub("", s).strip(" ,.-")
        if nuevo == s:
            break
        s = nuevo
    palabras_ = []
    for i, w in enumerate(s.split(" ")):
        base = w.strip(".,").lower()
        if base in _MINUSCULAS and i > 0:
            palabras_.append(base)
        elif _es_sigla(w, base):
            palabras_.append(w)
        else:
            palabras_.append(w.capitalize() if w.isupper() or w.islower() else w)
    return " ".join(palabras_) or raw.title()


def palabras(texto: str) -> int:
    return len(re.findall(r"\S+", texto))


# ----------------------------------------------------------------------------- variantes
def _h(pid: str) -> int:
    return int(hashlib.sha1(pid.encode()).hexdigest(), 16)


def elegir_variantes(pid: str, hay_obs: bool) -> dict:
    """Reparto determinista y estable. La variante C solo existe si hay evidencia web; se compara de a una variable."""
    h = _h(pid)
    opciones = ["A", "B", "D"] + (["C"] if hay_obs else [])
    return {"whatsapp": opciones[h % len(opciones)],
            "email_credencial": (h // 7) % 2 == 0,
            "email_asunto": "A" if (h // 13) % 2 == 0 else "B"}


# ----------------------------------------------------------------------------- render
@dataclass
class Mensaje:
    canal: str                 # whatsapp | email | seguimiento
    variante: str              # p. ej. WA-A · EM-con-A · FU-d3
    cuerpo: str
    asunto: str = ""
    problemas: list[str] = field(default_factory=list)

    @property
    def valido(self) -> bool:
        """Válido = sin errores. Los «Aviso:» no bloquean."""
        return not any(not p.startswith("Aviso:") for p in self.problemas)


def _sub(texto: str, vars_: dict) -> str:
    return re.sub(r"\{(\w+)\}", lambda m: str(vars_.get(m.group(1), m.group(0))), texto).strip()


def _vars(r: dict, obs: str = "") -> dict:
    t = plantillas()
    g = t["giros"].get(r.get("giro") or "Otro", t["giros"]["Otro"])
    return {
        "nombre": limpiar_nombre(r.get("nombre", "")), "giro_corto": r.get("giro_display") or (r.get("giro") or "").lower() or "su sector",
        "cosa": g["cosa"], "pregunta": g["pregunta"], "ejemplo": g["ejemplo"], "obs": obs, "credencial": config.OWNER_CREDENTIAL,
        "owner": config.OWNER_NAME, "owner_corto": config.OWNER_NAME.split()[0], "whatsapp": _tel_firma(config.OWNER_WHATSAPP),
    }


def _tel_firma(n: str) -> str:
    return f"{n[:3]} {n[3:6]} {n[6:]}" if len(n) == 10 else n


def obs_con_evidencia(senales_rows: list[dict]) -> tuple[str, str] | None:
    """Solo señales con URL de origen y texto de evidencia pueden convertirse en observación. Sin evidencia → None."""
    con_evidencia = [s["signal_type"] for s in senales_rows if s.get("signal_source_url") and s.get("signal_text")]
    return senales.observacion(con_evidencia)


def primer_contacto(r: dict, canal: str, senales_rows: list[dict] | None = None) -> Mensaje:
    """r: fila del prospecto (id, nombre, giro, giro_display...). canal: 'whatsapp' | 'email'."""
    t = plantillas()
    obs = obs_con_evidencia(senales_rows or [])
    v = elegir_variantes(r["id"], hay_obs=obs is not None)
    if canal == "whatsapp":
        letra = v["whatsapp"]
        cuerpo = _sub(t["whatsapp"][letra], _vars(r, obs[1] if obs else ""))
        m = Mensaje("whatsapp", f"WA-{letra}", cuerpo)
    else:
        clave = "cuerpo_con_credencial" if v["email_credencial"] else "cuerpo_sin_credencial"
        vars_ = _vars(r)
        otra = "B" if v["email_asunto"] == "A" else "A"
        candidatos = [(v["email_asunto"], _sub(t["email"][f"asunto_{v['email_asunto']}"], vars_)), (otra, _sub(t["email"][f"asunto_{otra}"], vars_)),
                      ("S", f"Pregunta sobre {vars_['nombre']}"), ("S", "Una pregunta sobre sus procesos")]
        letra, asunto = next(((l, a) for l, a in candidatos if len(a) <= ASUNTO_IDEAL), candidatos[-1])  # acorta solo si el nombre es largo
        m = Mensaje("email", f"EM-{'con' if v['email_credencial'] else 'sin'}-{letra}", _sub(t["email"][clave], vars_), asunto)
    m.problemas = validate_message(m.cuerpo, m.canal, m.asunto, evidencia=obs is not None)
    return m


def seguimiento(r: dict, paso: int) -> Mensaje:
    """paso 1 = D+3 · 2 = D+7 · 3 = D+14. Cada uno aporta algo nuevo."""
    clave = {1: "d3", 2: "d7"}.get(paso, "d14")
    cuerpo = _sub(plantillas()["seguimiento"][clave], _vars(r))
    m = Mensaje("seguimiento", f"FU-{clave}", cuerpo)
    m.problemas = validate_message(m.cuerpo, "seguimiento")
    return m


# ----------------------------------------------------------------------------- validación
def validate_message(texto: str, canal: str, asunto: str = "", evidencia: bool = False) -> list[str]:
    """Devuelve la lista de problemas (vacía = válido). Se ejecuta antes de mostrar cualquier mensaje."""
    problemas = []
    low = texto.lower()
    if re.search(r"\{\w+\}", texto) or re.search(r"\{\w+\}", asunto):
        problemas.append("Quedan variables sin renderizar: " + ", ".join(sorted(set(re.findall(r"\{\w+\}", texto + asunto)))))
    n, tope = palabras(texto), PALABRAS_MAX.get(canal, 80)
    if n > tope:
        problemas.append(f"Demasiado largo: {n} palabras (máx. {tope})")
    for f in PROHIBIDAS:
        if f in low:
            problemas.append(f"Frase prohibida: «{f}»")
    for rx in CLAIMS_NO_SUSTENTADOS:
        if re.search(rx, low):
            problemas.append("Afirmación no sustentada sobre la empresa")
            break
    if "vi en su sitio" in low and not evidencia:
        problemas.append("Cita el sitio web sin evidencia registrada")
    if canal == "whatsapp":
        if texto.count("?") != 1:
            problemas.append(f"Debe tener exactamente 1 pregunta (tiene {texto.count('?')})")
        if "http" in low or "www." in low:
            problemas.append("No incluyas enlaces en el primer mensaje")
    if canal == "email":
        if not asunto:
            problemas.append("Falta el asunto")
        elif len(asunto) > ASUNTO_MAX:
            problemas.append(f"Asunto largo: {len(asunto)} caracteres (máx. {ASUNTO_MAX}, ideal ≤ {ASUNTO_IDEAL})")
        elif len(asunto) > ASUNTO_IDEAL:
            problemas.append(f"Aviso: asunto de {len(asunto)} caracteres (ideal ≤ {ASUNTO_IDEAL})")
        if "<" in texto and ">" in texto:
            problemas.append("Contiene HTML")
        if config.OWNER_NAME not in texto:
            problemas.append("Falta la firma")
    return problemas
