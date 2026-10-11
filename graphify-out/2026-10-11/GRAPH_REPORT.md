# Graph Report - Buscador de prospectos  (2026-10-11)

## Corpus Check
- 35 files · ~26,507 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 506 nodes · 1005 edges · 33 communities
- Extraction: 99% EXTRACTED · 1% INFERRED · 0% AMBIGUOUS · INFERRED: 8 edges (avg confidence: 0.5)
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- test_enrich.py
- db.py
- UNIVERSAL AGENT INSTRUCTION SPECIFICATION (AI-GUIDELINES.md)
- trabajo.py
- mensajes.py
- pipeline.py
- test_grupos_scoring.py
- Buscador de prospectos (DENUE)
- prospectos/metricas.py
- 4.1 Fit Score
- BRIEF_CLAUDE_CODE_PROSPECCION_DENUE.md
- 25. Orden exacto de implementación
- 8. FASE 7 — Next Best Action
- 26. Tests mínimos
- 5. FASE 4 — Enriquecimiento web prudente
- Tres columnas
- 12. Receta de copy: RAPID
- 13. Reglas de escritura para todos los mensajes
- 10. FASE 9 — Funnel y seguimiento
- 15. Plantillas completas
- 16. Email — primer contacto
- 3. FASE 2 — Identidad, deduplicación y agrupación
- 11. FASE 10 — Métricas útiles
- 17. Seguimientos
- 2. FASE 1 — Calidad y trazabilidad de datos DENUE
- 0. Instrucciones no negociables para Claude Code
- 20. Validación de mensajes antes de mostrarlos
- 21. Filtro de claims
- 9. FASE 8 — Acciones de contacto
- analizar_todos
- copiar.py

## God Nodes (most connected - your core abstractions)
1. `conectar()` - 31 edges
2. `analizar_todos()` - 22 edges
3. `primer_contacto()` - 18 edges
4. `_accion()` - 17 edges
5. `_contexto()` - 16 edges
6. `upsert_denue()` - 14 edges
7. `row()` - 14 edges
8. `registrar_contacto()` - 13 edges
9. `enriquecer_dominio()` - 13 edges
10. `_fila_db()` - 13 edges

## Surprising Connections (you probably didn't know these)
- `test_clasificar_giros_y_display()` --calls--> `clasificar()`  [EXTRACTED]
  tests/test_core.py → prospectos/giros.py
- `filtros_hoy()` --calls--> `telefono_mx()`  [EXTRACTED]
  app.py → prospectos/contacto.py
- `nba()` --calls--> `recommend_next_action()`  [EXTRACTED]
  tests/test_grupos_scoring.py → prospectos/acciones.py
- `_accion()` --calls--> `recommend_next_action()`  [EXTRACTED]
  ui/trabajo.py → prospectos/acciones.py
- `_accion()` --calls--> `telefono_legible()`  [EXTRACTED]
  ui/trabajo.py → prospectos/contacto.py

## Import Cycles
- None detected.

## Communities (33 total, 0 thin omitted)

### Community 0 - "test_enrich.py"
Cohesion: 0.09
Nodes (39): Client, a_texto(), descargar(), enlaces_internos(), enriquecer_dominio(), host_seguro(), nuevo_cliente(), Visita hasta MAX_PAGES_PER_DOMAIN páginas de un dominio. Devuelve status,… (+31 more)

### Community 1 - "db.py"
Cohesion: 0.09
Nodes (62): cambiar_estado(), conectar(), guardar_analisis(), guardar_senales(), historial(), _marcar_revisado(), _migrar(), posponer() (+54 more)

### Community 2 - "UNIVERSAL AGENT INSTRUCTION SPECIFICATION (AI-GUIDELINES.md)"
Cohesion: 0.11
Nodes (17): 1. Interaction Rules with the User, 2. Knowledge Graph Architecture (`graphify`), 3. Context Management & Token Preservation, 4. Supply Chain Security & Dependency Defense, 5. Input Validation & Execution Boundaries, 6. Security Audits & Skills Integration, 7. Project Execution Workflow, 8. GitHub Acquisition Guard — NVIDIA SkillSpector (+9 more)

### Community 3 - "trabajo.py"
Cohesion: 0.07
Nodes (42): filtros_hoy(), DataFrame, Panel Streamlit: streamlit run app.py (entorno conda python314_Demos).…, Filtros dentro de un popover de la cola (no consumen altura de página)., cache_data, normalizar_url(), Base completa: búsqueda, edición de estado/notas, exportación y actualización…, cargar() (+34 more)

### Community 4 - "mensajes.py"
Cohesion: 0.10
Nodes (41): Exception, elegir_variantes(), _es_sigla(), _h(), limpiar_nombre(), Mensaje, obs_con_evidencia(), palabras() (+33 more)

