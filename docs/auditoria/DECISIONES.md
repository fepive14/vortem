# DECISIONES — Auditoría Vortem CRM

> Decisiones de arquitectura relevantes para el desacople CRM ↔ VoiceHire.
> Formato basado en el estilo de ADRs existente en `README.md`.

---

## D-001: Integración VoiceHire exclusivamente inbound (webhook → CRM)

**Contexto**
El CRM necesita recibir resultados de llamadas del servicio VoiceHire.

**Decisión**
La integración es unidireccional: VoiceHire llama al CRM vía webhook. El CRM no hace ninguna llamada HTTP saliente a VoiceHire. No existe cliente HTTP, URL de VoiceHire ni API key en el código del CRM.

**Consecuencias**
- ✅ El servicio VoiceHire puede operar, redeployarse o evolucionar sin coordinación con el CRM.
- ✅ El CRM es independiente del uptime de VoiceHire.
- ✅ La frontera está claramente definida: el contrato del webhook es la única interfaz.
- ⚠️ El CRM no puede consultar el estado de una llamada en curso ni cancelarla.

**Estado**: Confirmada (existente, no modificada por la auditoría)

---

## D-002: Autenticación del webhook via shared secret en header

**Contexto**
El endpoint `POST /api/v1/webhooks/voicehire/{organization_id}` debe autenticar al remitente sin JWT (VoiceHire no tiene sesión en el CRM).

**Decisión**
Se usa un shared secret en el header `X-VoiceHire-Secret`, comparado contra `settings.VOICEHIRE_WEBHOOK_SECRET`.

**Consecuencias**
- ✅ Simple de implementar y de configurar en VoiceHire.
- ⚠️ No protege contra replay attacks si TLS no está en uso.
- ⚠️ No protege contra tampering del body (ver H-005).
- ❌ La implementación actual usa comparación `!=` en lugar de `hmac.compare_digest` (ver H-002).

**Pendiente de decisión**
¿Se añade firma HMAC del body completo (H-005), o se documenta explícitamente que el modelo de amenaza actual no lo requiere (p. ej., comunicación en red privada con TLS mutual)?

**Estado**: Revisión pendiente (H-002 crítico a resolver; H-005 requiere decisión)

---

## D-003: URL de webhook con `organization_id` en el path

**Contexto**
El CRM es multi-tenant. VoiceHire debe poder enviar webhooks para distintas organizaciones.

**Decisión**
La URL del webhook incluye el `organization_id` como parámetro de path: `POST /api/v1/webhooks/voicehire/{organization_id}`. El webhook service filtra el lead por `lead_id AND organization_id` para garantizar aislamiento de tenant.

**Consecuencias**
- ✅ Cada organización tiene su URL de webhook propia; el aislamiento de datos está garantizado a nivel de query.
- ✅ VoiceHire puede operar con múltiples tenants del CRM sin cambios de protocolo.
- ⚠️ Si el `organization_id` se filtra o no existe, el CRM devuelve 404 (comportamiento correcto).

**Estado**: Confirmada (existente, no modificada por la auditoría)

---

## D-004: Bus de eventos interno via PostgreSQL LISTEN/NOTIFY

**Contexto**
Tras procesar un webhook, el CRM necesita disparar efectos secundarios (notificaciones a supervisores, etc.) de forma desacoplada del request HTTP.

**Decisión**
El CRM usa una tabla `events` + PostgreSQL `LISTEN/NOTIFY` como bus de eventos interno. El worker es un proceso separado que drena la tabla y ejecuta handlers.

**Consecuencias**
- ✅ No introduce dependencias de mensaje externas (no requiere Kafka, RabbitMQ, etc.).
- ✅ El worker drena eventos pendientes al arrancar, recuperando eventos perdidos si el worker estuvo offline.
- ⚠️ Existe una ventana de pérdida de eventos si el proceso muere entre el commit de negocio y la inserción del evento (ver H-007). El worker solo puede recuperar eventos que llegaron a insertarse.
- ⚠️ No escala horizontalmente de forma segura: múltiples instancias del worker pueden procesar el mismo evento (hay una guardia `processed_at IS NOT NULL` pero no hay locking).

