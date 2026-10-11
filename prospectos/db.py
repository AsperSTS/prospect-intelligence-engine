"""Persistencia SQLite con migraciones versionadas (PRAGMA user_version) y respaldo automático previo.

Los campos de DENUE se refrescan en cada descarga sin pisar el CRM (estado, notas, historial).
El historial de contactos vive en `interactions`; `actividad` solo alimenta las metas diarias.
"""
import json
import sqlite3
from contextlib import contextmanager
from datetime import date, datetime, timedelta

from . import config

SCHEMA_VERSION = 2

ESTADOS = ["nuevo", "revisado", "contactado", "respondio", "respuesta_positiva", "reunion", "propuesta",
           "cliente", "no_interesado", "sin_respuesta", "descartado"]
# Estados que salen de la cola de trabajo
CERRADOS = {"descartado", "no_interesado", "sin_respuesta", "cliente"}
ETAPA = {"contactado": 1, "respondio": 2, "respuesta_positiva": 3, "reunion": 4, "propuesta": 5, "cliente": 6}

RESPUESTAS = {  # tipo de respuesta -> (estado resultante, etapa mínima alcanzada)
    "interesado": ("respuesta_positiva", 3),
    "redirigido": ("respondio", 2),
    "pregunta": ("respondio", 2),
    "no_interesado": ("no_interesado", 2),
    "ya_tienen_solucion": ("no_interesado", 2),
    "no_es_prioridad": ("no_interesado", 2),
    "numero_incorrecto": ("revisado", 0),   # no se alcanzó a la persona: hay que buscar otro canal
    "correo_rebotado": ("revisado", 0),
    "otro": ("respondio", 2),
}

INTERVALOS = [3, 4, 7]  # D+3, D+7 (+4), D+14 (+7) contados desde el primer contacto

DENUE_COLS = [
    "nombre", "razon_social", "giro", "clase_actividad", "clase_id", "rama_id", "subrama_id", "estrato", "tipo_establecimiento",
    "corredor_nombre", "corredor_tipo", "entidad", "municipio", "localidad", "direccion", "calle", "num_exterior", "num_interior",
    "edificio", "numero_local", "cp", "telefono", "correo", "sitio", "dominio", "latitud", "longitud", "fecha_alta",
]

SCHEMA = """
CREATE TABLE IF NOT EXISTS prospectos (
    id TEXT PRIMARY KEY,
    nombre TEXT NOT NULL,
    razon_social TEXT, giro TEXT, clase_actividad TEXT, clase_id TEXT, estrato TEXT,
    entidad TEXT, municipio TEXT, direccion TEXT, cp TEXT, telefono TEXT, correo TEXT, sitio TEXT,
    latitud REAL, longitud REAL, fecha_alta TEXT,
    whatsapp TEXT, correo_web TEXT, senales TEXT DEFAULT '[]', enriquecido_en TEXT,
    problema TEXT, canal TEXT, score INTEGER DEFAULT 0, mensaje TEXT,
    estado TEXT DEFAULT 'nuevo', notas TEXT DEFAULT '',
    contactado_en TEXT, proximo_seguimiento TEXT, toques INTEGER DEFAULT 0, variante TEXT,
    creado_en TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS actividad (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    fecha TEXT NOT NULL DEFAULT (date('now','localtime')),
    tipo TEXT NOT NULL CHECK (tipo IN ('investigado','contacto','seguimiento','publicacion')),
    prospecto_id TEXT
);
CREATE TABLE IF NOT EXISTS interactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    prospect_id TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now','localtime')),
    channel TEXT,
    interaction_type TEXT NOT NULL,      -- contacto | seguimiento | respuesta | nota
    sequence_step INTEGER,               -- 0 = primer contacto, 1..3 = D+3/D+7/D+14
    template_variant TEXT,
    message_rendered TEXT,
    response_type TEXT,
    notes TEXT
);
CREATE TABLE IF NOT EXISTS web_signals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    prospect_id TEXT NOT NULL,
    signal_type TEXT NOT NULL,
    signal_text TEXT NOT NULL,           -- evidencia textual breve
    signal_source_url TEXT NOT NULL,
    signal_detected_at TEXT NOT NULL DEFAULT (datetime('now','localtime'))
);
CREATE TABLE IF NOT EXISTS web_cache (
    domain TEXT PRIMARY KEY,
    checked_at TEXT NOT NULL,
    status TEXT NOT NULL,                -- ok | bloqueado | error | vacio
    pages_fetched INTEGER DEFAULT 0,
    email TEXT, whatsapp TEXT
);
"""

