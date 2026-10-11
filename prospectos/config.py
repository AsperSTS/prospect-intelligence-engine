"""Configuración: lee .env sin exponer secretos."""
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
EXPORT_DIR = ROOT / "exports"
DB_PATH = Path(os.environ["PROSPECTOS_DB"]) if os.environ.get("PROSPECTOS_DB") else DATA_DIR / "prospectos.db"  # override solo para demos/pruebas
PREFS_PATH = DATA_DIR / "preferencias.json"
BACKUP_DIR = DATA_DIR / "backups"
TEMPLATES_PATH = ROOT / "config" / "templates.toml"

# --- Datos de Yael (única fuente; no duplicar en otros archivos) ---
OWNER_NAME = "Yael de los Santos"
OWNER_WHATSAPP = "2205704385"          # identidad/firma del remitente; NUNCA se usa para construir wa.me
OWNER_CREDENTIAL = "Trabajé en Audi México en proyectos de digitalización y automatización."
GMAIL_URL = "https://mail.google.com/mail/u/1/#inbox?compose=new"
COUNTRY_CODE = "52"

# --- Enriquecimiento web (límites configurables) ---
REQUEST_TIMEOUT_SECONDS = 5
MAX_RESPONSE_BYTES = 1_000_000
MAX_PAGES_PER_DOMAIN = 5
MIN_DELAY_PER_DOMAIN_SECONDS = 1.0
MAX_REDIRECTS = 3
REENRICH_AFTER_DAYS = 30

# --- Métricas ---
MIN_SAMPLE_PER_VARIANT = 20   # menos contactos que esto = "muestra pequeña"

ENTIDADES = {"21": "Puebla", "29": "Tlaxcala", "15": "Estado de México", "22": "Querétaro", "11": "Guanajuato", "19": "Nuevo León", "20": "Oaxaca"}
ESTRATOS = {"3": "11-30", "4": "31-50", "5": "51-100"}

# (sector, subsector) — subsector "0" = todo el sector. Comercio al por menor excluido a propósito.
SECTORES = [
    ("31", "0"), ("32", "0"), ("33", "0"),  # manufactura
    ("43", "0"),                             # comercio al por mayor
    ("48", "484"), ("48", "488"),            # autotransporte de carga y servicios relacionados
    ("49", "492"), ("49", "493"),            # mensajería y almacenamiento
    ("23", "0"),                             # construcción
    ("81", "811"),                           # reparación y mantenimiento (talleres)
]


def get_token() -> str:
    env = ROOT / ".env"
    if not env.exists():
        raise SystemExit("Falta .env con DENUE_TOKEN=<token>")
    for line in env.read_text().splitlines():
        if line.startswith("DENUE_TOKEN="):
            token = line.split("=", 1)[1].strip()
            if token:
                return token
    raise SystemExit("DENUE_TOKEN vacío en .env")
