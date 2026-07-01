# BITÁCORA — Auditoría Vortem CRM

> Log cronológico de cambios ejecutados. Cada entrada enlaza a un hallazgo y a un commit.
> Formato: `YYYY-MM-DD | ID hallazgo | Hash commit | Descripción`

---

## 2026-06-28

| Fecha | Hallazgo(s) | Commit | Acción |
|-------|------------|--------|--------|
| 2026-06-28 | — | — | Fase 0 completada: reconocimiento del repositorio, mapeo de arquitectura, identificación del contrato webhook |
| 2026-06-28 | — | — | Fase 1 completada: auditoría de seguridad, rendimiento, correctitud y arquitectura; 14 hallazgos registrados (H-001..H-014) |
| 2026-06-28 | — | — | Fase 2 completada: artefactos de auditoría creados (`ESTADO.md`, `HALLAZGOS.md`, `BITACORA.md`, `DECISIONES.md`); plan priorizado en `ESTADO.md`; esperando aprobación para Fase 3 |
| 2026-06-28 | — | — | **Cambio de alcance**: objetivo cambia de integración VoiceHire a CRM funcional local con 4 capacidades (CSV import, creación manual, estados custom, triggers). H-001/H-002/H-006 diferidos; H-005 aparcado; H-004/H-007/H-011 suben de prioridad |
| 2026-06-28 | H-015..H-028 | — | Fase 1b completada: 14 hallazgos nuevos registrados en HALLAZGOS.md — incluye IDOR crítico en `GET /stages`, ausencia de las 4 capacidades, falta de validaciones cross-org |
| 2026-06-28 | — | — | Fase 2b completada: ESTADO.md actualizado con plan de 4 bloques (A: aislamiento, B: CSV, C: estados, D: triggers); DECISIONES.md actualizado con D-006..D-009 pendientes de respuesta; esperando aprobación |

---

---

## Bloque A — Aislamiento multi-organización (H-015, H-016, H-017, H-022)

| Fecha | Hallazgo(s) | Commit | Acción |
|-------|------------|--------|--------|
| 2026-06-28 | H-015..H-017, H-022 | pendiente | Tests de caracterización: `tests/test_org_isolation.py` (13 tests: 9 seguridad + 4 happy-path) |
| 2026-06-28 | H-015 | pendiente | `stage_service.list_stages`: añadido `organization_id` al WHERE; `stages.py` pasa `org_id` |
| 2026-06-28 | H-016 | pendiente | `lead_service`: validación `assigned_to` en create/update; `contact_service`: idem; `supervisor_service.assign_lead`: nuevo parámetro `organization_id` + validación; endpoints actualizados |
| 2026-06-28 | H-017 | pendiente | `deal_service.create_deal`: valida `contact_id`, `pipeline_id`, `stage_id` contra org; `update_deal`: valida `stage_id`, `pipeline_id`, `assigned_to` |
| 2026-06-28 | H-022 | pendiente | `conversion_service.convert_lead`: valida `stage_id`, `pipeline_id` contra org cuando `create_deal=True` |

_Commits del Bloque A se registrarán cuando el usuario ejecute los tests y confirme que pasan._

---

## Bloque D (H-007) — Outbox pattern