### Community 5 - "pipeline.py"
Cohesion: 0.07
Nodes (41): _nombre_generico(), date, Next Best Action: recomendación determinista del siguiente paso. La herramienta…, recommend_next_action(), dominio(), email_valido(), Normalización y validación de datos de contacto. No infere fijo/móvil: solo…, Devuelve 10 dígitos si el formato es razonable (quita 52 / 044 / 045 / 01); si… (+33 more)

### Community 6 - "test_grupos_scoring.py"
Cohesion: 0.10
Nodes (40): clasificar(), display_desde_clase(), Giro, hipotesis(), Clasificación por SCIAN: giro interno, nombre natural (giro_corto), puntos de…, Comercio al por mayor de abarrotes' -> 'distribución de abarrotes';…, (texto, base, confianza). La confianza solo sube con evidencia web concreta:…, agrupar() (+32 more)

### Community 7 - "Buscador de prospectos (DENUE)"
Cohesion: 0.20
Nodes (9): Archivos, Buscador de prospectos (DENUE), Comandos, Conceptos clave, Diseño (sistema de islas), Entorno, Flujo diario (panel), Qué sigue (solo tras 30-50 contactos reales) (+1 more)

### Community 10 - "prospectos/metricas.py"
Cohesion: 0.18
Nodes (14): _bucket(), corte(), funnel(), lectura(), preparar(), DataFrame, Métricas de funnel. Solo lo que sirve para decidir: qué giro, tamaño, canal,…, Une el primer contacto (canal y variante realmente usados) y crea los rangos de… (+6 more)

### Community 11 - "4.1 Fit Score"
Cohesion: 0.13
Nodes (15): 4.1 Fit Score, 4.2 Priority Score, 4.3 El score DEBE ser explicable, 4. FASE 3 — Separar Fit Score de Priority Score, A. Contactabilidad — 0 a 30, A. Giro objetivo — 0 a 25, B. Estrato de personal — 0 a 20, B. Evidencia contextual — 0 a 20 (+7 more)

### Community 12 - "BRIEF_CLAUDE_CODE_PROSPECCION_DENUE.md"
Cohesion: 0.15
Nodes (12): 14. Variables de mensajes, 18. Preguntas por giro, 19. Generación de `{giro_corto}`, 1. Estado conceptual actual, 22. Respuestas y clasificación manual, 23. FASE 11 — Mapa y rutas SOLO después de validar outreach, 24. Definición de “terminado” para esta versión, 27. Datos de configuración de Yael (+4 more)

### Community 13 - "25. Orden exacto de implementación"
Cohesion: 0.15
Nodes (13): 25. Orden exacto de implementación, Paso 10 — workflow, Paso 11 — métricas, Paso 12 — STOP, Paso 1 — inspección, Paso 2 — backup + migración, Paso 3 — DENUE, Paso 4 — dedupe (+5 more)

### Community 14 - "8. FASE 7 — Next Best Action"
Cohesion: 0.25
Nodes (8): 8. FASE 7 — Next Best Action, DISCARD, EMAIL, FOLLOW_UP, MANUAL_REVIEW, SKIP, TELÉFONO, WHATSAPP_OR_COPY

### Community 15 - "26. Tests mínimos"
Cohesion: 0.29
Nodes (7): 26. Tests mínimos, Data, Dedupe, Enrichment, Mensajes, Score, Workflow

### Community 16 - "5. FASE 4 — Enriquecimiento web prudente"
Cohesion: 0.29
Nodes (7): 5.1 Seguridad obligatoria, 5.2 Límites, 5.3 Páginas máximas, 5.4 Señales web, 5.5 No usar “tiene web” como gran señal, 5. FASE 4 — Enriquecimiento web prudente, Señales comerciales/operativas útiles

### Community 17 - "Tres columnas"
Cohesion: 0.29
Nodes (7): 7.1 Layout principal, 7. FASE 6 — Rediseño UI para decisión rápida, Cabecera compacta, Columna 1 — Cola, Columna 2 — Contexto, Columna 3 — Acción, Tres columnas

### Community 18 - "12. Receta de copy: RAPID"
Cohesion: 0.33
Nodes (6): 12. Receta de copy: RAPID, A — Autoridad mínima, D — Descompresión, I — Intervención pequeña, P — Pregunta, R — Reconocer contexto

### Community 19 - "13. Reglas de escritura para todos los mensajes"
Cohesion: 0.33
Nodes (6): 13. Reglas de escritura para todos los mensajes, Email primer contacto, Prohibido, Regla principal, Tono, WhatsApp primer contacto

### Community 20 - "10. FASE 9 — Funnel y seguimiento"
Cohesion: 0.40
Nodes (5): 10.1 Estados, 10.2 Tabla de interacciones, 10.3 Seguimientos, 10.4 Si responde, 10. FASE 9 — Funnel y seguimiento

