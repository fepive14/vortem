# Vortem CRM — Deployment Guide

Production installation on a client server (Ubuntu 22.04).

---

## Prerequisites

| Requirement | Minimum |
|---|---|
| OS | Ubuntu 22.04 LTS |
| Docker | 24+ |
| Docker Compose | v2 (bundled with Docker Desktop or `docker compose` plugin) |
| git | any recent version |
| openssl | any recent version (for key generation) |
| CPU | 2 vCPU |
| RAM | 4 GB |
| Disk | 20 GB |

---

## Step 1 — Clone the repository

```bash
git clone <repo-url> vortem
cd vortem
```

---

## Step 2 — Configure environment variables

```bash
cp .env.example .env
```

Open `.env` and fill in the required variables:

| Variable | How to generate / where to find |
|---|---|
| `SECRET_KEY` | `openssl rand -hex 32` |
| `POSTGRES_PASSWORD` | Any strong password (only used internally between containers) |
| `VOICEHIRE_WEBHOOK_SECRET` | Agreed with the VoiceHire team — must match what they send in `X-VoiceHire-Secret` |
| `NEXT_PUBLIC_API_URL` | `http://<server-ip>:8000` or `https://<domain>:8000` if TLS is terminated upstream |

All other variables have working defaults in `.env.example` and typically do not need to be changed.

---

## Step 3 — Start all services

```bash
docker compose up -d
```

Verify all containers are healthy:

```bash
docker compose ps
```

Expected output — all services should show `running` or `healthy`:

```
NAME           STATUS
vortem-backend   running
vortem-worker    running
vortem-db        running (healthy)
vortem-redis     running (healthy)
vortem-frontend  running
```

---

## Step 4 — Run database migrations

```bash
docker compose exec backend alembic upgrade head
```

This command is **idempotent** — it is safe to run multiple times. It applies only unapplied migrations and skips ones already applied.

> **Important:** Docker does not apply migrations automatically on startup. This step must be completed before running `create_admin` (Step 5b) or any other CLI tool that accesses the database. On a brand-new environment, skipping this step causes `relation 'users' does not exist` errors.

---

## Step 5 — Bootstrap the instance

Run **once** to create the first organization and admin user:

```bash
curl -X POST http://<server-ip>:8000/api/v1/setup \
  -H "Content-Type: application/json" \
  -d '{
    "email": "admin@yourcompany.com",
    "password": "change-me-immediately",
    "full_name": "Administrator",
    "org_name": "Your Organization"
  }'
```

> The `/setup` endpoint returns `403 Forbidden` after the first successful call. This is expected — it cannot be used to overwrite the existing organization.

Change the admin password immediately after first login.

---

## Step 5b — Create organization admin user

> **Requires Step 4 (migrations) to be completed first.** Docker does not run migrations
> automatically on startup — skipping Step 4 on a fresh environment causes
> `relation 'users' does not exist`.

Run the interactive CLI bootstrap tool:

```bash
docker compose exec -it backend python -m app.cli.create_admin
```

The tool prompts for four values (password input is hidden):

```
=== Vortem CRM — Create Org Admin ===

Email: admin@yourcompany.com
Full name: Administrator
Organization name: Your Organization
Password (min 8 chars):
```

It hashes the password internally — no SQL, no raw bcrypt hashes. If an organization was
already created by Step 5, the tool reuses it automatically; no duplicates are created.

If you skipped Step 5, the tool creates the organization and admin user in a single step —
making Step 5 optional for new installations.

> **Protection:** The tool refuses to run if an org-scoped admin already exists, preventing
> accidental duplicate accounts.

---

## Step 6 — Verify the installation

| Check | URL |
|---|---|
| Frontend (login page) | `http://<server-ip>:3000` |
| API health | `http://<server-ip>:8000/health` |
| Interactive API docs | `http://<server-ip>:8000/docs` |

Log in with the credentials used in Step 5.

---

## Step 7 — Configure VoiceHire webhook

In the VoiceHire admin panel, set the webhook URL to:

```
http://<server-ip>:8000/api/v1/webhooks/voicehire/<organization_id>
```

Where `<organization_id>` is the UUID of the organization created in Step 5 (visible in **Settings → Organization** inside the CRM).

Set the secret header:

| Header | Value |
|---|---|
| `X-VoiceHire-Secret` | The value of `VOICEHIRE_WEBHOOK_SECRET` from your `.env` |

---

## Updating

```bash
# Pull latest code
git pull

# Rebuild and restart containers
docker compose down
docker compose up -d --build

# Apply any new migrations
docker compose exec backend alembic upgrade head
```

> Downtime during `docker compose down` / `up` is typically under 30 seconds.

---

## Useful Commands

```bash
# Follow logs for all services
docker compose logs -f

# Follow logs for a specific service
docker compose logs -f backend
docker compose logs -f frontend
docker compose logs -f worker

# Restart a single service without downtime for others
docker compose restart backend

# Stop all services (data is preserved)
docker compose down

# Stop all services and DELETE all data (volumes)
# WARNING: this is irreversible — all database data will be lost
docker compose down -v

# Open a psql session
docker compose exec db psql -U postgres -d vortem
```

---

## Troubleshooting

### Frontend shows a blank page

1. Check that `NEXT_PUBLIC_API_URL` in `.env` matches the server's actual IP or domain.
2. Verify the backend is reachable: `curl http://<server-ip>:8000/health`
3. Check frontend logs: `docker compose logs frontend`

### Backend returns 500 on all requests

1. Check backend logs: `docker compose logs backend`
2. Confirm migrations have been applied: `docker compose exec backend alembic current`
3. Confirm the database container is healthy: `docker compose ps db`

### Migration fails

1. Check for unapplied conflicts: `docker compose exec backend alembic history`
2. Ensure the database container is running and healthy before retrying.
3. Never edit migration files that have already been applied in production.

### Cannot connect to database

1. Confirm the `db` container is healthy: `docker compose ps`
2. Check that `POSTGRES_PASSWORD` in `.env` matches the value used when the volume was first created. If they differ, you must destroy the volume (`docker compose down -v`) and start over — **this deletes all data**.
