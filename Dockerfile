#------ Step 1: Builder -----------
FROM python:3.14-slim AS builder

WORKDIR /app

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv
COPY pyproject.toml uv.lock README.md ./
RUN uv sync --frozen --no-dev --no-install-project

COPY src ./src
COPY alembic ./alembic
COPY alembic.ini ./
RUN uv sync --frozen --no-dev

#------ Step 2: Runtime -----------
FROM python:3.14-slim AS runtime

WORKDIR /app

COPY --from=builder /app/.venv ./.venv
COPY --from=builder /app/src ./src
COPY --from=builder /app/alembic ./alembic
COPY --from=builder /app/alembic.ini ./

ENV PATH="/app/.venv/bin:$PATH"

CMD ["sh", "-c", "uvicorn progress_fitness_api.main:app --host 0.0.0.0 --port ${PORT:-8000}"]