# ESTADO — Auditoría Vortem CRM

> Actualizado: 2026-06-28 | Fase actual: **1b completada / Fase 2b completada — Esperando aprobación**

---

## Contexto de alcance

El objetivo cambió de "integración VoiceHire" a **"CRM funcional para uso real"** con 4 capacidades:
1. Importar bases de datos de clientes desde CSV
2. Crear registros manualmente desde la aplicación
3. Que cada organización defina sus propios estados/categorías para clientes
4. Que esos estados/categorías disparen acciones automáticas (triggers)

La app corre **solo en local** — no expuesta a internet, sin usuarios reales aún.

---

## Fases

| # | Fase | Estado |
|---|------|--------|
| 0 | Reconocimiento | ✅ Completo |
| 1 | Auditoría (superficie VoiceHire) | ✅ Completo |
| 1b | Auditoría (nueva superficie) | ✅ Completo |
| 2 | Documentación y plan (VoiceHire) | ✅ Completo |
| 2b | Plan — 4 capacidades nuevas | ✅ Completo |
| 3/4 | Bloque A: aislamiento multi-org | 🔄 En progreso — tests escritos, fixes aplicados, **pendiente de ejecución** |
| 3/4 | Bloque B: CSV import | ⏸ Pendiente |
| 3/4 | Bloque C: estados custom | ⏸ Pendiente |
| 3/4 | Bloque D: triggers (H-021, H-004, H-011) | ⏸ Pendiente — D-009 resuelto, H-007 cerrado |

---

## Cobertura de tests (estado actual)

| Área | Tests | Estado |
|------|-------|--------|
| Webhook | 6 | ✅ Pasa — falta idempotencia en contexto de triggers |
| Auth | 11 | ✅ Buena cobertura |
| Leads / Contacts / Deals | 28 | ✅ Pasa — faltan: IDOR stages, assigned_to cross-org |
| Pipelines / Stages | 8 | ✅ Pasa — falta test IDOR en list_stages |
| Notifications / Reports / Supervisor | 21 | ✅ OK |
| Setup / Users | 13 | ✅ OK |
| **CSV import** | 0 | ❌ Funcionalidad inexistente |
| **Custom labels/estados** | 0 | ❌ Funcionalidad inexistente |
| **Motor de triggers** | 0 | ❌ Funcionalidad inexistente |
| Frontend | 0 | ❌ Sin tests |
| **Total backend** | **93/93 passing** | ✅ |

---

## Hallazgos por estado y prioridad

### DIFERIDOS (reactivar antes de exponer a internet)

| ID | Severidad | Título |
|----|-----------|--------|
| H-001 | 🔴 Crítico | Secret webhook con default funcional conocido |
| H-002 | 🔴 Crítico | Timing oracle en verificación de secret |
| H-006 | 🟡 Medio | `VOICEHIRE_WEBHOOK_SECRET` ausente de `.env.example` |

### APARCADO (fuera de alcance)

| ID | Severidad | Título |
|----|-----------|--------|
| H-005 | 🟠 Alto | Sin firma HMAC del body del webhook |

### ACTIVOS — Nueva priorización

| ID | Severidad | Título | Bloque |
|----|-----------|--------|--------|
| **H-015** | 🔴 Crítico | IDOR en `GET /stages` — lee stages de otra org | A | 🔄 Fix aplicado |
| **H-016** | 🟠 Alto | `assigned_to` no validado contra la org | A | 🔄 Fix aplicado |
| **H-017** | 🟠 Alto | FKs de Deal no validadas contra la org | A | 🔄 Fix aplicado |
| **H-022** | 🟡 Medio | Conversión: stage/pipeline sin validar contra org | A | 🔄 Fix aplicado |
| **H-019** | 🟠 Alto | CSV import completamente ausente | B | ⏸ |
| **H-020** | 🟠 Alto | Sin estados/categorías personalizados por org | C | ⏸ |
| **H-021** | 🟠 Alto | Motor de triggers inexistente | D | ⏸ D-009 pendiente |
| **H-018** | 🟠 Alto | Sin validación de email/phone (crítico para CSV) | B | ⏸ |
| **H-004** | 🟠 Alto | Webhook no idempotente — duplica Activity | D | ⏸ |
| **H-007** | 🟠 Alto | Ventana de pérdida de eventos post-commit | D | 🔄 Fix aplicado (outbox) |
| **H-011** | 🟡 Medio | `LEAD_QUALIFIED` se republica en reintentos | D | ⏸ |
| **H-023** | 🟡 Medio | Sin bulk insert — CSV N filas = N transacciones | B |
| **H-025** | 🟡 Medio | List sin filtros — inviable con bases grandes | B |
| **H-026** | 🟡 Medio | Sin índice en `leads.email`/`phone` | B |
| **H-027** | 🟡 Medio | `Lead` sin `tags`/`custom_fields` (asimetría) | C |
| **H-024** | 🟡 Medio | `LeadCreate.voicehire_data` editable manualmente | B |
| **H-028** | 🟡 Medio | `currency` sin validación ISO 4217 | General |
| **H-003** | 🟠 Alto | Campo `event` webhook sin enum | General |
| **H-008** | 🟡 Medio | Sin CI/CD | General |
| **H-009** | 🟡 Medio | Bootstrap admin sin org | General |
| **H-010** | 🟡 Medio | `voicehire_data` sin límite de tamaño | General |
| **H-012** | 🟡 Medio | `X-Request-ID` sin sanitizar | General |
| **H-013** | 🟡 Medio | Sin tests frontend | General |
| **H-014** | 🟡 Medio | `campaign_id` sin documentación (DIFERIDO) | — |

