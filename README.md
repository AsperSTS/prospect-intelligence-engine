# Prospect Intelligence

Local B2B prospecting tool that turns public business data into a prioritized, explainable work queue.

The current version uses DENUE (INEGI) as its main data source, enriches records with public website information, scores prospects using deterministic rules, and helps prepare and track outreach without sending messages automatically.

## What it does

- Imports establishments from DENUE by location, sector and employee range.
- Normalizes business, contact and website data.
- Calculates separate Fit and Priority scores with visible breakdowns.
- Groups records that may belong to the same company or business group.
- Reviews a limited set of public website pages and stores detected signals with their source URL.
- Generates commercial hypotheses clearly marked as unverified.
- Prepares first-contact messages from editable templates.
- Tracks contacts, responses and follow-ups at 3, 7 and 14 days.
- Provides a Streamlit interface and CLI commands.
- Exports data to Excel.

The application does not send email or WhatsApp messages. Final review and outreach remain manual.

## Architecture

```text
DENUE API
   ↓
validation and normalization
   ↓
SQLite
   ↓
classification and enrichment
   ↓
Fit / Priority scoring
   ↓
Streamlit queue and CLI
   ↓
manual outreach and follow-up tracking
```

The data-ingestion layer is separated from analysis so additional public sources can be incorporated later.

## Stack

Python 3.14 · SQLite · Streamlit · httpx · pandas · pydantic · openpyxl

## Quick start

Create a local environment and install dependencies:

```bash
python3.14 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Create `.env` from `.env.example` and add a DENUE API token:

```text
DENUE_TOKEN=your_token
```

Run the pipeline:

```bash
python -m prospectos run --enriquecer 100
```

Open the dashboard:

```bash
streamlit run app.py
```

Run tests:

```bash
python -m pytest
```

## Design decisions

- **Explainable scoring:** scores are prioritization rules, not purchase probabilities.
- **Human-in-the-loop outreach:** the system prepares context and messages but does not send them.
- **Deterministic templates:** no LLM is required for prospect classification or messaging.
- **Local-first storage:** SQLite keeps the workflow simple for a single-user tool.
- **Defensive enrichment:** website requests are limited and validated before processing.

## Limitations

DENUE and website data may be incomplete or outdated. `fecha_alta` represents incorporation into DENUE, not company founding date. Website signals and commercial hypotheses must be verified before use.

The current scoring model is rule-based and has not yet been calibrated with enough real outreach outcomes to treat it as predictive.

## Author

Yael de los Santos · 2026

## License

MIT. See [LICENSE](LICENSE).