### Community 21 - "15. Plantillas completas"
Cohesion: 0.40
Nodes (5): 15.1 WhatsApp — A: puerta de entrada, 15.2 WhatsApp — B: pregunta directa, 15.3 WhatsApp — C: evidencia contextual, 15.4 WhatsApp — D: credencial, 15. Plantillas completas

### Community 22 - "16. Email — primer contacto"
Cohesion: 0.40
Nodes (5): 16. Email — primer contacto, Asunto A, Asunto B, Cuerpo — versión principal, Versión sin credencial

### Community 23 - "3. FASE 2 — Identidad, deduplicación y agrupación"
Cohesion: 0.40
Nodes (5): 3.1 ID canónico, 3.2 Crear agrupación probable, 3.3 Regla, 3. FASE 2 — Identidad, deduplicación y agrupación, Normalización

### Community 24 - "11. FASE 10 — Métricas útiles"
Cohesion: 0.50
Nodes (4): 11. FASE 10 — Métricas útiles, Cortes, Funnel, Regla estadística práctica

### Community 25 - "17. Seguimientos"
Cohesion: 0.50
Nodes (4): 17. Seguimientos, D+14 — cierre limpio, D+3 — volver concreto, D+7 — reducir fricción

### Community 26 - "2. FASE 1 — Calidad y trazabilidad de datos DENUE"
Cohesion: 0.50
Nodes (4): 2.1 Recuperar y guardar los campos útiles, 2.2 Regla para `fecha_alta`, 2.3 Fuente de cada dato, 2. FASE 1 — Calidad y trazabilidad de datos DENUE

### Community 27 - "0. Instrucciones no negociables para Claude Code"
Cohesion: 0.67
Nodes (3): 0. Instrucciones no negociables para Claude Code, Filosofía, NO hacer

### Community 28 - "20. Validación de mensajes antes de mostrarlos"
Cohesion: 0.67
Nodes (3): 20. Validación de mensajes antes de mostrarlos, Email, WhatsApp

### Community 29 - "21. Filtro de claims"
Cohesion: 0.67
Nodes (3): 21. Filtro de claims, No se puede decir, Se puede decir

### Community 30 - "9. FASE 8 — Acciones de contacto"
Cohesion: 0.67
Nodes (3): 9.1 Gmail, 9.2 WhatsApp, 9. FASE 8 — Acciones de contacto

### Community 31 - "analizar_todos"
Cohesion: 0.10
Nodes (26): BaseModel, get_token(), Configuración: lee .env sin exponer secretos., DenueClient, DenueError, Establecimiento, Cliente DENUE (INEGI) con validación estricta de esquema. El token nunca se…, Pagina BuscarAreaActEstr. Registros malformados se omiten, no rompen la corrida. (+18 more)

### Community 32 - "copiar.py"
Cohesion: 0.32
Nodes (7): test_copiar_color_scheme_coincide_con_el_modo(), test_copiar_escapa_y_filtra_urls(), fila(), html(), Fila de botones de un clic: copiar al portapapeles y abrir enlaces…, items: {'etiqueta'} (texto fijo), {'label', 'texto'} para copiar o {'label',…, _seguro()

## Knowledge Gaps
- **121 isolated node(s):** `1. Interaction Rules with the User`, `A. Context Discovery & Navigation`, `B. Graph Maintenance`, `3. Context Management & Token Preservation`, `4. Supply Chain Security & Dependency Defense` (+116 more)
  These have ≤1 connection - possible missing edges or undocumented components.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `analizar_todos()` connect `analizar_todos` to `test_enrich.py`, `db.py`, `mensajes.py`, `pipeline.py`, `test_grupos_scoring.py`?**
  _High betweenness centrality (0.047) - this node is a cross-community bridge._
- **Why does `conectar()` connect `db.py` to `trabajo.py`, `pipeline.py`, `analizar_todos`?**
  _High betweenness centrality (0.025) - this node is a cross-community bridge._
- **Why does `primer_contacto()` connect `mensajes.py` to `analizar_todos`?**
  _High betweenness centrality (0.021) - this node is a cross-community bridge._
- **What connects `1. Interaction Rules with the User`, `A. Context Discovery & Navigation`, `B. Graph Maintenance` to the rest of the system?**
  _121 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `test_enrich.py` be split into smaller, more focused modules?**
  _Cohesion score 0.0858974358974359 - nodes in this community are weakly interconnected._
- **Should `db.py` be split into smaller, more focused modules?**
  _Cohesion score 0.08531468531468532 - nodes in this community are weakly interconnected._
- **Should `UNIVERSAL AGENT INSTRUCTION SPECIFICATION (AI-GUIDELINES.md)` be split into smaller, more focused modules?**
  _Cohesion score 0.1111111111111111 - nodes in this community are weakly interconnected._