# BRIEF DE IMPLEMENTACIÓN — Sistema privado de prospección DENUE

> **Objetivo:** mejorar el sistema existente para convertir DENUE en una cola diaria de prospectos B2B priorizados, explicables y accionables, sin automatizar el envío ni convertir la herramienta en un CRM sobredimensionado.
>
> **Usuario:** Yael de los Santos.
>
> **Uso:** herramienta local y privada para una sola persona. **No se publicará en web por ahora.**
>
> **WhatsApp Business de Yael:** `2205704385`
>
> **Gmail predeterminado:** `https://mail.google.com/mail/u/1/`
>
> **Principio rector:** automatizar investigación y organización; mantener humana la decisión y el envío.

---

# 0. Instrucciones no negociables para Claude Code

Antes de tocar código:

1. **Inspecciona la estructura real del proyecto.**
2. Identifica:
   - archivo de entrada de Streamlit;
   - módulo que llama a DENUE;
   - esquema SQLite actual;
   - migraciones existentes;
   - módulo de enriquecimiento web;
   - lógica de scoring;
   - `mensajes.py`;
   - estados y seguimiento;
   - tests existentes.
3. Haz un inventario breve de lo encontrado.
4. Implementa **por fases**. No reescribas el proyecto completo.
5. Conserva compatibilidad con la base actual cuando sea razonable.
6. Si una migración puede destruir datos, crea backup automático antes.
7. Cada cambio debe ser pequeño, verificable y reversible.

## NO hacer

- No añadir LLMs.
- No añadir APIs de IA.
- No automatizar el envío de WhatsApp o correo.
- No crear cuentas, login, multiusuario o permisos.
- No mover la aplicación a cloud.
- No crear microservicios.
- No añadir Redis, Celery, Kafka ni infraestructura innecesaria.
- No construir scraping masivo.
- No intentar descubrir nombres de dueños o empleados.
- No inferir que una empresa usa o no ERP.
- No afirmar problemas que no estén respaldados por evidencia.
- No convertir `fecha_alta` en “años de antigüedad de la empresa”.
- No inferir fijo/móvil únicamente por LADA o longitud del teléfono.
- No generar mensajes “hiperpersonalizados” con datos inventados.
- No cambiar el stack principal salvo que sea imprescindible.
- No añadir features visuales antes de terminar la medición del funnel.

## Filosofía

Este producto debe responder una sola pregunta:

> **¿A quién debería contactar ahora, por qué, y qué mensaje humano puedo enviarle?**

Si una feature no ayuda a responder eso, probablemente no pertenece todavía al producto.

---

# 1. Estado conceptual actual

Pipeline esperado:

```text
API DENUE
   ↓
validación de esquema
   ↓
SQLite
   ↓
clasificación por SCIAN
   ↓
enriquecimiento web limitado
   ↓
Fit Score
   ↓
Priority Score
   ↓
cola diaria
   ↓
revisión humana
   ↓
mensaje sugerido
   ↓
copiar / abrir canal
   ↓
marcar como contactado
   ↓
seguimientos D+3 / D+7 / D+14
   ↓
respuesta / reunión / propuesta / cliente
   ↓
métricas por giro, variante y canal
```

La base inicial contiene aproximadamente **4,709 establecimientos de Puebla y Tlaxcala**, filtrados a giros industriales/logísticos y estratos compatibles.

No asumir que 4,709 establecimientos equivalen a 4,709 empresas únicas.

---

# 2. FASE 1 — Calidad y trazabilidad de datos DENUE

## 2.1 Recuperar y guardar los campos útiles

Mantener los campos actuales y recuperar, cuando DENUE los exponga:

```text
id_denue / clee
nombre_establecimiento
razon_social
codigo_scian_clase
nombre_scian_clase
codigo_scian_rama
nombre_scian_rama
codigo_scian_subrama
nombre_scian_subrama
estrato_personal
tipo_establecimiento
nombre_corredor_industrial
tipo_corredor_industrial
fecha_alta
telefono
correo
sitio_web
calle
numero_exterior
numero_interior
edificio
numero_local
codigo_postal
municipio
localidad
latitud
longitud
```

Adaptar nombres al esquema existente; **no crear duplicados semánticos**.

## 2.2 Regla para `fecha_alta`

En código, UI y documentación:

```text
fecha_alta ≠ fecha de fundación
fecha_alta = fecha de alta/incorporación reportada en DENUE
```

Mostrar:

```text
Alta en DENUE: 2018-03
```

NO mostrar:

```text
Empresa con 8 años de antigüedad
```

Puede usarse como señal secundaria de priorización, nunca como edad real de la empresa.

## 2.3 Fuente de cada dato

