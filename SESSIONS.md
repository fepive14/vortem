# Vortem — Session Summaries

---

## Session Closing Checklist

> **Mandatory steps at the end of every development session.**

```
[ ] 1. Run tests — all must pass before closing
        docker compose exec backend pytest -v

[ ] 2. Update SESSIONS.md — add or update the summary for this session
        (bugs found, decisions made, files changed, final test count)

[ ] 3. Commit everything — use Conventional Commits format
        feat:     new feature
        fix:      bug fix
        docs:     documentation only
        refactor: no behaviour change
        test:     adding or fixing tests
        chore:    tooling, deps, config

        git add <files>
        git commit -m "type: short description"

[ ] 4. Push to origin main
        git push
```

No session is complete until all four steps are done.

---

## Session 1 — Phase 1A: Backend Foundation

**Date:** 2026-03-28
**Phase:** 1A
**Status:** Complete — 15/15 tests passing

---

### What was built

#### Infrastructure
| File | Description |
|---|---|
| `docker-compose.yml` | 4 services: `db` (postgres:16), `redis` (redis:7), `backend` (FastAPI), `worker` (event bus). Healthchecks on db and redis. Persistent volumes. |
| `backend/Dockerfile` | Multi-stage: `base → deps → development/production`. Hot-reload in dev, 4 uvicorn workers in prod. |
| `.env.example` | All required variables with inline comments. |
| `.gitattributes` | `eol=lf` for all text files — ensures Unix line endings in the repo regardless of contributor OS. |

#### Configuration & Core
| File | Description |
|---|---|
| `backend/app/core/config.py` | `pydantic-settings` — validates `DATABASE_URL` scheme at startup, exposes `worker_dsn` as a derived property. |
| `backend/app/core/logging.py` | `structlog` — JSON in production, colored console in development. `request_id` injected into every log via `contextvars`. |
| `backend/app/core/security.py` | bcrypt cost=12 for passwords. JWT HS256 with `token_type` claim to distinguish access vs. refresh tokens. |

#### Database
| File | Description |
|---|---|
| `backend/app/db/session.py` | Async SQLAlchemy engine + `get_session` dependency. Auto-commit/rollback. `pool_pre_ping=True`. |
| `backend/app/db/redis.py` | Shared async connection pool. `get_redis` FastAPI dependency. |

#### Models
| File | Description |
|---|---|
| `backend/app/models/base.py` | UUID PK via `gen_random_uuid()`, `created_at` / `updated_at` with `server_default`. |
| `backend/app/models/organization.py` | Tenant entity. Self-referential parent/child hierarchy. `settings: JSONB`. `lazy="raise"` on relationships to prevent N+1. |
| `backend/app/models/user.py` | `UserRole` enum (`admin/supervisor/agent/viewer`). `SAEnum(create_type=False)` to bind to the existing PG type. CHECK constraint: non-global users must have `organization_id`. `timezone` field for future WFM module. |
| `backend/app/models/event.py` | Persistent event bus record. `processed_at`, `failed_at`, `error` fields. |

#### Migrations
| File | Description |
|---|---|
| `backend/alembic/env.py` | Async-capable. Online mode uses `create_async_engine(settings.DATABASE_URL)` directly — never reads the psycopg2 URL from the ini config. Offline mode uses psycopg2 for SQL generation only. |
| `backend/alembic/versions/0001_initial.py` | Idempotent: `CREATE EXTENSION IF NOT EXISTS`, `CREATE TABLE IF NOT EXISTS`, `DO $$ ... $$` for the enum. Tables: `organizations`, `users`, `events`. Partial index on `events(processed_at) WHERE processed_at IS NULL AND failed_at IS NULL` for the worker. |

#### API & Services
| File | Description |
|---|---|
| `backend/app/api/v1/setup.py` | `POST /api/v1/setup` — thin router: validate → call service → commit → publish event. Returns 403 if already initialized. |
| `backend/app/api/v1/auth.py` | `POST /login`, `POST /logout`, `POST /refresh`, `GET /me`. httpOnly cookies, `secure=True` in production. |
| `backend/app/api/v1/router.py` | Aggregates all v1 sub-routers under `/api/v1`. |
| `backend/app/services/setup_service.py` | Creates first Organization + global admin User. Uses `flush()` — lets the endpoint decide when to commit. |
| `backend/app/services/auth_service.py` | Timing-safe login (dummy bcrypt comparison on unknown email). Token rotation on refresh. Invariant checks for inactive users and missing org. |

#### Middleware & Auth
| File | Description |
|---|---|
| `backend/app/middleware/auth.py` | `require_auth` — any authenticated user. `require_roles(*roles)` — factory, global admins bypass role checks. `get_current_org_id(user)` — standard helper for tenant-scoped queries in services. |

#### Event Bus
| File | Description |
|---|---|
| `backend/app/events/catalog.py` | `EventType` constants. Single source of truth for all event type strings. |
| `backend/app/events/publisher.py` | INSERT into `events` + `pg_notify('vortem_events', event_id)` in the same transaction. Always called after the business transaction commits. |
| `backend/app/events/worker.py` | Separate process. `LISTEN vortem_events`. Drains pending events on startup (guards against missed notifications during downtime). Auto-reconnects on connection loss. Handler registry by event type. |

#### Tests
| File | Description |
|---|---|
| `backend/tests/conftest.py` | `NullPool` engine. `TRUNCATE ... CASCADE` after every test for isolation (chosen over SAVEPOINT — more reliable when service code calls `session.commit()`). Fixtures: `test_org`, `test_user`, `test_global_admin`, `access_token`, `refresh_token_fixture`. |
| `backend/tests/test_setup.py` | 4 tests: happy path, already initialized (403), weak password (422), invalid email (422). |
| `backend/tests/test_auth.py` | 11 tests: login success/wrong password/unknown email/inactive user, logout, refresh success/no cookie/invalid token, me authenticated/unauthenticated/invalid token. |