**Pendiente de decisión**
¿Se implementa outbox pattern para cerrar la ventana de H-007, o se documenta el riesgo como aceptable dado el modelo de despliegue single-instance?

**Estado**: Revisión pendiente (H-007 a resolver)

---

---

> **Actualización 2026-06-28 — Cambio de alcance**
>
> D-001 a D-005 documentan el diseño original (integración VoiceHire). Se mantienen.
> D-006 a D-009 son nuevas decisiones requeridas para las 4 capacidades nuevas.
> Las decisiones D-006 a D-009 están **pendientes de respuesta** — no se construye nada hasta tenerlas.

---

## D-005: `campaign_id` en Lead como referencia suave a VoiceHire

**Contexto**
VoiceHire agrupa llamadas en campañas. El CRM necesita registrar a qué campaña pertenece un lead.

**Decisión**
`Lead.campaign_id` es un UUID sin FK constraint. La integridad referencial es responsabilidad de VoiceHire (que controla el cycle de vida de las campañas). El CRM almacena el UUID pero no valida su existencia en ninguna tabla.

**Consecuencias**
- ✅ El CRM no necesita conocer el esquema interno de campañas de VoiceHire.
- ✅ VoiceHire puede evolucionar su modelo de campañas sin migraciones en el CRM.
- ⚠️ Un campaign_id inválido queda almacenado silenciosamente (ver H-014).

**Estado**: Confirmada (intencional, documentada en `lead.py:58`)

---

## D-010: CLI vs endpoint para bootstrap del primer org-admin (H-009)

**Contexto**
El endpoint `POST /api/v1/setup` crea un admin global sin `organization_id`. Para operar cualquier endpoint de negocio se necesita un usuario con org. Había dos opciones para crearlo de forma segura.

**Opciones evaluadas**

| | CLI `python -m app.cli.create_admin` | Endpoint `POST /api/v1/setup/org-admin` |
|---|---|---|
| Seguridad | Solo quien tiene shell al contenedor puede ejecutarlo | Otro endpoint sin auth expuesto |
| Password | `getpass.getpass()` — nunca en HTTP ni en logs | En el body JSON |
| Complejidad | ~80 líneas, sin router ni schema Pydantic | Requiere router + schema + protección HTTP |
| Precedente | Django `createsuperuser`, Flask `flask create-user` | Menos estándar para este patrón |

**Decisión**: CLI script.

**Implementación**: `backend/app/cli/create_admin.py` con `create_org_admin(session, ...)` como capa de lógica separada (testeable) y `_main()` como entry point interactivo.

**Protección contra doble ejecución**: si ya existe algún usuario con `organization_id IS NOT NULL`, la función rechaza con `ValueError`.

**Estado**: ✅ Aprobada — 2026-06-30. Tests: 110/110 verde.

---

# Decisiones Fase 2b — Nuevas capacidades (pendientes de respuesta)

---

## D-006: Estrategia de deduplicación en la importación CSV

**Contexto**
Al importar un CSV de leads, es posible que un lead con el mismo email o teléfono ya exista en la organización (importación previa, entrada manual).

**Opciones**

| Opción | Descripción | Ventaja | Riesgo |
|--------|-------------|---------|--------|
| A — Omitir duplicado | Si ya existe un lead con el mismo email en la org, saltarse la fila | Simple, no pierde datos previos | El usuario no sabe que se descartaron datos nuevos del CSV |
| B — Actualizar | Si ya existe, actualizar sus campos con los del CSV | Los datos del CSV "ganan" sobre los existentes | Puede sobreescribir datos editados manualmente |
| C — Siempre insertar | Insertar todas las filas sin comprobar duplicados | Máxima simplicidad | Leads duplicados en BD |
| D — Reportar y decidir | Marcar duplicados en el reporte; el usuario decide qué hacer en una segunda pasada | Control total | UX más compleja |