Añadir trazabilidad simple cuando sea útil:

```text
source_denue = true
source_website = true/false
website_checked_at
```

Para señales web, guardar:

```text
signal_type
signal_text
signal_source_url
signal_detected_at
```

La UI debe distinguir visualmente:

- **Dato público**
- **Señal detectada**
- **Hipótesis**
- **Dato ingresado manualmente**

---

# 3. FASE 2 — Identidad, deduplicación y agrupación

DENUE contiene establecimientos. No asumir que cada fila es una empresa distinta.

## 3.1 ID canónico

Mantener `id_denue` o `CLEE` como identificador estable del establecimiento.

## 3.2 Crear agrupación probable

Añadir campos:

```text
company_group_key
possible_chain BOOLEAN
possible_chain_count INTEGER
group_reason TEXT
```

Construir `company_group_key` usando señales deterministas y explicables.

Prioridad:

1. razón social normalizada;
2. dominio web normalizado;
3. teléfono exacto repetido;
4. nombre normalizado + municipio/estado;
5. combinaciones prudentes.

### Normalización

Para comparar:

- lowercase;
- quitar acentos;
- quitar puntuación;
- quitar sufijos empresariales comunes SOLO para comparación:
  - s.a.
  - s.a. de c.v.
  - sa de cv
  - s. de r.l.
  - etc.

No sobrescribir el nombre original.

## 3.3 Regla

Si coinciden señales:

```text
⚠ Posible grupo/cadena — 4 establecimientos relacionados
Motivo: misma razón social + mismo dominio
```

NO afirmar:

```text
Tiene 4 sucursales
```

La agrupación es una ayuda para revisión humana.

---

# 4. FASE 3 — Separar Fit Score de Priority Score

El score actual no debe mezclar “qué buen cliente sería” con “qué tan accionable es hoy”.

Crear:

```text
fit_score        INTEGER 0–100
priority_score   INTEGER 0–100
fit_breakdown    JSON/TEXT
priority_breakdown JSON/TEXT
```

Si SQLite actual no tiene JSON1 garantizado, usar TEXT con JSON serializado.

---

## 4.1 Fit Score

Pregunta:

> **¿Qué tan compatible es este establecimiento con los servicios que Yael puede vender?**

Modelo inicial sugerido. Ajustarlo a la estructura real sin inventar precisión.

### A. Giro objetivo — 0 a 25

Ejemplo:

```text
Autopartes / manufactura especializada     +25
Metalmecánica                              +24
Taller industrial                          +22
Logística / transporte                     +20
Almacén / distribución                     +18
Constructora / contratista                 +17
Comercializadora B2B                       +15
Otro compatible                            +8–14
No compatible                              0
```

La clase SCIAN completa debe poder refinar esto.

### B. Estrato de personal — 0 a 20

Prioridad de arranque:

```text
11–30    +14
31–50    +20
51–100   +20
```

No inferir número exacto.

### C. Tipo de establecimiento — 0 a 10

```text
Fijo/establecimiento formal compatible  +10
Desconocido                              +4
Incompatible                             0
```

No descartar automáticamente si el campo viene vacío.

### D. Corredor industrial — 0 a 15

```text
corredor industrial identificado +15
zona/parque compatible            +10
sin dato                            0
```

### E. Complejidad operativa probable — 0 a 20

Basada SOLO en giro/SCIAN y señales públicas.

Ejemplos:

```text
fabricación bajo pedido
múltiples servicios
flotilla
almacén
producción
calidad
distribución
mantenimiento
cotizaciones
```

No convertirlo en hechos internos.

### F. Señales públicas útiles — 0 a 10

Máximo 10 aunque haya muchas.

---

## 4.2 Priority Score

Pregunta:

> **¿Qué tan conveniente es revisar/contactar este prospecto hoy?**

### A. Contactabilidad — 0 a 30

```text
email válido                 +10
teléfono disponible          +10
sitio web disponible          +5
más de un canal útil          +5
```

No inferir móvil/fijo únicamente por longitud.

### B. Evidencia contextual — 0 a 20

```text
señal web concreta           +10
señal directamente relacionada con servicio +10
```

### C. Fit Score — 0 a 35

Normalizar:

```python
round(fit_score * 0.35)
```

### D. Estado operativo — -20 a +15

Ejemplo:

```text
nuevo y nunca revisado                    +5
seguimiento vencido                       +15
respondió y requiere acción               +15
contactado recientemente                   -8
posible cadena ya contactada              -15
descartado / no interesado                -100 => excluir
sin canal de contacto                      -10
```

### E. Frescura — 0 a 5

Solo para favorecer registros/enriquecimientos recientes.

---

## 4.3 El score DEBE ser explicable

En UI:

```text
FIT 84
────────────────────
Giro                  +25
Estrato               +20
Corredor              +15
Tipo establec.        +10
Complejidad           +9
Señales               +5

PRIORIDAD 79
────────────────────
Fit ponderado         +29
Contacto              +25
Contexto              +15
Estado                +5
Frescura              +5
```

Nunca presentar `84` como probabilidad de compra.

Agregar tooltip:

> “El score es una regla de priorización interna, no una probabilidad.”

---

# 5. FASE 4 — Enriquecimiento web prudente

Mantener el enfoque determinista.

## 5.1 Seguridad obligatoria

Conservar o reforzar:

- bloquear localhost;
- bloquear `127.0.0.0/8`;
- bloquear RFC1918;
- bloquear link-local;
- bloquear metadata endpoints;
- resolver DNS antes de request;
- volver a validar después de redirects;
- máximo de redirects;
- timeout corto;
- límite máximo de bytes;
- content-type permitido;
- no ejecutar JavaScript;
- no descargar binarios.

## 5.2 Límites

Configurables:

```python
REQUEST_TIMEOUT_SECONDS = 5
MAX_RESPONSE_BYTES = 1_000_000
MAX_PAGES_PER_DOMAIN = 5
MIN_DELAY_PER_DOMAIN_SECONDS = 1.0
MAX_REDIRECTS = 3
```

Cachear por dominio.

No volver a enriquecer automáticamente durante, por ejemplo, 30 días salvo acción manual.

## 5.3 Páginas máximas

Intentar SOLO páginas razonables:

```text
/
nosotros
servicios
productos
contacto
```

Detectar enlaces internos equivalentes, no inventar rutas infinitas.

## 5.4 Señales web

Guardar señales con evidencia textual breve y URL.

### Señales comerciales/operativas útiles

```text
cotiza
cotización
solicitar cotización
fabricación
producción
calidad
ISO
inventario
almacén
logística
distribución
proveedores
flotilla
mantenimiento
servicio técnico
fabricación sobre pedido
proyectos
entregas
sucursales
```

## 5.5 No usar “tiene web” como gran señal

“Tiene sitio web” mejora contactabilidad.

El valor contextual viene de lo que el sitio revela públicamente.

---

# 6. FASE 5 — Hipótesis explícitas, no afirmaciones

Cada prospecto puede tener:

```text
hypothesis_text
hypothesis_basis
hypothesis_confidence
```

Valores de `hypothesis_confidence`:

```text
baja
media
alta
```

Ejemplo correcto:

```text
Hipótesis:
Por el giro y porque el sitio menciona fabricación bajo pedido, podría existir
fricción al dar seguimiento a cotizaciones, órdenes y costos.
```

Incorrecto:

```text
La empresa pierde horas haciendo cotizaciones en Excel.
```

No sabemos eso.

La UI debe mostrar:

```text
⚠ Hipótesis, no dato verificado
```

---

# 7. FASE 6 — Rediseño UI para decisión rápida

No rediseñar por estética. Rediseñar para procesar prospectos en pocos minutos.

## 7.1 Layout principal

### Cabecera compacta

```text
Hoy: 18 por revisar | 4 seguimientos | 2 respuestas | 1 reunión
[Filtro giro] [Municipio] [Fit mínimo] [Solo con contacto]
```

### Tres columnas

#### Columna 1 — Cola

Cada tarjeta/fila:

```text
METALFORM
Metalmecánica · Puebla
FIT 87 · PRIORIDAD 82
📞 ✉ 🌐
```

Atajos:

```text
↑ / ↓  navegar
C      marcar contactado
D      descartar
E      email
W      WhatsApp/copy
S      saltar
```

No implementar atajos si Streamlit los complica demasiado; primero botones simples.

#### Columna 2 — Contexto

```text
METALFORM
Razón social: ...
Municipio: Puebla
Estrato: 31–50
SCIAN: Fabricación de ...
Corredor: FINSA
Tipo: fijo
Alta en DENUE: 2014-07

¿Por qué sí?
✓ giro prioritario
✓ estrato ideal
✓ corredor industrial
✓ email + teléfono
✓ web menciona fabricación bajo pedido

⚠ Posible grupo: 3 establecimientos

Evidencia web
• “...” — /servicios
• “...” — /productos

Hipótesis
...
```

#### Columna 3 — Acción

```text
Next best action: EMAIL
Motivo: email corporativo + contexto web + fit alto

[Mensaje sugerido]

[Copiar mensaje]
[Abrir Gmail]
[Copiar email]

[Marcar contactado]
[Descartar]
[Posponer]
```

---

# 8. FASE 7 — Next Best Action

Crear una función determinista:

```python
recommend_next_action(prospect) -> {
    "action": "...",
    "reason": "...",
    "confidence": "..."
}
```

Acciones:

```text
email
telefono
whatsapp_or_copy
manual_review
follow_up
skip
discard
```

Reglas iniciales:

### EMAIL

Si:

```text
email válido
+ fit suficientemente alto
+ no contactado recientemente
```

Especialmente si hay contexto web.

### TELÉFONO

Si:

```text
teléfono disponible
+ fit alto
+ no email
```

La herramienta NO llama automáticamente.

### WHATSAPP_OR_COPY

Solo si hay teléfono y el usuario decide probar WhatsApp.

No afirmar que el número es móvil.

### MANUAL_REVIEW

Si:

```text
possible_chain = true
datos contradictorios
SCIAN dudoso
nombre genérico
score alto sin contacto claro
```

### FOLLOW_UP

Si seguimiento vencido.

### SKIP

Si no hay suficientes datos.

### DISCARD

Solo tras decisión humana o regla inequívoca de incompatibilidad.

---

# 9. FASE 8 — Acciones de contacto

## 9.1 Gmail

Yael usa:

```text
https://mail.google.com/mail/u/1/
```

Crear botón:

```text
Abrir Gmail
```

URL recomendada:

```text
https://mail.google.com/mail/u/1/#inbox?compose=new
```

No depender del prellenado automático de Gmail para que la función sea útil.

Junto al botón:

```text
[Copiar email]
[Copiar asunto]
[Copiar cuerpo]
[Abrir Gmail]
```

El usuario pega manualmente.

Si más adelante se implementa prefill, hacerlo como mejora separada y comprobada.

## 9.2 WhatsApp

**WhatsApp Business del remitente:**

```text
2205704385
```

Esto sirve para firma/identidad. NO construir el enlace `wa.me` usando el número de Yael.

El enlace debe apuntar al **teléfono del prospecto**, normalizado solo si es razonablemente válido.

Formato mexicano esperado cuando corresponda:

```text
52 + 10 dígitos
```

Ejemplo:

```text
https://wa.me/52XXXXXXXXXX?text=<URL_ENCODED_MESSAGE>
```

Pero:

- no asumir que todo teléfono DENUE tiene WhatsApp;
- no abrir automáticamente;
- si el número es dudoso, mostrar:
  - `Copiar teléfono`
  - `Copiar mensaje`
- el usuario decide.

---

# 10. FASE 9 — Funnel y seguimiento

## 10.1 Estados

Normalizar a:

```text
nuevo
revisado
contactado
respondio
respuesta_positiva
reunion
propuesta
cliente
no_interesado
sin_respuesta
descartado
```

No borrar historial al cambiar estado.

## 10.2 Tabla de interacciones

Crear tabla separada si hoy los toques se guardan en columnas.

Sugerencia:

```sql
interactions
------------
id
prospect_id
created_at
channel
interaction_type
sequence_step
template_variant
message_rendered
response_type
notes
```

`message_rendered` permite saber exactamente qué se envió.

## 10.3 Seguimientos

Después del primer contacto:

```text
D+3
D+7
D+14
```

Tras D+14 sin respuesta:

```text
status = sin_respuesta
next_followup = NULL
```

No seguir molestando automáticamente.

## 10.4 Si responde

Cancelar secuencia pendiente inmediatamente.

Nunca mostrar follow-up automático a alguien que:

```text
respondió
dijo no
pidió no recibir mensajes
ya está en reunión/propuesta
```

---

# 11. FASE 10 — Métricas útiles

No priorizar dashboards bonitos. Solo decisiones.

## Funnel

```text
revisados
contactados
respondieron
respuesta positiva
reuniones
propuestas
clientes
```

Calcular:

```text
response_rate
positive_response_rate
meeting_rate
proposal_rate
win_rate
```

## Cortes

Por:

```text
giro
SCIAN clase
estrato
municipio
canal
variante de mensaje
fit bucket
priority bucket
```

## Regla estadística práctica

No declarar una plantilla “ganadora” con 3 o 5 contactos.

Mostrar:

```text
Muestra pequeña — todavía no concluir
```

hasta alcanzar al menos:

```text
20 contactos por variante
```

Preferible 30+ antes de decisiones fuertes.

Cambiar **una variable por prueba**.

Ejemplo:

```text
A vs B = cambia apertura
```

No cambiar al mismo tiempo asunto + longitud + CTA + segmento.

---

# 12. Receta de copy: RAPID

Usar esta receta para generar o revisar mensajes.

## R — Reconocer contexto

Una sola referencia real:

```text
Vi que {nombre} trabaja en fabricación de...
Vi en su sitio que manejan...
Encontré a {nombre} revisando empresas de...
```