---

### Architecture decisions

**Multi-tenant by design**
Every future data model filters by `organization_id`. `get_current_org_id(user)` in `middleware/auth.py` is the standard accessor — services never handle the NULL case directly.

**Global admin pattern**
`is_global_admin=True` users have `organization_id=NULL`. The DB CHECK constraint enforces that non-global users must have an org. The inverse invariant ("global admin has no org") is enforced in `auth_service`, not the DB, to keep schema logic minimal.

**Events always after commit**
`publisher.py` is called only after the business transaction commits. This guarantees the worker never reads a record that isn't yet visible in the DB.

**Session lifecycle**
`get_session` auto-commits and auto-rolls back. Services call `flush()` (not `commit()`) unless they are the final step. Endpoints call explicit `commit()` before publishing events.

**httpOnly cookies over Authorization header**
Access and refresh tokens are stored in httpOnly cookies. `secure=True` is set only in production. This makes the API compatible with SSR frontends and eliminates XSS token theft.

**Test isolation via TRUNCATE**
SAVEPOINTs were considered but dropped: when service code calls `session.commit()` inside an endpoint, it commits the savepoint and the isolation breaks. `TRUNCATE ... RESTART IDENTITY CASCADE` after each test is simpler and reliable.

---

### Bugs found and resolved

| Bug | Root cause | Fix |
|---|---|---|
| `asyncio extension requires an async driver` | `alembic/env.py` injected the psycopg2 URL into the Alembic config globally, so `async_engine_from_config` read a sync URL. | Online mode now calls `create_async_engine(settings.DATABASE_URL)` directly, bypassing the config entirely. psycopg2 URL is only used for offline SQL generation. |
| `ImportError: email-validator is not installed` | `pydantic[email]` extra was not declared; `EmailStr` requires it at runtime. | Changed `"pydantic>=2.10.0"` to `"pydantic[email]>=2.10.0"` in `pyproject.toml`. |
| `expected bcrypt hash, got bcrypt config string` | passlib 1.7.x is incompatible with bcrypt ≥ 4.1 (internal API removed). | Pinned `bcrypt==4.0.1` in `pyproject.toml`. |
| `malformed bcrypt hash (checksum must be exactly 31 chars)` | The `dummy_hash` in `auth_service.py` used for timing-safe login was a truncated 59-char string (missing 1 char in the checksum). | Replaced with a correctly generated 60-char hash via `bcrypt.hashpw(b"dummy", bcrypt.gensalt(rounds=12))`. |
| Docker binding to `5432`/`6379` instead of `5433`/`6380` | `.env` explicitly set `POSTGRES_PORT=5432` and `REDIS_PORT=6379`, overriding the `docker-compose.yml` defaults (`:-5433`, `:-6380`). `${VAR:-default}` only applies when the variable is absent. | Updated `.env` and `.env.example` to `POSTGRES_PORT=5433` and `REDIS_PORT=6380`. |

---

### Final state

```
backend/tests/test_setup.py::test_setup_happy_path         PASSED
backend/tests/test_setup.py::test_setup_already_initialized PASSED
backend/tests/test_setup.py::test_setup_weak_password       PASSED
backend/tests/test_setup.py::test_setup_invalid_email       PASSED
backend/tests/test_auth.py::test_login_success              PASSED
backend/tests/test_auth.py::test_login_wrong_password       PASSED
backend/tests/test_auth.py::test_login_nonexistent_email    PASSED
backend/tests/test_auth.py::test_login_inactive_user        PASSED
backend/tests/test_auth.py::test_logout_clears_cookies      PASSED
backend/tests/test_auth.py::test_refresh_success            PASSED
backend/tests/test_auth.py::test_refresh_no_cookie          PASSED
backend/tests/test_auth.py::test_refresh_invalid_token      PASSED
backend/tests/test_auth.py::test_me_authenticated           PASSED
backend/tests/test_auth.py::test_me_unauthenticated         PASSED
backend/tests/test_auth.py::test_me_invalid_token           PASSED

15 passed in N.NNs
```

Git: `650a674` — 46 files, 2507 insertions.

---

### What comes next — Phase 1B

Phase 1B will build the first business module on top of this foundation:

- **Contact model** — name, email, phone, company, `organization_id`, `owner_id` (FK to User), `source` enum, custom fields (`JSONB`)
- **Lead model** — FK to Contact, `stage_id` (FK to Pipeline stage), `value`, `currency`, `probability`, `expected_close_date`, `organization_id`
- **CRUD endpoints** — `POST/GET/PATCH/DELETE /api/v1/contacts` and `/api/v1/leads`, all scoped by `organization_id` via `get_current_org_id`
- **Events** — `contact.created`, `lead.created`, `lead.stage_changed` added to `EventType`
- **Tests** — happy path + permission boundary tests (agent cannot delete, viewer cannot write)

All endpoints will follow the same thin-router / service-layer pattern established in Phase 1A.

---

## Session 2 — Phase 1B: Contacts, Leads, CRUD

**Date:** 2026-03-28
**Phase:** 1B
**Status:** Complete — 35/35 tests passing

---

### What was built