**Clave de duplicado propuesta**: `(organization_id, email)` si email no es nulo, o `(organization_id, phone)` como fallback. Filas sin email ni phone nunca se consideran duplicadas.

**Reglas obligatorias:**
- Clave de identidad: `(organization_id, email)` si `email` no es nulo; `(organization_id, phone)` si no hay email. Filas sin email ni phone nunca se consideran duplicadas (siempre se insertan).
- La actualización NUNCA sobreescribe un campo existente con una celda vacía del CSV. Solo se actualizan los campos que vienen con valor en el CSV.

**Estado**: ✅ Aprobada — Opción B (actualizar con las reglas anteriores)

---

## D-007: Comportamiento ante fallos parciales en la importación CSV

**Contexto**
Un CSV de 1 000 filas puede tener 50 filas con formato de email inválido. ¿Qué hace el sistema?

**Opciones**

| Opción | Descripción | Ventaja | Riesgo |
|--------|-------------|---------|--------|
| A — Todo o nada | Si hay una fila inválida, se cancela toda la importación | Consistencia total | El usuario debe corregir el CSV entero y reimportar |
| B — Importar válidas, reportar fallidas | Las filas válidas se importan; las inválidas se reportan con su número de línea y motivo | Mejor UX para archivos grandes | El estado de la BD puede ser "parcial" |

**Recomendación**: Opción B. Para archivos de miles de filas, obligar a reimportar todo por 2 filas malas es una mala UX. El reporte explícito por fila da transparencia.

**Estado**: ✅ Aprobada — Opción B (importar válidas, reportar fallidas)

---

## D-008: Modelo de datos para estados/categorías personalizados por organización

**Contexto**
Cada organización necesita poder definir sus propias etiquetas o categorías para leads y contactos, y asociar acciones a esas categorías (triggers).

**Opciones**

| Opción | Descripción | Ventaja | Riesgo |
|--------|-------------|---------|--------|
| A — Tags libres validados contra catálogo | `Lead.tags JSONB` + tabla `lead_label_catalog {org_id, name, color}`. Al asignar un tag, se valida que exista en el catálogo de la org. | Flexible, sin migración de enum | Tags históricos quedan huérfanos si se borra el catálogo |
| B — Tabla de etiquetas con relación N:M | `lead_labels {id, org_id, name, color}` + `lead_label_assignments {lead_id, label_id}` | Integridad referencial real, reportes más limpios | Más tablas, más joins |
| C — Extender `LeadStatus` con valores custom en JSONB | Mantener el enum PG para los estados core (new/qualified/etc.) y añadir un campo `custom_status: str` libre | Mínimo cambio de esquema | Sin validación ni catálogo; dificulta los triggers |

**Recomendación**: Opción B. La relación N:M permite que un lead tenga múltiples etiquetas, facilita el trigger "cuando etiqueta = X", y la integridad referencial garantiza que no existan etiquetas de otra org.

**Estado**: ✅ Aprobada — Opción B (tabla `lead_labels` + relación N:M)

---

## D-009: Mitigación de la ventana de pérdida de eventos (H-007) en el contexto de triggers

**Contexto**
El motor de triggers depende del bus de eventos interno (publish → worker). Si el proceso muere entre el commit de negocio y la llamada a `publish()`, el evento nunca se inserta y el trigger no se dispara. En el contexto actual (local, sin alta disponibilidad) esto es menos crítico, pero los triggers son exactamente donde una pérdida silenciosa tiene consecuencias visibles para el usuario.

**Opciones**