# columnas añadidas por la migración a v2 (nombre, DDL)
V2_COLUMNS = [
    ("rama_id", "TEXT"), ("subrama_id", "TEXT"), ("tipo_establecimiento", "TEXT"),
    ("corredor_nombre", "TEXT"), ("corredor_tipo", "TEXT"), ("localidad", "TEXT"),
    ("calle", "TEXT"), ("num_exterior", "TEXT"), ("num_interior", "TEXT"), ("edificio", "TEXT"), ("numero_local", "TEXT"),
    ("dominio", "TEXT"), ("source_website", "INTEGER DEFAULT 0"), ("website_checked_at", "TEXT"),
    ("group_key", "TEXT"), ("possible_chain", "INTEGER DEFAULT 0"), ("possible_chain_count", "INTEGER DEFAULT 0"), ("group_reason", "TEXT"),
    ("fit_score", "INTEGER DEFAULT 0"), ("priority_score", "INTEGER DEFAULT 0"), ("fit_breakdown", "TEXT"), ("priority_breakdown", "TEXT"),
    ("giro_display", "TEXT"), ("hypothesis_text", "TEXT"), ("hypothesis_basis", "TEXT"), ("hypothesis_confidence", "TEXT"),
    ("snooze_until", "TEXT"), ("etapa_max", "INTEGER DEFAULT 0"), ("analizado_en", "TEXT"),
]


def _respaldar(origen: sqlite3.Connection, version: int) -> None:
    config.BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    destino = config.BACKUP_DIR / f"prospectos_v{version}_{datetime.now():%Y%m%d_%H%M%S}.db"
    bak = sqlite3.connect(destino)
    try:
        origen.backup(bak)
    finally:
        bak.close()


def _migrar(con: sqlite3.Connection) -> None:
    version = con.execute("PRAGMA user_version").fetchone()[0]
    if version >= SCHEMA_VERSION:
        return
    existe = con.execute("SELECT count(*) FROM sqlite_master WHERE type='table' AND name='prospectos'").fetchone()[0]
    if existe and con.execute("SELECT count(*) FROM prospectos").fetchone()[0] > 0:
        _respaldar(con, version)   # respaldo automático antes de tocar nada
    con.executescript(SCHEMA)
    existentes = {r[1] for r in con.execute("PRAGMA table_info(prospectos)")}
    for col, ddl in [("toques", "INTEGER DEFAULT 0"), ("variante", "TEXT"), ("contactado_en", "TEXT"), ("proximo_seguimiento", "TEXT"), ("score", "INTEGER DEFAULT 0")] + V2_COLUMNS:
        if col not in existentes:
            con.execute(f"ALTER TABLE prospectos ADD COLUMN {col} {ddl}")
    # normaliza estados al vocabulario vigente
    con.execute("UPDATE prospectos SET estado='revisado' WHERE estado='contactar'")
    con.execute("UPDATE prospectos SET estado='cliente' WHERE estado='ganado'")
    # contactos previos sin historial: crear la interacción de origen para no perderlos en las métricas
    con.execute(
        "INSERT INTO interactions (prospect_id, created_at, interaction_type, sequence_step, channel, template_variant, notes)"
        " SELECT id, COALESCE(contactado_en, date('now')), 'contacto', 0, 'manual', variante, 'migrado' FROM prospectos"
        " WHERE toques>=1 AND id NOT IN (SELECT prospect_id FROM interactions)")
    con.execute("UPDATE prospectos SET etapa_max=MAX(COALESCE(etapa_max,0),1) WHERE toques>=1")
    con.executescript("""
        CREATE INDEX IF NOT EXISTS ix_estado_score ON prospectos(estado, score DESC);
        CREATE INDEX IF NOT EXISTS ix_prio ON prospectos(estado, priority_score DESC);
        CREATE INDEX IF NOT EXISTS ix_group ON prospectos(group_key);
        CREATE INDEX IF NOT EXISTS ix_dominio ON prospectos(dominio);
        CREATE INDEX IF NOT EXISTS ix_actividad_fecha ON actividad(fecha, tipo);
        CREATE INDEX IF NOT EXISTS ix_inter_prospect ON interactions(prospect_id, created_at);
        CREATE INDEX IF NOT EXISTS ix_signals_prospect ON web_signals(prospect_id);
    """)
    con.execute(f"PRAGMA user_version={SCHEMA_VERSION}")
    con.commit()


