"""CLI entry: uv run foodease-session"""

from __future__ import annotations

import logging
import sys

import uvicorn

from foodease_session.config import ConfigError, load_settings


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    try:
        settings = load_settings()
    except ConfigError as exc:
        print(f"config error: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc

    # Import after settings validated so missing env fails before bind
    from foodease_session.app import create_app

    app = create_app(settings)
    print(f"foodease-session listening on http://{settings.host}:{settings.port}")
    print(f"OpenAPI docs: http://{settings.host}:{settings.port}/docs")
    uvicorn.run(app, host=settings.host, port=settings.port, log_level="info")


if __name__ == "__main__":
    main()
