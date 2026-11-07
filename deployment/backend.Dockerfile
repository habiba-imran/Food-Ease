# syntax=docker/dockerfile:1
FROM python:3.12-slim-bookworm
COPY --from=ghcr.io/astral-sh/uv:0.10.6 /uv /uvx /bin/
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy PATH=/app/orchestration/.venv/bin:$PATH \
    ENABLE_MOCK_AGENT=false FOODEASE_LEGACY_DEV_API=false
RUN useradd --create-home --uid 10001 backend && mkdir -p /app && chown backend:backend /app
WORKDIR /app
COPY --chown=backend:backend contracts ./contracts
COPY --chown=backend:backend website/pyproject.toml website/README.md ./website/
COPY --chown=backend:backend website/src ./website/src
COPY --chown=backend:backend website/templates ./website/templates
COPY --chown=backend:backend zainab-pack/catalog-seed.json ./zainab-pack/catalog-seed.json
COPY --chown=backend:backend orchestration/pyproject.toml orchestration/uv.lock orchestration/README.md ./orchestration/
COPY --chown=backend:backend orchestration/src ./orchestration/src
USER backend
RUN mkdir -p website/static && uv sync --project orchestration --locked --no-dev
EXPOSE 10000
CMD ["uvicorn", "foodease_session.production:create_backend", "--factory", "--host", "0.0.0.0", "--port", "10000", "--workers", "1", "--no-access-log"]