| Fecha | Hallazgo(s) | Commit | Acción |
|-------|------------|--------|--------|
| 2026-06-28 | H-007 | ver commit | Tests de atomicidad: `tests/test_outbox.py` (3 tests: fallo en create_lead, fallo en webhook, ambos eventos presentes) |
| 2026-06-28 | H-007 | ver commit | `publisher.py`: eliminado `await session.commit()` interno; log renombrado a `event_staged` |
| 2026-06-28 | H-007 | ver commit | `api/v1/leads.py`: `create_lead` y `convert_lead` — publish antes de commit |
| 2026-06-28 | H-007 | ver commit | `api/v1/contacts.py`: `create_contact` — publish antes de commit |
| 2026-06-28 | H-007 | ver commit | `api/v1/deals.py`: `create_deal` y `update_deal` — publish (condicional) antes de commit; condición evaluada con stage_id en-memoria post-flush |
| 2026-06-28 | H-007 | ver commit | `api/v1/pipelines.py`: `create_pipeline` — publish antes de commit |
| 2026-06-28 | H-007 | ver commit | `api/v1/supervisor.py`: `assign_lead` — publish antes de commit |
| 2026-06-28 | H-007 | ver commit | `api/v1/webhooks.py`: status evaluado en-memoria (post-flush de process_voicehire_event); ambos publish antes de commit; refresh después |
| 2026-06-30 | H-007 | ver commit | **Harness de test corregido** — `conftest.py`: `_override_get_session` con rollback en excepción + `raise_app_exceptions=False`; `test_outbox.py`: `lead_id` capturado pre-request para evitar MissingGreenlet post-rollback |
| 2026-06-30 | — | ver commit | **structlog corregido** — `app/core/logging.py`: `ProcessorFormatter` usa `foreign_pre_chain` para que `add_logger_name` acceda a `_record` antes de que `remove_processors_meta` lo elimine |
| 2026-06-30 | H-007 | 412d3fa | Suite completa: **107/107 verdes**. H-007 cerrado. |

---

## Bloque H-009 — CLI bootstrap org-admin

| Fecha | Hallazgo(s) | Commit | Acción |
|-------|------------|--------|--------|
| 2026-06-30 | H-009 | ver commit | `app/cli/__init__.py` + `app/cli/create_admin.py`: CLI script con `create_org_admin()` (lógica) + `_main()` (interactivo con getpass) |
| 2026-06-30 | H-009 | ver commit | `tests/test_cli_create_admin.py`: 3 tests — happy path, ya existe org-admin, reutiliza org existente |
| 2026-06-30 | H-009 | ver commit | `DEPLOYMENT.md`: Step 5b reemplaza SQL workaround con CLI; Step 4 añade nota sobre migraciones obligatorias antes del CLI |
| 2026-06-30 | H-009 | ver commit | Login confirmado en localhost:3000. Suite completa: **110/110 verdes**. H-009 cerrado. |

---

## Épica V — Verticales de negocio / Fase 1 (H-029)

| Fecha | Hallazgo(s) | Commit | Acción |
|-------|------------|--------|--------|
| 2026-07-01 | — | — | Diseño aprobado: arquitectura (D-011), relación 1:N Dueño↔Mascota (D-012), columna tipada vs JSONB (D-013). Plan de 4 fases registrado en ESTADO.md y DECISIONES.md |
| 2026-07-01 | H-029 | pendiente | `alembic/versions/0005_verticals.py`: enum `org_vertical` + `organizations.vertical NOT NULL DEFAULT 'generic'` |
| 2026-07-01 | H-029 | pendiente | `models/organization.py`: enum `OrgVertical {generic, veterinary}` + campo `vertical` con `create_type=False` |
| 2026-07-01 | H-029 | pendiente | `schemas/organization.py`: `vertical: OrgVertical` en `OrganizationResponse` + nuevo `SetOrgVerticalRequest` |
| 2026-07-01 | H-029 | pendiente | `services/setup_service.py`: `SetupRequest` acepta `vertical` (default `generic`); `bootstrap()` lo propaga al crear la org |
| 2026-07-01 | H-029 | pendiente | `cli/create_admin.py`: `create_org_admin()` acepta `vertical`; `_main()` lo solicita interactivamente con validación |
| 2026-07-01 | H-029 | pendiente | `api/v1/organizations.py` (nuevo): `PATCH /{org_id}/vertical` — guard `is_global_admin`; 403 a usuarios normales |
| 2026-07-01 | H-029 | pendiente | `api/v1/router.py`: registra el nuevo router en `/api/v1/organizations` |
| 2026-07-01 | H-029 | pendiente | `tests/conftest.py`: crea/destruye tipo `org_vertical` en el esquema de test |
| 2026-07-01 | H-029 | pendiente | `tests/test_verticals.py`: 8 tests — default generic, CLI con veterinary, setup con/sin vertical, guard 403, global_admin puede cambiar, enum inválido 422, org inexistente 404 |