#### Models
| File | Description |
|---|---|
| `backend/app/models/contact.py` | Contact entity. Fields: first_name, last_name, phone, email, company, position, country, status (SAEnum: active/inactive/do_not_contact), lead_id (nullable FK), assigned_to (nullable FK), tags (JSONB), custom_fields (JSONB). `lazy="raise"` on all relationships. |
| `backend/app/models/lead.py` | Lead entity. Fields: first_name, last_name, phone, email, country, status (SAEnum: new/contacted/qualified/converted/discarded), source (SAEnum: csv_import/manual/api/voicehire), campaign_id (nullable UUID), assigned_to (nullable FK), voicehire_data (JSONB). `lazy="raise"` on all relationships. |

#### Migration
| File | Description |
|---|---|
| `backend/alembic/versions/0002_contacts_leads.py` | Idempotent. Creates enums contact_status, lead_status, lead_source with DO $$ ... $$ guards. Creates tables leads and contacts (in that order — contacts FK references leads). Indexes on organization_id, assigned_to, and leads.status. |

#### Schemas
| File | Description |
|---|---|
| `backend/app/schemas/contact.py` | ContactCreate, ContactUpdate, ContactRead (from_attributes=True). |
| `backend/app/schemas/lead.py` | LeadCreate, LeadUpdate, LeadRead (from_attributes=True). |

#### Services
| File | Description |
|---|---|
| `backend/app/services/contact_service.py` | create_contact (publishes CONTACT_CREATED), list_contacts (scoped by org, ordered by created_at DESC), get_contact, update_contact, delete_contact. |
| `backend/app/services/lead_service.py` | Same shape as contact_service. create_lead publishes LEAD_CREATED. |

#### Events
| File | Description |
|---|---|
| `backend/app/events/catalog.py` | Added: CONTACT_CREATED, LEAD_CREATED, LEAD_STAGE_CHANGED. |

#### API
| File | Description |
|---|---|
| `backend/app/api/v1/contacts.py` | POST/GET/GET/{id}/PATCH/{id}/DELETE/{id}. Agents cannot delete (403). Viewers cannot write (403). All endpoints scoped by organization_id. |
| `backend/app/api/v1/leads.py` | Same permission structure as contacts. |
| `backend/app/api/v1/router.py` | Updated to include contacts and leads routers. |

#### Tests
| File | Description |
|---|---|
| `backend/tests/test_contacts.py` | 10 tests: create, list empty, list returns created, get success, get not found, update as agent, update as viewer (403), delete as supervisor, delete as agent (403), isolation by org. |
| `backend/tests/test_leads.py` | 10 tests: same coverage pattern as test_contacts.py. |

---

### Architecture decisions

**Permission model for CRUD**
- All authenticated roles can read (GET) contacts and leads.
- Agents can create and update but cannot delete.
- Only admin and supervisor can delete.
- Viewers cannot write (create, update, or delete).
- This is enforced at the router level via `require_roles()` from `middleware/auth.py`.

**Org isolation at the service layer**
Every read in list/get filters by `organization_id`. A contact that exists in org A is not visible from org B even if you have a valid token for org B.

---

### Bugs found and resolved

| Bug | Root cause | Fix |
|---|---|---|
| `MissingGreenlet` on PATCH response | After `session.flush()` with `onupdate=func.now()` on `updated_at`, SQLAlchemy marks the column as expired. Pydantic's synchronous attribute access then hits a `MissingGreenlet` error when trying to serialize the response. | Added `await session.refresh(updated)` after `session.commit()` in both PATCH endpoints (contacts and leads), before serializing the response. |

---

### Final state
```
backend/tests/test_setup.py::test_setup_happy_path              PASSED
backend/tests/test_setup.py::test_setup_already_initialized     PASSED
backend/tests/test_setup.py::test_setup_weak_password           PASSED
backend/tests/test_setup.py::test_setup_invalid_email           PASSED
backend/tests/test_auth.py::test_login_success                  PASSED
backend/tests/test_auth.py::test_login_wrong_password           PASSED
backend/tests/test_auth.py::test_login_nonexistent_email        PASSED
backend/tests/test_auth.py::test_login_inactive_user            PASSED
backend/tests/test_auth.py::test_logout_clears_cookies          PASSED
backend/tests/test_auth.py::test_refresh_success                PASSED
backend/tests/test_auth.py::test_refresh_no_cookie              PASSED
backend/tests/test_auth.py::test_refresh_invalid_token          PASSED
backend/tests/test_auth.py::test_me_authenticated               PASSED
backend/tests/test_auth.py::test_me_unauthenticated             PASSED
backend/tests/test_auth.py::test_me_invalid_token               PASSED
backend/tests/test_contacts.py::test_create_contact_success         PASSED
backend/tests/test_contacts.py::test_list_contacts_empty            PASSED
backend/tests/test_contacts.py::test_list_contacts_returns_created  PASSED
backend/tests/test_contacts.py::test_get_contact_success            PASSED
backend/tests/test_contacts.py::test_get_contact_not_found          PASSED
backend/tests/test_contacts.py::test_update_contact_as_agent        PASSED
backend/tests/test_contacts.py::test_update_contact_as_viewer_forbidden PASSED
backend/tests/test_contacts.py::test_delete_contact_as_supervisor   PASSED
backend/tests/test_contacts.py::test_delete_contact_as_agent_forbidden PASSED
backend/tests/test_contacts.py::test_contact_isolated_by_org        PASSED
backend/tests/test_leads.py::test_create_lead_success               PASSED
backend/tests/test_leads.py::test_list_leads_empty                  PASSED
backend/tests/test_leads.py::test_list_leads_returns_created        PASSED
backend/tests/test_leads.py::test_get_lead_success                  PASSED
backend/tests/test_leads.py::test_get_lead_not_found                PASSED
backend/tests/test_leads.py::test_update_lead_as_agent              PASSED
backend/tests/test_leads.py::test_update_lead_as_viewer_forbidden   PASSED
backend/tests/test_leads.py::test_delete_lead_as_supervisor         PASSED
backend/tests/test_leads.py::test_delete_lead_as_agent_forbidden    PASSED
backend/tests/test_leads.py::test_lead_isolated_by_org              PASSED

35 passed in N.NNs
```

