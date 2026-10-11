# Validación del brief

Referencia: `BRIEF_CLAUDE_CODE_PROSPECCION_DENUE.md`. Revisión del código, pruebas y aplicación local. El documento se utiliza como especificación del producto; sus instrucciones dirigidas a otro agente no amplían la autorización del usuario.

**Veredicto: cumplimiento funcional mayoritario, no completo.** El flujo diario existe, pero hay diferencias concretas en fechas de seguimiento, campos DENUE y presentación compacta.

| Área | Resultado | Evidencia / diferencia |
|---|---|---|
| Datos DENUE | Parcial | ID, CLEE, nombre, razón social, clase SCIAN, estrato, ubicación, contactos, corredor y alta. Guarda códigos de rama/subrama, pero no sus nombres. |
| Trazabilidad | Cumple con matiz | Se separan datos públicos, señales web, hipótesis y registros manuales. Señales conservan URL y fecha. El origen DENUE es implícito, sin bandera `source_denue`. |
| Agrupación | Cumple | Normalización, agrupación probable, explicación y miembros; no afirma sucursales como hecho. |
| FIT y prioridad | Cumple | Scores separados, componentes explicables y ajuste explícito cuando la suma se limita a 0–100. Son heurísticas, no probabilidades. |
| Enriquecimiento | Cumple con límites | Límites de páginas/tiempo/tamaño, URLs y destinos validados, citas y procedencia. La identidad del sitio requiere revisión humana. |
| Hipótesis | Cumple | Texto condicional, base y confianza separados de hechos; aviso de verificación pendiente. |
| UI de tres columnas | Adaptación deliberada | Cola fija con scroll interno; contexto dominante y acción secundaria. Vistas temáticas sustituyen la ficha interminable. Datos completos accesibles mediante navegación. |
| Cola del brief | Parcial | Nombre, giro y prioridad en el selector. FIT, municipio y contactos se consultan en el contexto para mantener una cola compacta. Atajos opcionales no implementados. |
| Recomendación de acción | Cumple | Regla determinista, canal y confianza; explicación accesible en Registro y tooltip. |
| Mensajes y envío | Cumple | Plantillas editables, validación antes de registrar, copiado y apertura manual de Gmail/WhatsApp. Llamada y WhatsApp se registran como canales distintos. |
| Conversaciones | Cumple | Respuesta manual; no reutiliza el primer contacto. Clasificación y avance de etapas. |
| Seguimientos | Parcial | Secuencia 3/4/7 días desde cada envío real. Coincide con D+3/D+7/D+14 solo si se envía puntualmente; un atraso desplaza las siguientes fechas. |
| Cancelación | Cumple | Una respuesta cancela seguimientos; el tercer seguimiento sin respuesta cierra la secuencia. |
| Métricas | Cumple | Funnel y cortes por giro, variante y canal; cautela explícita con muestras pequeñas. |
| Mapa / automatización | Conforme al alcance | No se añadió envío automático ni mapa prematuro. |

## Cambios de esta revisión

- Cola sin paginador numérico: búsqueda literal en todos los registros y carga incremental de 60 elementos dentro del scroll fijo.
- Islas, espaciado, fuentes, navegación y estados de interacción coherentes; selector de tema visible y persistente sin recarga completa.
- En pantallas bajas, mensaje por partes; copiar conserva el texto íntegro. Contacto y evidencia tienen vistas propias, también visibles en el resumen amplio.
- Correcciones de canal telefónico, validación de mensajes editados, conversación manual y explicación del límite del score.

## Limitaciones técnicas pendientes

- Los campos opcionales DENUE presentes como `null` pueden rechazar un registro si el esquema espera texto. Ausencia y `null` deberían normalizarse consistentemente.
- No existe un lockfile completo de dependencias; falta reproducibilidad exacta del entorno.
- La comprobación DNS previa reduce SSRF, pero no elimina una posible sustitución DNS entre validación y conexión.
- Registrar contacto desde sesiones concurrentes no tiene protección de idempotencia; el uso previsto es local y de una sola persona.
- CSS usa atributos de Streamlit: futuras actualizaciones requieren repetir las comprobaciones visuales.
- Pantallas inferiores a 1000 px apilan columnas. Zoom alto, textos externos extraordinariamente largos y edición libre requieren validación adicional.

## Verificación

Las pruebas funcionales usan SQLite temporal. No se enviaron mensajes ni se registraron contactos reales durante la revisión. No se probó una descarga real de DENUE.

El análisis local de Semgrep cubre cuatro familias de patrones: ejecución dinámica, shell inseguro, deserialización insegura y TLS desactivado. No sustituye CodeQL ni un análisis completo de dependencias.

Para inspeccionar cajas sin cambiar sus medidas: añadir `?layout_debug=1` a la URL. Los bordes están desactivados en el uso normal.
