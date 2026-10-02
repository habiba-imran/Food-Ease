"""Phase 0 verification helpers — no provider calls; does not read .env secrets for display."""

from __future__ import annotations

from foodease_agent.config import REQUIRED_ENV_VARS, ConfigError, load_config


def check_v03_missing_var() -> None:
    env = {name: "x" for name in REQUIRED_ENV_VARS}
    env["IDLE_PROMPT_1_SECONDS"] = "8"
    env["IDLE_PROMPT_2_SECONDS"] = "20"
    env["RECORD_AUDIO"] = "false"
    env["DEV_MODE"] = "false"
    del env["CARTESIA_API_KEY"]
    try:
        load_config(environ=env)
    except ConfigError as exc:
        message = str(exc)
        if "CARTESIA_API_KEY" not in message:
            raise SystemExit(f"V0.3 FAIL: error did not name var: {message}") from exc
        print(f"V0.3 PASS: {message}")
        return
    raise SystemExit("V0.3 FAIL: expected ConfigError")


if __name__ == "__main__":
    check_v03_missing_var()