---

## Plan de implementación (Fases 3 y 4)

> Entra en vigor tras aprobación explícita. Cada ítem debe tener test en verde antes de considerarse cerrado.

### Bloque A — Aislamiento multi-org (prerequisito de todo lo demás)

- [ ] **[H-015]** Fix `list_stages`: añadir `organization_id` al filtro del servicio y pasar `org_id` desde el endpoint
- [ ] **[H-015]** Test IDOR: usuario de org A no puede leer stages de org B
- [ ] **[H-016]** Validar `assigned_to` contra la org en leads, contacts, deals y `assign_lead`
- [ ] **[H-016]** Tests de asignación cross-org (debe devolver 400)
- [ ] **[H-017]** Validar `contact_id`, `stage_id`, `pipeline_id` en `deal_service.create_deal`
- [ ] **[H-022]** Idem en `conversion_service.convert_lead`
- [ ] **[H-017/H-022]** Tests de FK cross-org en deals y conversión

### Bloque B — CSV import (depende de A para el aislamiento)

- [ ] **[H-026]** Migración: índices en `leads.email` y `leads.phone` por org
- [ ] **[H-027]** Migración: añadir `tags JSONB` y `custom_fields JSONB` a `leads`
- [ ] **[H-024]** Eliminar `voicehire_data` de `LeadCreate`
- [ ] **[H-018]** Añadir validación de `EmailStr` y regex de teléfono a Lead/Contact schemas
- [ ] **[H-025]** Añadir parámetros de filtro (`search`, `status`, `assigned_to`) a `list_leads`/`list_contacts`
- [ ] **[H-023]** Implementar bulk insert en `lead_service`
- [ ] **[H-019]** Endpoint `POST /api/v1/leads/import` con: upload, parse, validate, deduplicate, bulk insert, report
- [ ] **[H-019]** Decisión y tests de: comportamiento en fallo parcial, deduplicación, límites (ver D-006, D-007)
- [ ] **[H-019]** Sanitización CSV injection

### Bloque C — Estados/categorías personalizados (depende de A y de B)

- [ ] **[H-020]** Decisión de modelo de datos (ver D-008): tags libres vs. catálogo validado
- [ ] **[H-020]** Migración: tabla `lead_labels` (o equivalente)
- [ ] **[H-020]** API: CRUD de etiquetas por org + asignar/quitar etiqueta de lead/contact
- [ ] **[H-020]** Tests: aislamiento de etiquetas entre orgs, CRUD

### Bloque D — Motor de triggers (depende de C)

- [ ] **[H-007]** Mitigación de ventana de pérdida de eventos: decisión outbox vs. documentar (ver D-004)
- [ ] **[H-004/H-011]** Idempotencia en triggers: tabla `trigger_executions`
- [ ] **[H-021]** Tabla `triggers` + API de configuración (CRUD por org, solo admin)
- [ ] **[H-021]** Handler en worker: evalúa triggers al recibir `LEAD_LABEL_CHANGED` / `LEAD_STATUS_CHANGED`
- [ ] **[H-021]** Acciones iniciales: notificación, reasignación de usuario, cambio de estado
- [ ] **[H-021]** Tests: trigger se dispara una sola vez, fallo de acción no rompe flujo principal

### Bloque General (en paralelo o al final)

- [ ] **[H-003]** Validación de enum en campo `event` del webhook
- [ ] **[H-008]** GitHub Actions CI
- [ ] **[H-012]** Sanitizar `X-Request-ID`
- [ ] **[H-028]** Validación ISO 4217 en `currency`