Git: `f4144c1` — pushed to origin/main.

---

### What comes next — Phase 1C

- Pipeline, Stage, Deal models
- Lead → Contact conversion flow (`POST /leads/{id}/convert`)
- Activity model (used by conversion to persist voicehire_data)
- Tests: pipelines (8), deals (8), conversion (6) → target 57/57

---

## Session 3 — Phase 1C: Pipeline, Deals, Conversion

**Date:** 2026-03-28
**Phase:** 1C
**Status:** Complete — 57/57 tests passing

---

### What was built

#### Models
| File | Description |
|---|---|
| `backend/app/models/pipeline.py` | Pipeline entity. organization_id nullable (null = instance-level default). Fields: name, description, is_default. `lazy="raise"` on all relationships. |
| `backend/app/models/stage.py` | Stage entity. Fields: name, order, color, probability (0–100), is_won, is_lost, pipeline_id (FK). `lazy="raise"` on all relationships. |
| `backend/app/models/deal.py` | Deal entity. Fields: name, value (Numeric 14,2), currency, contact_id, stage_id, pipeline_id, assigned_to, expected_close_date, closed_at, notes, custom_fields (JSONB). `lazy="raise"` on all relationships. |
| `backend/app/models/activity.py` | Activity entity. Polymorphic — covers call, note, task, email, meeting, voicehire_call. Fields: type (SAEnum), contact_id, lead_id, deal_id, assigned_to, due_at, completed_at, body, metadata (JSONB). `lazy="raise"` on all relationships. |
| `backend/app/models/organization.py` | Added pipeline_id (nullable FK → pipelines.id) — null = inherit instance default. |

#### Migration
| File | Description |
|---|---|
| `backend/alembic/versions/0003_pipeline_stages_deals.py` | Idempotent. Creates enum activity_type with DO $$ guard. Creates tables: pipelines, stages, deals, activities. ALTER TABLE organizations ADD COLUMN IF NOT EXISTS pipeline_id. Indexes: stages(pipeline_id), UNIQUE stages(pipeline_id, order), deals(organization_id/contact_id/stage_id/pipeline_id), activities(contact_id/lead_id). |

#### Schemas
| File | Description |
|---|---|
| `backend/app/schemas/pipeline.py` | PipelineCreate, PipelineUpdate, PipelineRead (from_attributes=True). |
| `backend/app/schemas/stage.py` | StageCreate, StageUpdate, StageRead (from_attributes=True). |
| `backend/app/schemas/deal.py` | DealCreate, DealUpdate, DealRead (from_attributes=True). |
| `backend/app/schemas/conversion.py` | ConvertLeadRequest (assigned_to, create_deal, deal_name, stage_id, pipeline_id, value, currency). ConvertLeadResponse (contact: ContactRead, deal: DealRead | None). |

#### Services
| File | Description |
|---|---|
| `backend/app/services/pipeline_service.py` | create_pipeline (publishes PIPELINE_CREATED), list_pipelines, get_pipeline, update_pipeline, delete_pipeline. |
| `backend/app/services/stage_service.py` | create_stage (validates pipeline belongs to org), list_stages (ORDER BY order ASC), get_stage, update_stage, delete_stage. |
| `backend/app/services/deal_service.py` | create_deal (publishes DEAL_CREATED), list_deals, get_deal, update_deal (publishes DEAL_STAGE_CHANGED if stage_id changes), delete_deal. |
| `backend/app/services/conversion_service.py` | convert_lead: fetches lead → 404 if missing, 400 if already converted → creates Contact → creates Activity if voicehire_data non-empty → sets lead.status='converted' → optionally creates Deal → flush. Endpoint commits and publishes LEAD_CONVERTED. |

#### Events
| File | Description |
|---|---|
| `backend/app/events/catalog.py` | Added: PIPELINE_CREATED, DEAL_CREATED, DEAL_STAGE_CHANGED, LEAD_CONVERTED. |

#### API
| File | Description |
|---|---|
| `backend/app/api/v1/pipelines.py` | POST/GET/GET/{id}/PATCH/{id}/DELETE/{id}. Create/update: admin+supervisor. Delete: admin only. |
| `backend/app/api/v1/stages.py` | Same pattern. GET list takes ?pipeline_id= query param. Delete: admin only. |
| `backend/app/api/v1/deals.py` | All roles can create/read. Agents can update. Delete: admin+supervisor only. |
| `backend/app/api/v1/leads.py` | Added POST /{lead_id}/convert — require_roles(admin, supervisor). Returns ConvertLeadResponse. |
| `backend/app/api/v1/router.py` | Added pipelines, stages, deals routers. |

#### Tests
| File | Description |
|---|---|
| `backend/tests/test_pipelines.py` | 8 tests: create as supervisor (201), create as agent (403), list, get not found (404), update, delete as admin (204), delete as supervisor (403), isolation by org. |
| `backend/tests/test_deals.py` | 8 tests: create (201), list empty, get success, get not found (404), update stage, delete as agent (403), delete as supervisor (204), isolation by org. |
| `backend/tests/test_conversion.py` | 6 tests: creates contact, sets lead status, idempotency (400), not found (404), with deal, voicehire_data creates Activity. |

