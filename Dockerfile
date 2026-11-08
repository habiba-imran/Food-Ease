# syntax=docker/dockerfile:1
FROM python:3.12-slim-bookworm
COPY --from=ghcr.io/astral-sh/uv:0.10.6 /uv /uvx /bin/
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy UV_CACHE_DIR=/tmp/uv-cache \
    PATH=/app/voice-agent/.venv/bin:$PATH \
    HF_HOME=/app/.cache/huggingface \
    TIKTOKEN_CACHE_DIR=/app/.cache/tiktoken \
    FOODEASE_APP_TRANSPORT=website FOODEASE_AGENT_NAME=foodease \
    FOODEASE_CLOUD_RUNTIME=1 \
    RECORD_AUDIO=false DEV_MODE=false PREEMPTIVE_GENERATION=false
RUN useradd --create-home --uid 10001 agent && mkdir -p /app/.cache && chown -R agent:agent /app
WORKDIR /app
COPY --chown=agent:agent contracts/pyproject.toml contracts/README.md ./contracts/
COPY --chown=agent:agent website/pyproject.toml website/README.md ./website/
COPY --chown=agent:agent voice-agent/pyproject.toml voice-agent/uv.lock voice-agent/README.md ./voice-agent/
USER agent
WORKDIR /app/voice-agent
RUN uv sync --locked --no-dev --no-install-project --no-install-package foodease-contract
COPY --chown=agent:agent contracts/src /app/contracts/src
COPY --chown=agent:agent voice-agent/src /app/voice-agent/src
RUN uv sync --locked --no-dev --no-editable \
    && python -c "import tiktoken; tiktoken.get_encoding('o200k_base')" \
    && python -m livekit.agents download-files
EXPOSE 8081
HEALTHCHECK --interval=30s --timeout=5s --start-period=120s \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8081/', timeout=4)" || exit 1
CMD ["python", "-m", "foodease_agent.worker", "start"]