No usar:

```text
Estuve investigando mucho su empresa...
Me impresionó su increíble trayectoria...
```

## A — Autoridad mínima

Solo cuando aporte confianza:

```text
Trabajé en Audi México en proyectos de digitalización y automatización.
```

No:

```text
Somos expertos líderes...
Tenemos amplia experiencia...
```

Yael vende inicialmente como profesional independiente. Hablar en primera persona.

## P — Pregunta

El objetivo del primer mensaje es **obtener información**, no cerrar la venta.

Una sola pregunta.

Preferir:

```text
¿Cómo llevan hoy...?
¿Con quién podría revisar...?
```

Evitar preguntas que presupongan dolor:

```text
¿Todavía pierden horas en Excel?
```

## I — Intervención pequeña

Si hay interés:

```text
Puedo enseñarle un ejemplo sencillo.
Puedo revisar primero el proceso y decirle qué tendría sentido automatizar.
```

No ofrecer de golpe una transformación completa.

## D — Descompresión

CTA de baja presión:

```text
Si corresponde a otra persona, ¿me indica con quién verlo?
Puedo explicárselo por aquí mismo.
```

No:

```text
Agendemos una llamada urgente.
Aproveche esta oportunidad.
Solo esta semana.
```

---

# 13. Reglas de escritura para todos los mensajes

## Tono

- humano;
- profesional;
- directo;
- sereno;
- técnico sin jerga;
- curioso;
- no agresivo.

## Regla principal

> **Cada palabra debe justificar su presencia.**

## WhatsApp primer contacto

Objetivo:

```text
35–55 palabras ideal
máximo ~65
1 pregunta
1 idea
sin links en primer toque salvo necesidad real
sin archivo adjunto
```

## Email primer contacto

Objetivo:

```text
60–95 palabras ideal
máximo ~120
asunto corto
1 pregunta principal
1 CTA pequeño
```

## Prohibido

Evitar:

```text
“Espero que se encuentre muy bien”
“Me pongo en contacto con usted para...”
“Somos una empresa líder...”
“soluciones innovadoras de vanguardia”
“transformación digital integral”
“sin sistemas caros”
“ahorre tiempo y dinero” sin contexto
“¿tiene 15 minutos mañana?”
“última oportunidad”
“sé que está ocupado”
“no quiero ser insistente” en los primeros seguimientos
“solo quería dar seguimiento”
```

No decir que algo les duele hasta que lo confirmen.

---

# 14. Variables de mensajes

Mantener un sistema pequeño.

Variables:

```text
{nombre}
{giro_corto}
{cosa}
{pregunta}
{ejemplo}
{obs}
{credencial}
```

Definiciones:

```text
{nombre}
Nombre limpio del establecimiento.

{giro_corto}
Descripción natural, no el texto legal completo del SCIAN.

{cosa}
Proceso concreto: reportes de producción, órdenes, inventario, rutas, etc.

{pregunta}
Pregunta abierta definida por giro.

{ejemplo}
Ejemplo sencillo de una solución que Yael realmente podría construir.

{obs}
SOLO evidencia pública concreta del sitio.

{credencial}
“Trabajé en Audi México en proyectos de digitalización y automatización.”
```

Eliminar:

```text
{plural}
{resultado}
```

como variables obligatorias.

Estaban haciendo que los mensajes sonaran demasiado a plantilla comercial.

Pueden existir internamente, pero no forzar su presencia.

---

# 15. Plantillas completas

Guardar estas plantillas en archivo editable, por ejemplo:

```text
config/templates.md
```

o mantener la ubicación actual si ya existe.

El código debe leerlas desde una fuente clara o definirlas estructuradamente.

No duplicar texto entre `mensajes.py` y Markdown sin una razón.

---

## 15.1 WhatsApp — A: puerta de entrada

**Uso:** no sabemos quién decide.

```text
Hola, buen día. Soy Yael de los Santos. Vi que {nombre} trabaja en {giro_corto}. Me dedico a digitalizar y automatizar procesos para empresas. ¿Con quién podría revisar cómo llevan hoy {cosa}?
```

No agregar Audi si el mensaje ya funciona sin credencial.

---

## 15.2 WhatsApp — B: pregunta directa

**Uso:** empresa bien identificada, sin evidencia web específica.

```text
Hola, buen día. Soy Yael de los Santos. Desarrollo software y automatizaciones para procesos internos. Vi a {nombre} y quería hacerles una pregunta: {pregunta}
```

---

## 15.3 WhatsApp — C: evidencia contextual

**Uso:** existe `{obs}` real.

```text
Hola, buen día. Soy Yael. {obs} Me dedico a digitalizar procesos y, al verlo, me surgió una duda: {pregunta}
```

