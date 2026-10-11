# Prospect Intelligence

Herramienta local para encontrar, priorizar y dar seguimiento a prospectos B2B usando datos públicos.

Actualmente utiliza información de DENUE (INEGI) para identificar empresas en Puebla y Tlaxcala, enriquecer algunos registros con información pública de sus sitios web y generar una cola de prospectos según su relevancia.

El sistema no envía mensajes automáticamente. La revisión, contacto y seguimiento quedan siempre bajo control del usuario.

## Funciones

- Consulta y almacenamiento de empresas desde fuentes públicas
- Clasificación y priorización de prospectos
- Enriquecimiento básico desde sitios web públicos
- Detección de señales comerciales y operativas
- Seguimiento de contactos y respuestas
- Plantillas editables para correo y WhatsApp
- Panel interactivo con Streamlit
- Exportación de datos a Excel
- Base local en SQLite

## Instalación

### Conda

```bash
conda env create -f environment.yml
conda activate prospectos-intelligence
```

### Python

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Probado con Python 3.14.

## Configuración

Actualmente el proyecto utiliza la API de DENUE.

Copia:

```bash
.env.example
```

como:

```bash
.env
```

y agrega tu token:

```env
DENUE_TOKEN=tu_token
```

El archivo `.env` está excluido del repositorio.

## Uso

Ejecutar el pipeline:

```bash
python -m prospectos run --enriquecer 100
```

Abrir el panel:

```bash
streamlit run app.py
```

Ver los prospectos prioritarios desde terminal:

```bash
python -m prospectos daily
```

También están disponibles:

```text
cuantificar
pull
analizar
enriquecer
export
```

## Estructura

```text
prospectos/             lógica, datos y scoring
ui/                     interfaz Streamlit
config/templates.toml   plantillas de contacto
tests/                  pruebas
data/                   base SQLite local
exports/                archivos generados
```

## Datos

La base local se crea automáticamente en:

```text
data/prospectos.db
```

Los datos provienen actualmente de fuentes públicas y pueden estar incompletos.

Los scores son reglas de priorización internas, no predicciones de compra ni evaluaciones de las empresas.

## Estado

Proyecto personal en desarrollo.

La arquitectura está preparada para incorporar nuevas fuentes de información y cruzar datos adicionales en futuras versiones.