@contextmanager
def conectar():
    config.DATA_DIR.mkdir(exist_ok=True)
    con = sqlite3.connect(config.DB_PATH)
    con.row_factory = sqlite3.Row
    _migrar(con)
    try:
        yield con
        con.commit()
    finally:
        con.close()


def upsert_denue(con: sqlite3.Connection, filas: list[dict]) -> tuple[int, int]:
    """Devuelve (nuevos, actualizados). Refresca solo campos DENUE; el CRM no se toca."""
    nuevos = 0
    for f in filas:
        vals = [f.get(c) for c in DENUE_COLS]
        if con.execute("SELECT 1 FROM prospectos WHERE id=?", (f["id"],)).fetchone():
            con.execute(f"UPDATE prospectos SET {', '.join(c + '=?' for c in DENUE_COLS)} WHERE id=?", vals + [f["id"]])
        else:
            cols = ["id"] + DENUE_COLS
            con.execute(f"INSERT INTO prospectos ({','.join(cols)}) VALUES ({','.join('?' * len(cols))})", [f["id"]] + vals)
            nuevos += 1
    return nuevos, len(filas) - nuevos


def guardar_senales(con: sqlite3.Connection, pid: str, senales: list[dict]) -> None:
    con.execute("DELETE FROM web_signals WHERE prospect_id=?", (pid,))
    con.executemany(
        "INSERT INTO web_signals (prospect_id, signal_type, signal_text, signal_source_url) VALUES (?,?,?,?)",
        [(pid, s["signal_type"], s["signal_text"], s["signal_source_url"]) for s in senales])


def senales_de(con: sqlite3.Connection, pid: str) -> list[sqlite3.Row]:
    return con.execute("SELECT * FROM web_signals WHERE prospect_id=? ORDER BY id", (pid,)).fetchall()


def guardar_analisis(con: sqlite3.Connection, pid: str, **campos) -> None:
    """Escribe columnas de análisis (scores, hipótesis, grupo...). Los dict/list se serializan a JSON."""
    campos = {k: (json.dumps(v, ensure_ascii=False) if isinstance(v, (dict, list)) else v) for k, v in campos.items()}
    sets = ", ".join(f"{k}=?" for k in campos)
    con.execute(f"UPDATE prospectos SET {sets}, analizado_en=datetime('now','localtime') WHERE id=?", [*campos.values(), pid])


def registrar_actividad(con: sqlite3.Connection, tipo: str, pid: str | None = None) -> None:
    con.execute("INSERT INTO actividad (tipo, prospecto_id) VALUES (?, ?)", (tipo, pid))


def _marcar_revisado(con, pid: str) -> None:
    previo = con.execute("SELECT estado FROM prospectos WHERE id=?", (pid,)).fetchone()
    if previo and previo["estado"] == "nuevo":
        registrar_actividad(con, "investigado", pid)


def _subir_etapa(con, pid: str, etapa: int) -> None:
    con.execute("UPDATE prospectos SET etapa_max=MAX(COALESCE(etapa_max,0), ?) WHERE id=?", (etapa, pid))


def registrar_contacto(con: sqlite3.Connection, pid: str, canal: str, variante: str | None, mensaje: str | None, notas: str | None = None) -> None:
    """Primer contacto: crea la interacción y programa D+3."""
    _marcar_revisado(con, pid)
    hoy = date.today()
    registrar_actividad(con, "contacto", pid)
    con.execute("INSERT INTO interactions (prospect_id, channel, interaction_type, sequence_step, template_variant, message_rendered, notes)"
                " VALUES (?,?,?,?,?,?,?)", (pid, canal, "contacto", 0, variante, mensaje, notas))
    con.execute("UPDATE prospectos SET estado='contactado', toques=1, contactado_en=?, proximo_seguimiento=?, snooze_until=NULL,"
                " notas=COALESCE(?, notas) WHERE id=?",
                (hoy.isoformat(), (hoy + timedelta(days=INTERVALOS[0])).isoformat(), notas, pid))
    _subir_etapa(con, pid, 1)


