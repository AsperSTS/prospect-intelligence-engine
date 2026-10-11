# Graph Report - Buscador de prospectos  (2026-10-10)

## Corpus Check
- 13 files · ~4,950 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 109 nodes · 196 edges · 9 communities
- Extraction: 97% EXTRACTED · 3% INFERRED · 0% AMBIGUOUS · INFERRED: 5 edges (avg confidence: 0.5)
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- test_core.py
- db.py
- UNIVERSAL AGENT INSTRUCTION SPECIFICATION (AI-GUIDELINES.md)
- DenueClient
- __main__.py
- enrich.py
- pipeline.py
- Buscador de prospectos

## God Nodes (most connected - your core abstractions)
1. `conectar()` - 10 edges
2. `DenueClient` - 10 edges
3. `UNIVERSAL AGENT INSTRUCTION SPECIFICATION (AI-GUIDELINES.md)` - 9 edges
4. `pull()` - 8 edges
5. `analizar()` - 8 edges
6. `8. GitHub Acquisition Guard — NVIDIA SkillSpector` - 7 edges
7. `cmd_daily()` - 6 edges
8. `main()` - 6 edges
9. `upsert_denue()` - 6 edges
10. `Establecimiento` - 6 edges

## Surprising Connections (you probably didn't know these)
- `test_estado_invalido()` --calls--> `conectar()`  [EXTRACTED]
  tests/test_core.py → prospectos/db.py
- `test_upsert_no_pisa_crm()` --calls--> `conectar()`  [EXTRACTED]
  tests/test_core.py → prospectos/db.py
- `test_estado_invalido()` --calls--> `cambiar_estado()`  [EXTRACTED]
  tests/test_core.py → prospectos/db.py
- `test_upsert_no_pisa_crm()` --calls--> `cambiar_estado()`  [EXTRACTED]
  tests/test_core.py → prospectos/db.py
- `test_telefono_y_wa_link()` --calls--> `link_whatsapp()`  [EXTRACTED]
  tests/test_core.py → prospectos/rules.py

## Import Cycles
- None detected.

## Communities (9 total, 0 thin omitted)

### Community 0 - "test_core.py"
Cohesion: 0.15
Nodes (19): Devuelve (nuevos, actualizados)., upsert_denue(), analizar(), calcular_score(), clasificar(), elegir_canal(), normalizar_telefono_mx(), Reglas de negocio: giro → problema probable, canal, score y mensaje. Sin LLM,… (+11 more)

### Community 1 - "db.py"
Cohesion: 0.16
Nodes (19): actualizar(), cargar(), Panel Streamlit: streamlit run app.py (entorno conda python314_Demos), tarjeta(), cache_data, Connection, DataFrame, cambiar_estado() (+11 more)

### Community 2 - "UNIVERSAL AGENT INSTRUCTION SPECIFICATION (AI-GUIDELINES.md)"
Cohesion: 0.11
Nodes (17): 1. Interaction Rules with the User, 2. Knowledge Graph Architecture (`graphify`), 3. Context Management & Token Preservation, 4. Supply Chain Security & Dependency Defense, 5. Input Validation & Execution Boundaries, 6. Security Audits & Skills Integration, 7. Project Execution Workflow, 8. GitHub Acquisition Guard — NVIDIA SkillSpector (+9 more)

### Community 3 - "DenueClient"
Cohesion: 0.23
Nodes (6): DenueClient, DenueError, Cliente DENUE (INEGI) con validación estricta de esquema. El token nunca se…, Pagina BuscarAreaActEstr. Registros malformados se omiten, no rompen la corrida., _redact(), RuntimeError

### Community 4 - "__main__.py"
Cohesion: 0.33
Nodes (9): get_token(), Configuración: lee .env sin exponer secretos., cmd_cuantificar(), cmd_export(), cmd_pull(), cmd_run(), main(), CLI: python -m prospectos <comando> (+1 more)

### Community 5 - "enrich.py"
Cohesion: 0.29
Nodes (9): Client, enriquecer(), extraer(), host_seguro(), normalizar_url(), Enriquecimiento web: correo, WhatsApp y señales desde el sitio de la empresa.…, test_correos_basura_filtrados(), test_extraer_html() (+1 more)

### Community 6 - "pipeline.py"
Cohesion: 0.33
Nodes (4): BaseModel, Establecimiento, _fila(), Orquesta pull → enrich → analyze sobre la base SQLite.

### Community 7 - "Buscador de prospectos"
Cohesion: 0.29
Nodes (6): Buscador de prospectos, Cómo funciona, Entorno, Reglas, Secretos, Uso

## Knowledge Gaps
- **19 isolated node(s):** `1. Interaction Rules with the User`, `A. Context Discovery & Navigation`, `B. Graph Maintenance`, `3. Context Management & Token Preservation`, `4. Supply Chain Security & Dependency Defense` (+14 more)
  These have ≤1 connection - possible missing edges or undocumented components.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `DenueClient` connect `DenueClient` to `__main__.py`, `pipeline.py`?**
  _High betweenness centrality (0.066) - this node is a cross-community bridge._
- **Why does `conectar()` connect `db.py` to `test_core.py`, `__main__.py`?**
  _High betweenness centrality (0.042) - this node is a cross-community bridge._
- **Why does `Establecimiento` connect `pipeline.py` to `test_core.py`, `DenueClient`?**
  _High betweenness centrality (0.032) - this node is a cross-community bridge._
- **What connects `1. Interaction Rules with the User`, `A. Context Discovery & Navigation`, `B. Graph Maintenance` to the rest of the system?**
  _19 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `UNIVERSAL AGENT INSTRUCTION SPECIFICATION (AI-GUIDELINES.md)` be split into smaller, more focused modules?**
  _Cohesion score 0.1111111111111111 - nodes in this community are weakly interconnected._