---

### Architecture decisions

**Pipeline scoping**
`pipeline_id` on Organization is nullable. Null = organization inherits the instance-level default pipeline (where `pipeline.organization_id IS NULL`). Each org can optionally override with its own pipeline.

**Activity as audit trail for conversion**
When a Lead with non-empty `voicehire_data` is converted, the data is persisted as an `Activity(type='voicehire_call')`. This keeps the full call history attached to the Lead and Contact without polluting the Contact model with AI-specific fields.

**Explicit UUID generation in conversion**
SQLAlchemy's `default=uuid.uuid4` is invoked at flush time, not at object construction. When a Deal needs `contact.id` before flush, the fix is to generate the UUID explicitly (`contact_id = uuid.uuid4()`) and pass it to both objects rather than relying on the ORM default.

---

### Bugs found and resolved

| Bug | Root cause | Fix |
|---|---|---|
| `contact.id` is `None` when constructing Deal | SQLAlchemy's `default=uuid.uuid4` runs at `flush()`, not at `session.add()` or object construction. Deal was reading `contact.id` before the first flush. | Generate `contact_id = uuid.uuid4()` explicitly before constructing Contact, then pass the same value to both Contact and Deal. |

---

### Final state
```
57 passed in 60.12s (0:01:00)
```

Git: `f261e79` — pushed to origin/main.

---

### What comes next — Phase 1D

- Notifications model + service
- `GET /api/v1/notifications` — paginated, scoped by user
- `PATCH /api/v1/notifications/{id}/read` — mark as read
- `GET /api/v1/notifications/unread-count` — for polling (every 30s from frontend)
- Event handlers in worker.py that generate Notification records for: lead.converted, deal.stage_changed, task due
- Tests: 8 tests → target 65/65

---

## Session 4 — Phase 1D: Supervisor, Webhooks, Notifications

**Date:** 2026-03-28
**Phase:** 1D
**Status:** Complete — 76/76 tests passing

---

### What was built

#### Models
| File | Description |
|---|---|
| `backend/app/models/notification.py` | Notification entity. Fields: user_id (FK → users), type (str), priority (SAEnum: normal/high), title, body, entity_type (str, nullable), entity_id (UUID, nullable), read_at (nullable). Polymorphic reference to any entity. |

#### Migration
| File | Description |
|---|---|
| `backend/alembic/versions/0004_notifications_webhook.py` | Creates enum notification_priority with DO $$ guard. Creates table notifications. Indexes on user_id, (user_id, read_at), organization_id. Also patches: ALTER TABLE events ADD COLUMN IF NOT EXISTS updated_at (backfill for existing installs where 0001 omitted it). ALTER TABLE organizations DROP CONSTRAINT IF EXISTS fk_organizations_pipeline_id before drop_all teardown. |

#### Schemas
| File | Description |
|---|---|
| `backend/app/schemas/notification.py` | NotificationRead (from_attributes=True). |
| `backend/app/schemas/webhook.py` | VoiceHireWebhookPayload: lead_id, event, status (nullable), voicehire_data (dict), campaign_id (nullable). |
| `backend/app/schemas/lead.py` | Added LeadAssignRequest (assigned_to: UUID). |

#### Services
| File | Description |
|---|---|
| `backend/app/services/notification_service.py` | create_notification, list_notifications (by user+org, DESC), get_unread_count (COUNT WHERE read_at IS NULL), mark_as_read. |
| `backend/app/services/supervisor_service.py` | list_qualified_unassigned (status=qualified AND assigned_to IS NULL, ORDER BY created_at ASC — FIFO queue), assign_lead. |
| `backend/app/services/webhook_service.py` | process_voicehire_event: fetch lead → merge voicehire_data (update, not replace) → update status if provided → set campaign_id if missing → create Activity(type=voicehire_call) → flush. Endpoint commits and publishes events. |

#### Events
| File | Description |
|---|---|
| `backend/app/events/catalog.py` | Added: LEAD_ASSIGNED, LEAD_QUALIFIED, VOICEHIRE_CALL_COMPLETED, NOTIFICATION_CREATED. |
| `backend/app/events/worker.py` | Added 3 handlers: LEAD_QUALIFIED → notify all supervisors in org (priority=high). LEAD_ASSIGNED → notify assigned agent (priority=high). DEAL_STAGE_CHANGED → notify deal.assigned_to (priority=normal). Each handler uses its own session and catches exceptions without crashing the worker loop. |

#### API
| File | Description |
|---|---|
| `backend/app/api/v1/notifications.py` | GET /notifications (paginated, current user), GET /notifications/unread-count → {count: int}, PATCH /notifications/{id}/read → 200 with updated notification. 404 if wrong user. |
| `backend/app/api/v1/supervisor.py` | GET /supervisor/leads/queue (admin+supervisor only, skip/limit), PATCH /supervisor/leads/{id}/assign (admin+supervisor only) → publishes LEAD_ASSIGNED after commit. |
| `backend/app/api/v1/webhooks.py` | POST /webhooks/voicehire/{organization_id} — no auth, validated by X-VoiceHire-Secret header against settings.VOICEHIRE_WEBHOOK_SECRET. 401 if missing or wrong. |
| `backend/app/core/config.py` | Added VOICEHIRE_WEBHOOK_SECRET field (default: 'change-me-in-production'). |
| `backend/app/api/v1/router.py` | Added notifications, supervisor, webhooks routers. |