def registrar_seguimiento(con: sqlite3.Connection, pid: str, canal: str, variante: str | None, mensaje: str | None) -> str:
    """Seguimiento enviado (D+3/D+7/D+14). Tras el tercero sin respuesta → sin_respuesta. Devuelve el estado resultante."""
    fila = con.execute("SELECT toques FROM prospectos WHERE id=?", (pid,)).fetchone()
    toques = (fila["toques"] or 1) + 1
    paso = toques - 1
    registrar_actividad(con, "seguimiento", pid)
    con.execute("INSERT INTO interactions (prospect_id, channel, interaction_type, sequence_step, template_variant, message_rendered)"
                " VALUES (?,?,?,?,?,?)", (pid, canal, "seguimiento", paso, variante, mensaje))
    if paso >= len(INTERVALOS):
        con.execute("UPDATE prospectos SET toques=?, estado='sin_respuesta', proximo_seguimiento=NULL WHERE id=?", (toques, pid))
        return "sin_respuesta"
    sig = (date.today() + timedelta(days=INTERVALOS[paso])).isoformat()
    con.execute("UPDATE prospectos SET toques=?, proximo_seguimiento=? WHERE id=?", (toques, sig, pid))
    return "contactado"


def registrar_respuesta(con: sqlite3.Connection, pid: str, tipo: str, notas: str | None = None) -> str:
    """Clasifica una respuesta manualmente. Cancela de inmediato los seguimientos pendientes."""
    if tipo not in RESPUESTAS:
        raise ValueError(f"tipo de respuesta inválido: {tipo}")
    estado, etapa = RESPUESTAS[tipo]
    con.execute("INSERT INTO interactions (prospect_id, interaction_type, response_type, notes) VALUES (?,?,?,?)", (pid, "respuesta", tipo, notas))
    con.execute("UPDATE prospectos SET estado=?, proximo_seguimiento=NULL, notas=COALESCE(?, notas) WHERE id=?", (estado, notas, pid))
    if etapa:
        _subir_etapa(con, pid, etapa)
    return estado


def cambiar_estado(con: sqlite3.Connection, pid: str, estado: str, notas: str | None = None) -> None:
    """Cambio manual de estado. Todo estado distinto de 'contactado' cancela los seguimientos pendientes."""
    if estado not in ESTADOS:
        raise ValueError(f"estado inválido: {estado}")
    if estado == "contactado":
        previo = con.execute("SELECT estado FROM prospectos WHERE id=?", (pid,)).fetchone()
        if previo and previo["estado"] != "contactado":
            return registrar_contacto(con, pid, "manual", None, None, notas)
    if estado != "nuevo":
        _marcar_revisado(con, pid)
    con.execute("UPDATE prospectos SET estado=?, proximo_seguimiento=NULL, snooze_until=NULL, notas=COALESCE(?, notas) WHERE id=?",
                (estado, notas, pid))
    if estado in ETAPA:
        _subir_etapa(con, pid, ETAPA[estado])


def posponer(con: sqlite3.Connection, pid: str, dias: int = 3) -> None:
    con.execute("UPDATE prospectos SET snooze_until=? WHERE id=?", ((date.today() + timedelta(days=dias)).isoformat(), pid))


def historial(con: sqlite3.Connection, pid: str) -> list[sqlite3.Row]:
    return con.execute("SELECT * FROM interactions WHERE prospect_id=? ORDER BY id", (pid,)).fetchall()


def seguimientos_pendientes(con: sqlite3.Connection) -> list[sqlite3.Row]:
    return con.execute("SELECT * FROM prospectos WHERE estado='contactado' AND proximo_seguimiento<=date('now','localtime')"
                       " ORDER BY proximo_seguimiento").fetchall()


META_DIARIA = {"investigado": 5, "contacto": 3, "publicacion": 1, "seguimiento": 1}


def progreso_hoy(con: sqlite3.Connection) -> dict[str, int]:
    hecho = {t: 0 for t in META_DIARIA}
    for r in con.execute("SELECT tipo, count(*) n FROM actividad WHERE fecha=date('now','localtime') GROUP BY tipo"):
        hecho[r["tipo"]] = r["n"]
    return hecho