`{obs}` debe ser una oración corta.

Ejemplos válidos:

```text
Vi en su sitio que fabrican sobre pedido.
Vi que manejan servicio y venta de refacciones.
Vi que trabajan con entregas nacionales.
```

No inventar.

---

## 15.4 WhatsApp — D: credencial

**Uso:** cuando Audi aporta confianza al segmento.

```text
Hola, buen día. Soy Yael de los Santos. Trabajé en Audi México en proyectos de digitalización y automatización. Ahora desarrollo soluciones para procesos internos. Vi a {nombre} y quería preguntar: {pregunta}
```

No usar esta variante en todos los prospectos.

---

# 16. Email — primer contacto

## Asunto A

```text
Pregunta sobre {cosa} en {nombre}
```

## Asunto B

```text
{cosa} en {nombre}
```

## Cuerpo — versión principal

```text
Buen día,

Soy Yael de los Santos. Trabajé en Audi México en proyectos de digitalización y automatización y actualmente desarrollo soluciones para procesos internos.

Vi a {nombre} y quería preguntarles algo sobre {cosa}:

{pregunta}

Si hoy les genera trabajo manual, puedo mostrarles un ejemplo sencillo de cómo podría resolverse. Si este tema corresponde a otra persona, ¿me indica con quién verlo?

Saludos,
Yael de los Santos
WhatsApp: 220 570 4385
```

## Versión sin credencial

```text
Buen día,

Soy Yael de los Santos. Desarrollo software y automatizaciones para procesos internos.

Vi a {nombre} y quería preguntarles algo sobre {cosa}:

{pregunta}

Si tiene sentido revisarlo, puedo mostrarles un ejemplo sencillo por este medio. Si corresponde a otra persona, ¿me indica con quién verlo?

Saludos,
Yael de los Santos
WhatsApp: 220 570 4385
```

---

# 17. Seguimientos

Cada seguimiento debe aportar algo nuevo.

NO escribir simplemente:

```text
Solo doy seguimiento.
¿Vio mi mensaje?
```

---

## D+3 — volver concreto

```text
Hola nuevamente. Para aterrizar lo que comentaba, en su caso pensaba en algo como {ejemplo}.

Si {cosa} hoy requiere trabajo manual, puedo enseñarle cómo se vería con un ejemplo sencillo.
```

---

## D+7 — reducir fricción

```text
Buen día. Una forma simple de verlo sería revisar primero cómo llevan hoy {cosa} y detectar qué parte realmente valdría la pena automatizar.

Si le sirve, puedo explicarle la idea por aquí mismo.
```

---

## D+14 — cierre limpio

```text
Hola. Cierro el tema por aquí para no llenar su bandeja.

Si más adelante quieren revisar {cosa} o algún proceso que esté consumiendo trabajo manual, con gusto puedo ayudarles.

Saludos,
Yael
```

Después:

```text
status = sin_respuesta
```

No más secuencia.

---

# 18. Preguntas por giro

Estas preguntas deben ser abiertas y no presupuestar que trabajan “mal”.

| Giro | `{cosa}` | `{pregunta}` | `{ejemplo}` |
|---|---|---|---|
| Autopartes | reportes de producción y calidad | ¿Cómo concentran hoy la información de producción y calidad para sus reportes? | un tablero de producción, paros y scrap alimentado desde sus registros actuales |
| Equipo de transporte | seguimiento de órdenes y producción | ¿Cómo hacen seguimiento al avance de cada orden desde que entra hasta que termina producción? | una vista de órdenes abiertas, etapa actual y responsables |
| Metalmecánica | cotizaciones, órdenes y costos | ¿Cómo controlan actualmente cotizaciones, órdenes de trabajo y costos de cada trabajo? | un control sencillo de órdenes con etapa, materiales y costo acumulado |
| Manufactura | producción e inventario | ¿Cómo generan actualmente sus reportes de producción e inventario? | un reporte de producción e inventario generado desde las mismas fuentes que ya usan |
| Comercializadora | pedidos e inventario | ¿Cómo conectan actualmente pedidos, existencias y seguimiento al cliente? | una vista única de pedidos, estatus y existencias |
| Transporte | viajes y costos por unidad | ¿Cómo llevan el control de viajes, gastos y rentabilidad por unidad? | un tablero de viajes, gastos y mantenimiento por unidad |
| Logística | entregas y costos por ruta | ¿Cómo concentran el estado de las entregas y los costos de cada ruta? | un tablero de entregas, incidencias y costo por ruta |
| Almacén | entradas, salidas y existencias | ¿Cómo registran actualmente entradas, salidas y existencias? | un control de movimientos y existencias en una sola vista |
| Constructora | costos de obra y compras | ¿Cómo comparan durante la obra lo gastado contra el presupuesto? | un tablero de costos reales contra presupuesto por obra |
| Taller industrial | órdenes y refacciones | ¿Cómo llevan el seguimiento de las órdenes desde que entran hasta que se entregan? | un control de órdenes, estatus y refacciones asociadas |
| Otro | reportes o procesos repetitivos | ¿Hay algún reporte o proceso operativo que hoy requiera capturar o consolidar información manualmente? | una automatización construida sobre los archivos y herramientas que ya usan |