#### Tests
| File | Description |
|---|---|
| `backend/tests/test_notifications.py` | 7 tests: create+list, unread count, mark as read, wrong user (404), paginated, isolated by user, unread count excludes read. |
| `backend/tests/test_supervisor.py` | 6 tests: empty queue, shows qualified unassigned, excludes assigned, excludes non-qualified, assign success, agent forbidden (403). |
| `backend/tests/test_webhooks.py` | 6 tests: updates status, merges voicehire_data, creates activity, wrong secret (401), lead not found (404), qualified event triggers supervisor notification. |

---

### Architecture decisions

**Webhook authentication via shared secret**
VoiceHire webhooks bypass JWT auth — they come from an external system. Authentication uses a shared secret in the `X-VoiceHire-Secret` header validated against `settings.VOICEHIRE_WEBHOOK_SECRET`. The endpoint is scoped by `organization_id` in the URL so each org can receive its own events.

**voicehire_data merge strategy**
When a webhook arrives with new voicehire_data, it is merged (dict.update) into the existing field rather than replaced. This preserves data from previous calls and accumulates signal across multiple interactions.

**FIFO supervisor queue**
`list_qualified_unassigned` orders by `created_at ASC`. Oldest qualified leads appear first — supervisors work the queue in order of arrival, not recency.

**Event handlers are self-contained**
Each worker event handler opens its own AsyncSession and commits independently. Exceptions are caught and logged without crashing the worker loop — a failed notification does not block other handlers.

---

### Bugs found and resolved

| Bug | Root cause | Fix |
|---|---|---|
| `column events.updated_at does not exist` | Migration 0001 created the events table without updated_at; the ORM inherits it from Base. On a fresh install alembic applies all migrations in order so the schema matches, but an existing DB (created before 0001 was fixed) was missing the column. | Added updated_at to migration 0001 definition for fresh installs. Added `ALTER TABLE events ADD COLUMN IF NOT EXISTS updated_at` to migration 0004 for existing installs. Applied manually to the current dev DB. |
| `drop_all fails at teardown: cannot drop table pipelines` | `fk_organizations_pipeline_id` is a migration-only FK constraint not reflected in the ORM metadata. `Base.metadata.drop_all` doesn't know about it and can't order the drops correctly. | Added `ALTER TABLE organizations DROP CONSTRAINT IF EXISTS fk_organizations_pipeline_id` in the conftest teardown before `drop_all`. |
| `BoundLogger.info() got multiple values for argument 'event'` | `event=` is structlog's reserved positional argument (the log message key). Passing `event=payload.event` as a keyword arg in webhook_service.py conflicts with it. | Renamed the kwarg to `voicehire_event=payload.event` in the structlog call. |

---

### Final state
```
76 passed in 167.61s (0:02:47)
```

Git: `9d8cee3` — pushed to origin/main.

---

### What comes next — Phase 1E

- User management endpoints (admin can CRUD users in their org)
- Reports: conversion funnel, agent performance, activity by campaign
- Update architecture doc to reflect actual phases built vs original plan
- Backend complete → ready for frontend (Next.js)

---

## Session 5 — Phase 1E: User management, reports, backend complete

**Date:** 2026-03-28
**Commit:** 8ef8a16

### What was built

**Phase 1E — User Management & Reports (17 new tests, 93/93 total)**

New files:
- `backend/app/schemas/user.py` — added `UserCreate`, `UserUpdate`, `UserRead` schemas
- `backend/app/services/user_service.py` — `create_user`, `list_users`, `get_user`, `update_user`, `deactivate_user`
- `backend/app/api/v1/users.py` — 5 endpoints: `GET /users`, `GET /users/{id}`, `POST /users`, `PATCH /users/{id}`, `DELETE /users/{id}`
- `backend/app/services/report_service.py` — `lead_funnel`, `agent_performance`, `activity_by_campaign`
- `backend/app/api/v1/reports.py` — 3 endpoints: `GET /reports/funnel`, `GET /reports/agent-performance`, `GET /reports/activity-by-campaign`
- `backend/tests/test_users.py` — 9 tests
- `backend/tests/test_reports.py` — 8 tests

Modified:
- `backend/app/api/v1/router.py` — added `users` and `reports` routers

### Decisions

| Decision | Rationale |
|---|---|
| `DELETE /users/{id}` does soft-delete (sets `is_active=False`), not hard delete | Preserves audit history; consistent with `deactivate_user` service pattern |
| Reports scoped to admin + supervisor roles | Agents should not see aggregate performance data of peers |
| `activity_by_campaign` counts leads per `campaign_id` | Activities don't have a direct `campaign_id`; leads are the campaign-attributed entity |
| Agent performance uses two separate queries (activities + converted leads) | Cleaner than a complex JOIN; both queries are simple and fast |

### Final state
```
93 passed in 97.62s (0:01:37)
```

Git: `8ef8a16` — pushed to origin/main.

---

### What comes next — Frontend (Next.js)

Backend is complete. All 93 tests pass across all phases (1A–1E).

---

## Session 5 — Phase 2A: Frontend Setup, Login, Dashboard Layout

**Date:** 2026-03-28
**Phase:** 2A
**Status:** Complete — 93/93 backend tests passing, frontend running on port 3000

---

### What was built

#### Project setup
| File | Description |
|---|---|
| `frontend/` | Next.js 14 (App Router), TypeScript, Tailwind CSS, ESLint. |
| `frontend/Dockerfile` | Multi-stage: base → deps → development/production. Hot reload in dev on port 3000. |
| `docker-compose.yml` | Added frontend service on port 3000. Depends on backend. Volume mounts for hot reload. |

