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