---

# 19. Generación de `{giro_corto}`

No insertar el nombre SCIAN completo si suena burocrático.

Ejemplos:

```text
“Fabricación de partes de sistemas de frenos para vehículos automotores”
→ “autopartes”

“Fabricación de estructuras metálicas”
→ “estructuras metálicas”

“Autotransporte local de carga general”
→ “transporte de carga”

“Servicios de almacenamiento”
→ “almacenamiento y logística”
```

La clasificación puede seguir siendo determinista.

Guardar:

```text
giro_internal
giro_display
```

---

# 20. Validación de mensajes antes de mostrarlos

Crear una función:

```python
validate_message(message, channel)
```

Checks:

### WhatsApp

- máximo 65 palabras;
- exactamente 1 `?` preferiblemente;
- no variables sin renderizar `{...}`;
- no frases prohibidas;
- no links en primer mensaje;
- no claims no sustentados.

### Email

- máximo 120 palabras;
- asunto <= 60 caracteres idealmente;
- sin variables sin renderizar;
- sin HTML innecesario;
- firma correcta.

Si falla:

```text
⚠ Plantilla inválida
```

y explicar por qué.

---

# 21. Filtro de claims

Antes de insertar `{obs}` o hipótesis en un mensaje:

```python
if not evidence_source:
    do_not_use_observation()
```

Reglas:

### Se puede decir

```text
“Vi en su sitio que fabrican sobre pedido.”
```

si aparece públicamente.

### No se puede decir

```text
“Sé que hacen reportes manuales.”
“Sé que usan Excel.”
“Sé que tienen problemas de inventario.”
```

salvo que la empresa lo haya confirmado.

---

# 22. Respuestas y clasificación manual

No usar IA para interpretar respuestas por ahora.

Crear opciones rápidas:

```text
interesado
redirigido
pregunta
no_interesado
ya_tienen_solucion
no_es_prioridad
numero_incorrecto
correo_rebotado
otro
```

Permitir nota manual.

Esto alimentará las métricas reales.

---

# 23. FASE 11 — Mapa y rutas SOLO después de validar outreach

NO implementar todavía salvo que Fases 1–10 funcionen.

Guardar coordenadas desde ahora.

Condición para construir mapa:

```text
>= 50 contactos reales
y
evidencia de que visitas físicas tienen sentido
```

Entonces permitir:

```text
prospectos con fit >= X
dentro de zona/municipio/corredor
agrupados por proximidad
```

No optimizar rutas antes de saber que habrá visitas.

---

# 24. Definición de “terminado” para esta versión

La versión está lista para uso diario cuando Yael puede:

1. abrir Streamlit;
2. ver prospectos ordenados por prioridad;
3. entender por qué cada uno tiene ese score;
4. distinguir datos, señales e hipótesis;
5. detectar posibles cadenas;
6. ver una recomendación de canal;
7. editar una línea del mensaje;
8. copiar asunto/cuerpo o WhatsApp;
9. abrir Gmail o WhatsApp manualmente;
10. marcar “contactado”;
11. recibir el seguimiento correcto en D+3/D+7/D+14;
12. detener seguimientos si hubo respuesta;
13. clasificar la respuesta;
14. ver métricas básicas por giro, variante y canal.

Si esto funciona, **detener desarrollo y prospectar**.

---

# 25. Orden exacto de implementación

Claude Code debe ejecutar en este orden.

## Paso 1 — inspección

- [ ] mapear proyecto real;
- [ ] identificar DB y migraciones;
- [ ] identificar mensajes;
- [ ] identificar score;
- [ ] identificar enriquecedor;
- [ ] correr tests/arranque existente.

## Paso 2 — backup + migración

- [ ] backup SQLite;
- [ ] agregar campos DENUE;
- [ ] agregar campos de scoring;
- [ ] agregar grouping;
- [ ] agregar trazabilidad web;
- [ ] agregar tabla de interacciones si hace falta;
- [ ] migrar sin perder registros.

## Paso 3 — DENUE