#### Core libraries
| File | Description |
|---|---|
| `frontend/lib/api.ts` | Axios instance with `withCredentials: true` and 401→redirect interceptor. |
| `frontend/lib/types.ts` | TypeScript interfaces mirroring backend schemas: User, Organization, Lead, Contact, Deal, Notification, ApiError. |
| `frontend/lib/query-client.ts` | TanStack Query client — 1min stale, retry 1, no refetch on focus. |
| `frontend/lib/utils.ts` | `cn()` helper (clsx + tailwind-merge). |

#### Hooks
| File | Description |
|---|---|
| `frontend/hooks/useAuth.ts` | `useMe` (GET /auth/me), `useLogin` (POST /auth/login → redirect dashboard), `useLogout` (POST /auth/logout → redirect login). |
| `frontend/hooks/useNotifications.ts` | `useNotifications` (poll 30s), `useUnreadCount` (poll 30s), `useMarkAsRead`. |

#### Components
| File | Description |
|---|---|
| `frontend/components/ui/Spinner.tsx` | SVG spinner with size prop. |
| `frontend/components/ui/Badge.tsx` | Color-mapped badge for roles and statuses. |
| `frontend/components/ui/Card.tsx` | White card with shadow, accepts className. |
| `frontend/components/layout/Sidebar.tsx` | Fixed 240px sidebar. Nav links with active state (usePathname). Role-gated Settings link (admin only). User info + logout button at bottom. |
| `frontend/components/layout/NotificationPanel.tsx` | Bell icon with unread badge. Dropdown with last 10 notifications. Mark-as-read button. High-priority notifications with orange left border. |

#### Pages
| File | Description |
|---|---|
| `frontend/app/layout.tsx` | Root layout wrapped in QueryClientProvider + ReactQueryDevtools. |
| `frontend/app/page.tsx` | Root redirect: authenticated → /dashboard, unauthenticated → /login. |
| `frontend/app/login/page.tsx` | Login form (react-hook-form + zod). Email + password validation. Loading state on submit. Server error display. Already-logged-in redirect. |
| `frontend/app/dashboard/layout.tsx` | Protected route shell. useMe → spinner while loading, redirect on 401. Sidebar + NotificationPanel + main content area. |
| `frontend/app/dashboard/page.tsx` | Dashboard home with 4 stat cards (Total Leads, Leads Calificados, Contactos, Deals Activos) fetched from /reports/funnel. Loading skeletons. |

---

### Architecture decisions

**withCredentials on all requests**
The backend sets httpOnly cookies. `axios` does not send cookies cross-origin by default. `withCredentials: true` on the Axios instance ensures cookies are sent on every request without needing to pass tokens manually.

**401 interceptor**
Any 401 response triggers a client-side redirect to /login and clears stale UI. This handles token expiration transparently without per-component error handling.

**Polling over WebSocket for notifications**
Notifications poll every 30s via `refetchInterval`. This matches the architecture decision in v2.0 doc — WebSocket comes in Phase 3C. 30s is imperceptible for notifications.

**QueryClientProvider in root layout**
The QueryClient is instantiated in a separate `lib/query-client.ts` to avoid re-creation on re-renders, then provided at the root layout level so all pages share the same cache.

---

### Final state
```
93 backend tests passing
5 Docker services running: db:5433, redis:6380, backend:8000, worker, frontend:3000
```

Git: `878201a` — pushed to origin/main.

---

### What comes next — Phase 2B

- Leads list page: table with filters (status, source, search), pagination
- Supervisor queue page: `/dashboard/leads/queue` — leads calificados sin asignar, assign modal
- Lead detail page: info + activity timeline + convert button
- Lead create/edit form

---

## Session 6 — Phase 2B: Leads List, Detail, Supervisor Queue

**Date:** 2026-03-28
**Phase:** 2B
**Status:** Complete — 93/93 backend tests passing, frontend running on port 3000

---

### What was built

#### Hooks
| File | Description |
|---|---|
| `frontend/hooks/useLeads.ts` | useLeads (with status/skip/limit params), useLead, useCreateLead, useUpdateLead, useDeleteLead, useConvertLead. |
| `frontend/hooks/useSupervisor.ts` | useLeadsQueue (30s auto-refresh), useAssignLead. |
| `frontend/hooks/useUsers.ts` | useUsers with optional role filter (?role=agent for assign modal). |
| `frontend/hooks/usePipelines.ts` | usePipelines, useStages (depends on pipeline_id — cascade select). |

#### UI components
| File | Description |
|---|---|
| `frontend/components/ui/Modal.tsx` | Generic modal — backdrop + Escape key close, accessible. |
| `frontend/components/ui/Toast.tsx` + `ToastProvider` | Context-based toast system — auto-dismiss 3s, stacked, bottom-right. success/error variants. |
| `frontend/components/ui/Select.tsx` | Styled select wrapper (Tailwind). |
| `frontend/components/ui/Table.tsx` | Generic table with typed column definitions, loading skeleton rows, empty state slot. |

#### Pages
| File | Description |
|---|---|
| `frontend/app/dashboard/leads/page.tsx` | Leads table with client-side search (name/email/phone) + status/source dropdowns. "Nuevo Lead" button (hidden for viewer). Pagination with skip/limit. |
| `frontend/app/dashboard/leads/[id]/page.tsx` | Two-column detail: info card + collapsible voicehire_data viewer + activity placeholder. Actions panel: Convert / Assign / status change / Delete. Role-gated buttons. |
| `frontend/app/dashboard/leads/queue/page.tsx` | Supervisor/admin only — role check on mount, redirect if agent/viewer. Auto-refreshing queue table. Inline Assign button per row. Empty state with checkmark illustration. |

