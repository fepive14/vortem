# Vortem CRM — Backend

On-premise CRM designed for organizations with dedicated IT teams and technical investors.

## Prerequisites

- Docker 24+ and Docker Compose v2
- `openssl` (for key generation)

## Quick start (3 commands)

```bash
# 1. Copy and fill environment variables
cp .env.example .env
# Open .env and set a proper SECRET_KEY:
#   openssl rand -hex 32

# 2. Start all services
docker compose up -d

# 3. Run database migrations
docker compose exec backend alembic upgrade head
```

The API is now available at **http://localhost:8000**.

Bootstrap the instance (creates the first organization and admin user):

```bash
curl -X POST http://localhost:8000/api/v1/setup \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@example.com","password":"secret","full_name":"Admin","org_name":"Acme"}'
```

Interactive API docs: **http://localhost:8000/docs**

---

## Development

### Run tests

```bash
# Inside the running backend container
docker compose exec backend pytest -v

# Or directly if you have a local Python environment
cd backend && pytest -v
```

### Apply a new migration

```bash
# Auto-generate from model changes
docker compose exec backend alembic revision --autogenerate -m "describe_change"

# Apply
docker compose exec backend alembic upgrade head
```

### View structured logs

```bash
docker compose logs -f backend worker
```

---

## Architecture decisions

| Concern | Choice | Reason |
|---|---|---|
| Async ORM | SQLAlchemy 2 + asyncpg | First-class async, type-safe, battle-tested |
| Auth tokens | JWT (httpOnly cookies) | Stateless, XSS-resistant, works with SSR frontends |
| Password hashing | bcrypt cost=12 | Industry standard, adjustable cost |
| Event bus | PostgreSQL LISTEN/NOTIFY | Zero extra infra for on-premise deployments |
| Structured logging | structlog | JSON in production, readable in dev |
| Config | pydantic-settings | Validated at startup, IDE-friendly |

---

## Services

| Service | Port | Description |
|---|---|---|
| `backend` | 8000 | FastAPI application (hot-reload in dev) |
| `worker` | — | Event bus consumer |
| `db` | 5433 | PostgreSQL 16 (host port) |
| `redis` | 6380 | Redis 7 (host port) |

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