- [ ] recuperar campos descartados;
- [ ] validar esquema;
- [ ] guardar clase/rama/subrama SCIAN;
- [ ] guardar corredor;
- [ ] guardar tipo de establecimiento;
- [ ] guardar coordenadas;
- [ ] guardar fecha_alta correctamente.

## Paso 4 — dedupe

- [ ] normalizadores;
- [ ] group key;
- [ ] possible_chain;
- [ ] razón visible.

## Paso 5 — scoring

- [ ] Fit Score;
- [ ] breakdown;
- [ ] Priority Score;
- [ ] breakdown;
- [ ] tests con casos sintéticos.

## Paso 6 — enrichment

- [ ] conservar SSRF protections;
- [ ] límites;
- [ ] caching;
- [ ] señales + evidencia;
- [ ] no claims.

## Paso 7 — plantillas

- [ ] reemplazar plantillas actuales por las nuevas;
- [ ] mantener editable la configuración;
- [ ] validar longitud;
- [ ] guardar variante usada;
- [ ] agregar tablas por giro;
- [ ] renderer deterministic.

## Paso 8 — UI

- [ ] resumen;
- [ ] cola;
- [ ] contexto;
- [ ] acción;
- [ ] score breakdown;
- [ ] evidencias;
- [ ] posibles cadenas;
- [ ] mensaje editable.

## Paso 9 — acciones

- [ ] copy email;
- [ ] copy subject;
- [ ] copy body;
- [ ] open Gmail;
- [ ] copy phone;
- [ ] copy WhatsApp text;
- [ ] open WhatsApp solo si el usuario decide.

## Paso 10 — workflow

- [ ] contactado;
- [ ] D+3;
- [ ] D+7;
- [ ] D+14;
- [ ] cancelación en respuesta;
- [ ] cierre `sin_respuesta`.

## Paso 11 — métricas

- [ ] funnel;
- [ ] por giro;
- [ ] por variante;
- [ ] por canal;
- [ ] warning de muestras pequeñas.

## Paso 12 — STOP

No añadir nada más.

Mostrar al usuario:

```text
Sistema listo para una prueba de 30–50 contactos.
```

---

# 26. Tests mínimos

## Data

- fecha_alta no se convierte en edad;
- campos DENUE faltantes no rompen import;
- coordenadas inválidas quedan NULL;
- nombre original se conserva.

## Dedupe

- misma razón social + mismo dominio => posible grupo;
- nombres parecidos sin evidencia suficiente => NO agrupar fuerte;
- group reason siempre visible.

## Score

- score 0–100;
- breakdown suma correctamente;
- no_interesado queda fuera de cola;
- follow-up vencido sube prioridad.

## Enrichment

- localhost bloqueado;
- private IP bloqueada;
- redirect a private IP bloqueado;
- respuesta demasiado grande abortada;
- timeout manejado;
- cache evita volver a descargar.

## Mensajes

- no quedan `{variables}`;
- WhatsApp <= 65 palabras;
- email <= 120;
- no contiene afirmaciones inventadas;
- variante queda registrada.

## Workflow

- contactar crea interacción;
- programa D+3;
- respuesta cancela D+3/D+7/D+14;
- D+14 sin respuesta => `sin_respuesta`.

---

# 27. Datos de configuración de Yael

Crear configuración local única, sin secretos innecesarios:

```python
OWNER_NAME = "Yael de los Santos"
OWNER_WHATSAPP = "2205704385"
OWNER_CREDENTIAL = (
    "Trabajé en Audi México en proyectos de digitalización y automatización."
)
GMAIL_URL = "https://mail.google.com/mail/u/1/#inbox?compose=new"
COUNTRY_CODE = "52"
```

Si el proyecto ya tiene config, reutilizarla.

No hardcodear el número en diez archivos.

---

# 28. Qué debe aprender el sistema de los datos reales

El producto NO debe optimizarse para “conseguir más nombres”.

Debe responder progresivamente:

```text
¿Qué giro responde más?
¿Qué tamaño responde más?
¿Qué canal funciona mejor?
¿Qué apertura funciona mejor?
¿Qué problemas despiertan conversación?
¿Qué segmentos llegan a reunión?
¿Qué segmentos llegan a propuesta?
¿Qué segmentos terminan en cliente?
```

La verdadera calibración del scoring empieza después del contacto real.

Hasta entonces los scores son reglas razonables, no conocimiento del mercado.

---

# 29. Regla final de producto

Cuando haya una duda entre:

```text
A) añadir una feature
B) contactar 10 prospectos
```

elegir B salvo que la feature esté bloqueando el contacto.

El objetivo no es construir el mejor CRM.

El objetivo es:

> **conseguir conversaciones reales con empresas que puedan necesitar automatización, software, datos o digitalización de procesos.**
