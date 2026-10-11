# Prospect Intelligence

Herramienta local para priorizar prospectos B2B a partir de datos públicos.

## Problema que resuelve

Antes de contactar a una empresa hay que revisar su giro, su tamaño, sus datos de contacto y su sitio web. Hacer esa investigación a mano para cientos de establecimientos consume tiempo y es fácil de hacer sin criterio uniforme.

Esta herramienta reduce ese trabajo previo: toma establecimientos del DENUE (INEGI), los clasifica, revisa sitios web públicos y ordena una cola de trabajo con el motivo de cada puntuación. La decisión de a quién contactar, por qué y con qué mensaje sigue siendo de la persona que la usa.

## Qué hace hoy

- Importa establecimientos del DENUE por entidad, sector y estrato, con validación estricta del esquema de la API.
- Clasifica cada establecimiento por giro (SCIAN) y tamaño, y normaliza teléfonos, correos y dominios.
- Calcula un Fit Score y una Prioridad con desglose explicable.
- Agrupa registros que probablemente pertenecen a la misma empresa o grupo, con la razón de la agrupación.
- Visita un número acotado de páginas públicas por sitio web para extraer correo, WhatsApp y señales textuales, guardando la cita y la URL de origen.
- Genera hipótesis comerciales marcadas como no verificadas, con su base y su nivel de confianza.
- Prepara mensajes de primer contacto a partir de plantillas editables.
- Registra contactos, respuestas y seguimientos a 3, 7 y 14 días, y cancela los seguimientos cuando hay respuesta.
- Ofrece un panel en Streamlit (cola de trabajo, seguimientos, conversaciones, métricas y base completa) y comandos de terminal.
- Exporta la base a Excel.

La aplicación no envía mensajes. Los botones del panel copian el texto o abren Gmail o WhatsApp con el contenido preparado; el envío lo realiza la persona usuaria.

## Evolución prevista

DENUE es la fuente principal, pero la arquitectura separa la captura de datos del análisis para incorporar otras fuentes públicas. El objetivo es cruzar distintas señales para mejorar la selección de prospectos. Por ahora no hay otras fuentes integradas.

## Stack

Python 3.14 · SQLite · Streamlit · httpx · pandas · pydantic · openpyxl

## Instalación

Requiere Python 3.14.

Con Conda:

```bash
conda env create -f environment.yml
conda activate prospect-intelligence
```

Con `venv`:

```bash
python3.14 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Para ejecutar las pruebas, instala `requirements-dev.txt` en lugar de `requirements.txt`.

## Configuración

Solicita un token de la API DENUE de INEGI y guárdalo en un archivo `.env` a partir de la plantilla:

```bash
cp .env.example .env
```

Después define el valor en `.env`:

```text
DENUE_TOKEN=tu_token
```

El archivo `.env` no se versiona. Si falta el token, el programa se detiene con un mensaje que indica cómo corregirlo.

La base SQLite se crea en `data/prospectos.db`. Para usar otra ruta, define la variable `PROSPECTOS_DB`.

## Uso

Importar, analizar y enriquecer con sitios web (por defecto, Puebla y Tlaxcala):

```bash
python -m prospectos run --enriquecer 100
```

Abrir el panel:

```bash
streamlit run app.py
```

Ver los prospectos prioritarios y los seguimientos vencidos en terminal:

```bash
python -m prospectos daily
```

Otros comandos: `cuantificar`, `pull`, `analizar`, `enriquecer` y `export`. El comando `export` escribe un archivo `.xlsx` en `exports/`. Ejecuta `python -m prospectos --help` para ver las opciones.

Pruebas:

```bash
python -m pytest
```

## Estructura

```text
app.py                  panel Streamlit
prospectos/             importación DENUE, análisis, scoring, mensajes, CRM y base SQLite
ui/                     componentes y estilos del panel
config/templates.toml   plantillas de mensajes
.streamlit/config.toml  tema del panel
tests/                  pruebas automatizadas
data/                   base local generada (no versionada)
exports/                archivos generados (no versionados)
```

## Limitaciones

- Solo usa DENUE y sitios web públicos. No incorpora otras fuentes.
- Los datos de DENUE pueden estar incompletos o desactualizados. La fecha de alta es la incorporación reportada en DENUE, no la fecha de fundación.
- El enriquecimiento lee HTML estático. Los sitios que se generan con JavaScript pueden devolver poca información.
- Las puntuaciones son reglas internas de priorización, no probabilidades de compra. No están calibradas con resultados reales.
- Las hipótesis y señales deben verificarse antes de usarse en una conversación. El sitio encontrado puede no corresponder a la empresa.
- Está diseñada para una sola persona que trabaja en local. SQLite no soporta uso concurrente de varias personas.

## Autor

Yael de los Santos · 2026
WhatsApp: +52 220 570 4385

## Licencia

Distribuido bajo licencia MIT. Consulta [LICENSE](LICENSE).
