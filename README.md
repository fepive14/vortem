# Vortem CRM

On-premise CRM with integrated VoiceHire candidate pipeline. Designed for organizations with dedicated IT teams and technical investors. Self-hosted — no data leaves your server.

---

## Stack

| Layer | Technology |
|---|---|
| API | FastAPI (Python 3.12, async) |
| Database | PostgreSQL 16 |
| Cache / Pub-Sub | Redis 7 |
| Frontend | Next.js 14 (App Router) |
| Data fetching | TanStack Query v5 |
| Styling | Tailwind CSS v3 |
| Forms / Validation | react-hook-form + zod |

---

## Services

| Service | Host port | Description |
|---|---|---|
| `backend` | 8000 | FastAPI application (hot-reload in dev) |
| `worker` | — | Event bus consumer (PostgreSQL LISTEN/NOTIFY) |
| `db` | 5433 | PostgreSQL 16 |
| `redis` | 6380 | Redis 7 |
| `frontend` | 3000 | Next.js application (hot-reload in dev) |

---

## Quick Start

```bash
# 1. Copy and fill environment variables
cp .env.example .env
# Required: SECRET_KEY — generate with: openssl rand -hex 32
# Required: VOICEHIRE_WEBHOOK_SECRET — agree with VoiceHire team
# Required: NEXT_PUBLIC_API_URL — e.g. http://localhost:8000

# 2. Start all services
docker compose up -d

# 3. Run database migrations
docker compose exec backend alembic upgrade head

# 4. Bootstrap: creates first organization + admin user (run once only)
curl -X POST http://localhost:8000/api/v1/setup \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@example.com","password":"secret","full_name":"Admin","org_name":"Acme"}'
```

- API: **http://localhost:8000**
- API docs: **http://localhost:8000/docs**
- Frontend: **http://localhost:3000**

> The `/setup` endpoint returns `403` after the first successful call — it is safe to call again and will not overwrite existing data.

---

## Frontend Routes

| Route | Description | Role access |
|---|---|---|
| `/login` | Login page | Public |
| `/` | Dashboard — KPI cards + activity feed | All authenticated |
| `/contacts` | Contact list with search and filters | All authenticated |
| `/contacts/[id]` | Contact detail + interaction timeline | All authenticated |
| `/companies` | Company list | All authenticated |
| `/companies/[id]` | Company detail | All authenticated |
| `/deals` | Deals kanban (drag-and-drop by stage) | All authenticated |
| `/deals/[id]` | Deal drawer / detail | All authenticated |
| `/candidates` | VoiceHire candidate pipeline | All authenticated |
| `/candidates/[id]` | Candidate detail + interview results | All authenticated |
| `/reports` | Revenue and pipeline reports | Admin, Manager |
| `/settings` | Organization and user settings | Admin |

---

## Backend API — Key Endpoints

| Method | Path | Description |
|---|---|---|
| `POST` | `/api/v1/setup` | Bootstrap organization + admin (once only) |
| `POST` | `/api/v1/auth/login` | Obtain JWT (sets httpOnly cookie) |
| `POST` | `/api/v1/auth/logout` | Invalidate session |
| `GET` | `/api/v1/contacts` | List contacts (paginated, filterable) |
| `POST` | `/api/v1/contacts` | Create contact |
| `GET/PATCH/DELETE` | `/api/v1/contacts/{id}` | Contact CRUD |
| `GET` | `/api/v1/companies` | List companies |
| `POST` | `/api/v1/companies` | Create company |
| `GET` | `/api/v1/deals` | List deals |
| `POST` | `/api/v1/deals` | Create deal |
| `PATCH` | `/api/v1/deals/{id}/stage` | Move deal stage |
| `GET` | `/api/v1/candidates` | List VoiceHire candidates |
| `POST` | `/api/v1/webhooks/voicehire/{org_id}` | VoiceHire webhook receiver |
| `GET` | `/api/v1/reports/revenue` | Revenue report data |
| `GET` | `/api/v1/dashboard` | KPI summary for dashboard |

Full interactive docs at **http://localhost:8000/docs**.

---

## Development

### Run tests

```bash
# Always run the full suite — never individual files
# The create_tables fixture is session-scoped; running a single file
# skips it and produces false failures.
docker compose exec backend pytest -v

# Local Python environment
cd backend && pytest -v
```

> **Warning:** Do not run `pytest path/to/test_file.py` directly. Always run the full suite via `pytest -v` (or `pytest -v -k <pattern>` at most). The `create_tables` fixture is session-scoped and only runs when the full suite starts.

### Apply a migration

```bash
# Generate from model changes
docker compose exec backend alembic revision --autogenerate -m "describe_change"

# Apply (idempotent — safe to run multiple times)
docker compose exec backend alembic upgrade head
```

### View logs

```bash
docker compose logs -f backend worker
docker compose logs -f frontend
```

---

## Architecture Decisions

| Concern | Choice | Reason |
|---|---|---|
| Async ORM | SQLAlchemy 2 + asyncpg | First-class async, type-safe, battle-tested |
| Auth tokens | JWT (httpOnly cookies) | Stateless, XSS-resistant, works with SSR frontends |
| Password hashing | bcrypt cost=12 | Industry standard, adjustable cost |
| Event bus | PostgreSQL LISTEN/NOTIFY | Zero extra infra for on-premise deployments |
| Structured logging | structlog | JSON in production, readable in dev |
| Config | pydantic-settings | Validated at startup, IDE-friendly |
| Frontend data fetching | TanStack Query v5 | Declarative cache, stale-while-revalidate, background refetch |
| Frontend forms | react-hook-form + zod | Uncontrolled inputs (perf), schema-validated at submit |
| Drag-and-drop | HTML5 Drag API | Zero extra dependency; sufficient for kanban use case |
| Real-time updates | 30 s polling (TanStack Query) | Simpler than WebSockets; acceptable latency for CRM |

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

## Related Repositories

- [VoiceHire](https://github.com/voicehire/voicehire) — interview automation platform that feeds candidates into this CRM via webhook
