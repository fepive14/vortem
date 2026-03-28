# ─── Base ─────────────────────────────────────────────────────────────────────
FROM python:3.12-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# System deps required by psycopg/asyncpg native extensions
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
 && rm -rf /var/lib/apt/lists/*

# ─── Dependencies ─────────────────────────────────────────────────────────────
FROM base AS deps

COPY pyproject.toml .
RUN pip install --upgrade pip && pip install .

# ─── Development ──────────────────────────────────────────────────────────────
FROM deps AS development

# Install dev/test extras
RUN pip install ".[dev]"

# Source is mounted as a volume in docker-compose; no COPY needed.
ENV PYTHONPATH=/app

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

# ─── Production ───────────────────────────────────────────────────────────────
FROM deps AS production

COPY . .
ENV PYTHONPATH=/app

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
