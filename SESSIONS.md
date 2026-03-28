# Vortem — Session Summaries

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