#### Lead modals
| File | Description |
|---|---|
| `frontend/components/leads/LeadFormModal.tsx` | Shared create/edit modal — react-hook-form + zod, first_name/last_name required, email optional with format validation. |
| `frontend/components/leads/AssignLeadModal.tsx` | Agent selector from /api/v1/users?role=agent. On success: invalidate queue + leads queries, show toast. |
| `frontend/components/leads/ConvertLeadModal.tsx` | assigned_to selector + optional deal creation (pipeline → stage cascade). On success: redirect to /dashboard/contacts/{contact_id}. |

#### Sidebar update
| File | Description |
|---|---|
| `frontend/components/layout/Sidebar.tsx` | Added "Cola de Asignación" sub-item under Leads with live queue count badge. Visible to admin/supervisor only. |

#### lib updates
| File | Description |
|---|---|
| `frontend/lib/types.ts` | Added voicehire_data field to Lead interface (caught by TypeScript production build check). |
| `frontend/lib/utils.ts` | Added relativeTime() using Intl.RelativeTimeFormat with 'es' locale. Added statusColor() mapping status strings to Tailwind classes. |

---

### Architecture decisions

**Client-side search over server-side**
The leads list fetches 50 records and filters client-side. For the expected volume (100–1000 leads/day), 50 per page is enough. Server-side search can be added later if needed without changing the component API.

**ToastProvider via React context**
Toast is injected at the dashboard layout level so any child page can call `useToast()` without prop drilling. This pattern will be reused for all future pages.

**Pipeline → Stage cascade**
In ConvertLeadModal, the stages query is enabled only when a pipeline_id is selected (`enabled: !!pipelineId`). This avoids a wasted API call and keeps the UX clean — stage select is disabled until pipeline is chosen.

**Role check on queue page**
The supervisor queue page checks `user.role` on the client after `useMe` resolves. If agent or viewer, it redirects to `/dashboard/leads`. This is a UX guard — the real permission enforcement is on the backend (403 from the API).

---

### Bugs found and resolved

| Bug | Root cause | Fix |
|---|---|---|
| TypeScript build error on Lead type | `voicehire_data` field was missing from the Lead interface in `lib/types.ts`. The TypeScript production build caught it before commit. | Added `voicehire_data: Record<string, unknown>` to the Lead interface. |

---

### Final state
```
93 backend tests passing
5 Docker services running
Frontend: /dashboard/leads, /dashboard/leads/[id], /dashboard/leads/queue — all functional
```

Git: `3acced3` — pushed to origin/main.

---

### What comes next — Phase 2C

- Contacts list page: table with search + status filter
- Contact detail page: info card + lead origin link + activity placeholder
- Contact create/edit modal
- Quick actions: change status, assign to user

---

## Session 7 — Phase 2C: Contacts List, Detail, Create/Edit

**Date:** 2026-03-28
**Phase:** 2C
**Status:** Complete — 93/93 backend tests passing, TypeScript build clean (9 routes, 0 errors)

---

### What was built

#### Hooks
| File | Description |
|---|---|
| `frontend/hooks/useContacts.ts` | useContacts (status/skip/limit params), useContact, useCreateContact, useUpdateContact, useDeleteContact. queryKey: ['contacts', params] / ['contacts', id]. |

#### Pages
| File | Description |
|---|---|
| `frontend/app/dashboard/contacts/page.tsx` | Contacts table with client-side search (name/email/company) + status filter. "Nuevo Contacto" button (hidden for viewer). Loading skeletons + empty state. |
| `frontend/app/dashboard/contacts/[id]/page.tsx` | Two-column detail: info card (name, status badge, email, phone, company, position, country) + inline tag editor (pills + Enter to add) + lead origin card (link to /dashboard/leads/{lead_id} if lead_id set) + activity placeholder. Right column: edit button, status dropdown, assign dropdown, delete with confirm dialog (admin/supervisor only) → redirect to /dashboard/contacts on delete. |

#### Modals
| File | Description |
|---|---|
| `frontend/components/contacts/ContactFormModal.tsx` | Create/edit modal — react-hook-form + zod. Fields: first_name* (required), last_name* (required), email (optional, validated), phone, company, position, country, status (edit only, default 'active' on create), assigned_to. Same pattern as LeadFormModal. |

---

### Architecture decisions

**Tags as inline edit**
Tags render as colored pills on the detail page. Adding a tag uses an inline input (press Enter) that calls useUpdateContact with the updated tags array. No separate endpoint — the existing PATCH /contacts/{id} handles the full update.

**Lead origin card**
If `contact.lead_id` is set, the detail page renders a card pointing to `/dashboard/leads/{lead_id}`. This closes the loop between the conversion flow and the UI — a user can always trace a contact back to its VoiceHire lead origin.

**Delete with window.confirm**
The delete button calls `window.confirm()` before executing `useDeleteContact`. MVP-appropriate — no need for a custom confirm modal at this stage. On confirmation, deletes and redirects to `/dashboard/contacts`.

---

### Bugs found and resolved

None — TypeScript build clean, no runtime errors encountered.

---

### Final state
```
93 backend tests passing
TypeScript build: 9 routes, 0 errors
5 Docker services running
Frontend routes: /dashboard/contacts, /dashboard/contacts/[id] — functional
```

Git: `01add3a` — pushed to origin/main.

---

### What comes next — Phase 2D

- Deals kanban board: columns = pipeline stages, cards = deals
- Drag-and-drop (HTML5 API, no external library) to move deals between stages
- Deal detail drawer (slide-in panel, 480px, auto-save on blur)
- Deal create modal (from kanban columns and from contact detail page)
- Contact detail page: add Deals section showing deals linked to the contact