| Opción | Descripción | Complejidad |
|--------|-------------|-------------|
| A — Documentar el riesgo como aceptable (local) | El worker ya drena events al arrancar; en local los reinicios son raros | Baja |
| B — Outbox pattern ligero | Insertar el evento en la misma transacción que el cambio de negocio; el worker lo lee y hace pg_notify | Media — requiere refactorizar `publisher.py` |

**Recomendación**: Opción A para el MVP local. Documentar que antes de ir a producción debe revisarse B.

**Estado**: ✅ Aprobada — Opción B (outbox pattern). Motivo: el coste es mínimo (~15 líneas reordenadas, sin tablas ni lógica nueva) y B elimina el estado inconsistente "negocio guardado pero evento perdido", que es exactamente lo que no queremos en un motor de triggers. Implementado en 2026-06-28. Tests de atomicidad verificados y pasando (107/107) el 2026-06-30.

---

### Estimación honesta: Outbox (B) vs. aceptar riesgo (A)

**¿Qué protege cada opción?**

El `_drain_pending()` del worker ya cubre el caso "el worker se cayó y perdió notificaciones". Lo que H-007 describe es un caso diferente: **el API process muere entre el `session.commit()` del negocio y la llamada a `publish()`**. En ese caso el evento nunca se inserta en la tabla `events` y no hay nada que drenar.

Para triggers, el impacto concreto sería: un lead cambia de etiqueta → el proceso cae → el trigger no se dispara → el usuario ve que el lead está en la etiqueta X pero la acción automática no ocurrió. No hay error visible, solo silencio.

**Esfuerzo de la Opción B (outbox pattern ligero)**

El cambio consiste en invertir el orden de `publish()` y `session.commit()` en todos los endpoints. En lugar de:
```python
await session.commit()          # commit negocio
await publish(session, ...)     # segunda transacción: evento
```

El nuevo patrón es:
```python
# publish() solo hace flush(), ya no hace commit interno
await publish(session, ...)     # añade Event al scope de la transacción actual
await session.commit()          # un único commit: negocio + evento
```

| Métrica | Valor |
|---------|-------|
| Archivos cambiados | 7 (`publisher.py` + 6 endpoints: leads, contacts, deals, pipelines, supervisor, webhooks) |
| Líneas netas cambiadas | ~30 (eliminar el `commit()` interno de `publisher.py`; reordenar 2 líneas por endpoint) |
| Riesgo de regresión | Bajo — los tests existentes detectarían cualquier cambio de comportamiento |
| Migración de datos | Ninguna |
| Tiempo estimado | 1–2 horas incluyendo tests |

**Calidad del resultado:** El event bus pasa de "eventual" a "atómico con el negocio". Esto es lo correcto para triggers donde el usuario espera que la acción ocurra si y solo si el cambio de estado ocurrió.

**Mi recomendación:** Opción B. El esfuerzo es bajo, el beneficio es exactamente la semántica correcta para triggers, y el riesgo de regresión es controlado por los tests existentes. La única razón para elegir A sería si hay prisa máxima; para un MVP local donde vamos a construir triggers encima, vale la pena hacerlo bien ahora.

**Archivos modificados (implementación 2026-06-28):**
- `events/publisher.py` — eliminado `await session.commit()` interno; `publish()` ahora solo hace flush + pg_notify dentro de la transacción del llamador.
- `api/v1/leads.py` — `create_lead` y `convert_lead`: publish antes de commit.
- `api/v1/contacts.py` — `create_contact`: publish antes de commit.
- `api/v1/deals.py` — `create_deal` y `update_deal`: publish (condicional) antes de commit.
- `api/v1/pipelines.py` — `create_pipeline`: publish antes de commit.
- `api/v1/supervisor.py` — `assign_lead`: publish antes de commit.
- `api/v1/webhooks.py` — status evaluado en memoria post-flush; ambos publish antes de commit; refresh después.
- `tests/test_outbox.py` — 3 tests: atomicidad en create_lead, atomicidad en webhook, ambos eventos persistidos.
