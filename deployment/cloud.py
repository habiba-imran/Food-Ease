"""Run FoodEase-only Cloud CLI operations without exposing credential values.

Credentials enter the child environment, never its arguments. Provider secrets use
a temporary file outside the build context and are deleted after the CLI exits.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import tomllib
from pathlib import Path
from urllib.parse import urlsplit

from dotenv import dotenv_values

ROOT = Path(__file__).resolve().parents[1]


def local_environment() -> dict[str, str]:
    values = dotenv_values(ROOT / "voice-agent/.env")
    return {**os.environ, **{k: v for k, v in values.items() if v is not None}}


def redact(text: str, env: dict[str, str]) -> str:
    for key, value in env.items():
        if value and any(part in key.upper() for part in ("SECRET", "TOKEN", "KEY", "REDIS_URL")):
            text = text.replace(value, "[REDACTED]")
    text = re.sub(r'("worker_proof"\s*:\s*)"[^"]+"', r'\1"[REDACTED]"', text)
    return re.sub(r"\beyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+", "[REDACTED_JWT]", text)


def run_cli(arguments: list[str], env: dict[str, str], *, timeout=1200) -> int:
    target = env["LIVEKIT_URL"]
    # Always select explicit FoodEase credentials; never use the CLI's unrelated default.
    result = subprocess.run(
        ["lk", "--url", target, "--yes", *arguments],
        env=env,
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
        check=False,
    )
    output = redact((result.stdout or "") + (result.stderr or ""), env)
    evidence = ROOT / "deployment/evidence"
    evidence.mkdir(parents=True, exist_ok=True)
    (evidence / ("cloud-" + arguments[1] + ".txt")).write_text(output, encoding="utf-8")
    print(output, flush=True)
    return result.returncode


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "operation",
        choices=(
            "list",
            "create",
            "deploy",
            "status",
            "logs",
            "secrets",
            "configure-backend",
            "check-capacity",
        ),
    )
    parser.add_argument("--backend-url")
    parser.add_argument("--log-type", choices=("deploy", "build"), default="deploy")
    args = parser.parse_args()
    env = local_environment()
    for name in ("LIVEKIT_URL", "LIVEKIT_API_KEY", "LIVEKIT_API_SECRET"):
        if not env.get(name):
            raise SystemExit(f"Missing {name}")
    config = ROOT / "livekit.toml"
    agent_id = None
    if config.exists():
        data = tomllib.loads(config.read_text())
        agent_id = data.get("agent", {}).get("id")
        if (
            data.get("project", {}).get("subdomain")
            != urlsplit(env["LIVEKIT_URL"]).hostname.split(".")[0]
        ):
            raise SystemExit("livekit.toml belongs to another project; refusing deployment")
    if args.operation == "list":
        return run_cli(["agent", "list", "--json"], env)
    if args.operation == "create" and agent_id:
        raise SystemExit(
            "An agent ID is already recorded; use deploy instead of creating a duplicate"
        )
    if args.operation == "create":
        existing = subprocess.run(
            ["lk", "--url", env["LIVEKIT_URL"], "agent", "list", "--json"],
            env=env,
            cwd=ROOT,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=45,
            check=False,
        )
        if existing.returncode:
            print(redact(existing.stderr, env))
            return existing.returncode
        remote = json.loads(existing.stdout)
        if remote.get("agents", []) if isinstance(remote, dict) else remote:
            raise SystemExit(
                "Cloud agents already exist; bind the intended ID before deploying "
                "to prevent duplicates"
            )
    if args.operation not in {"create", "list"} and not agent_id:
        raise SystemExit("No deployed agent ID in livekit.toml")
    if args.operation in {"create", "deploy", "configure-backend", "check-capacity"}:
        from foodease_agent.config import load_config
        from foodease_agent.groq_capacity import CAPACITY_ENV_VARS, cloud_preflight

        settings = load_config(environ={**env, "FOODEASE_CLOUD_RUNTIME": "1"})
        if args.operation in {"create", "deploy", "check-capacity"}:
            if settings.llm_provider == "groq":
                if not settings.groq_capacity.redis_url:
                    raise SystemExit(
                        "Set GROQ_CAPACITY_REDIS_URL (rediss://) before Cloud deployment"
                    )
                try:
                    asyncio.run(cloud_preflight(settings.groq_capacity, settings.llm_model))
                except ValueError as error:
                    raise SystemExit(str(error)) from None
            if args.operation == "check-capacity":
                print(
                    "Two-client Redis conflict/reservation checks passed; no Groq request was sent."
                )
                print("This does not certify provider failover durability or global consistency.")
                return 0
        secrets = {
            name: env[name]
            for name in (
                "GROQ_API_KEY",
                "GROQ_API_KEY_2",
                "GROQ_API_KEY_3",
                "GROQ_API_KEY_4",
                "CARTESIA_API_KEY",
                "DEEPGRAM_API_KEY",
                "GOOGLE_API_KEY",
            )
            if env.get(name)
        }
        secrets.update(
            {
                "ASSISTANT_LANGUAGE": settings.assistant_language,
                "URDU_STT_MODEL": settings.urdu_stt_model,
                "LLM_PROVIDER": settings.llm_provider,
                "GROQ_MODEL": settings.llm_model
                if settings.llm_provider == "groq"
                else env.get("GROQ_MODEL", "openai/gpt-oss-20b"),
                "LLM_MODEL": env.get("LLM_MODEL", "gemini-3.1-flash-lite"),
                "LLM_THINKING_LEVEL": env.get("LLM_THINKING_LEVEL", "minimal"),
                "STT_MODEL": settings.stt_model,
                "TTS_MODEL": settings.tts_model,
                "TTS_VOICE_ID": settings.tts_voice_id,
                "IDLE_PROMPT_1_SECONDS": str(settings.idle_prompt_1_seconds),
                "IDLE_PROMPT_2_SECONDS": str(settings.idle_prompt_2_seconds),
                "RECORD_AUDIO": "false",
                "DEV_MODE": "false",
                "PREEMPTIVE_GENERATION": "false",
                "FOODEASE_APP_TRANSPORT": "website",
                "FOODEASE_AGENT_NAME": "foodease",
            }
        )
        secrets.update({name: env[name] for name in CAPACITY_ENV_VARS
                        if env.get(name) and name != "GROQ_CAPACITY_SQLITE_PATH"})
        if args.operation == "configure-backend":
            # Updating the callback must not overwrite provider keys changed in Cloud.
            secrets.clear()
        if args.backend_url:
            url = urlsplit(args.backend_url)
            if (
                url.scheme != "https"
                or not url.hostname
                or url.username
                or url.password
                or url.query
                or url.fragment
                or url.path not in {"", "/"}
            ):
                raise SystemExit("Backend URL must be a public HTTPS URL without credentials/query")
            secrets["FOODEASE_SESSION_API"] = args.backend_url.rstrip("/") + "/assist"
        if args.operation == "configure-backend" and not args.backend_url:
            raise SystemExit("--backend-url is required")
        with tempfile.TemporaryDirectory(prefix="foodease-cloud-") as temporary:
            secret_file = Path(temporary) / "secrets.env"
            secret_file.write_text(
                "".join(f"{k}={json.dumps(v)}\n" for k, v in secrets.items()),
                encoding="utf-8",
            )
            operation = (
                "update-secrets" if args.operation == "configure-backend" else args.operation
            )
            command = ["agent", operation, "--secrets-file", str(secret_file)]
            if operation == "create":
                command += ["--region", "ap-south"]
            elif agent_id:
                command += ["--id", agent_id]
            if operation == "update-secrets":
                return run_cli(command, env)
            # CLI upload policies expire while walking large Windows checkouts.
            # Stage only image inputs before requesting an upload policy.
            with tempfile.TemporaryDirectory(prefix="foodease-build-") as context:
                stage = Path(context)
                for name in ("Dockerfile", ".dockerignore", "requirements.txt"):
                    shutil.copy2(ROOT / name, stage / name)
                if config.exists():
                    shutil.copy2(config, stage / "livekit.toml")
                for package in ("voice-agent", "contracts", "website"):
                    target = stage / package
                    target.mkdir()
                    for name in ("pyproject.toml", "README.md"):
                        shutil.copy2(ROOT / package / name, target / name)
                    if package == "voice-agent":
                        shutil.copy2(ROOT / package / "uv.lock", target / "uv.lock")
                    if package != "website":
                        shutil.copytree(
                            ROOT / package / "src",
                            target / "src",
                            ignore=shutil.ignore_patterns("__pycache__", "*.pyc", ".env*"),
                        )
                count = sum(1 for path in stage.rglob("*") if path.is_file())
                size = sum(path.stat().st_size for path in stage.rglob("*") if path.is_file())
                print(
                    json.dumps({"build_context_files": count, "build_context_bytes": size}),
                    flush=True,
                )
                return run_cli([*command, str(stage)], env)
    command = ["agent", args.operation, "--id", agent_id]
    if args.operation == "status":
        command += ["--json"]
    if args.operation == "logs":
        command += ["--log-type", args.log_type]
        # Logs stream indefinitely; bound the process and redact before displaying.
        try:
            return run_cli(command, env, timeout=20)
        except subprocess.TimeoutExpired as error:
            output = "".join(
                part.decode(errors="replace") if isinstance(part, bytes) else part or ""
                for part in (error.stdout, error.stderr)
            )
            output = redact(output, env)
            evidence = ROOT / "deployment/evidence/cloud-logs.txt"
            evidence.parent.mkdir(parents=True, exist_ok=True)
            evidence.write_text(output, encoding="utf-8")
            print(output)
            return 0
    return run_cli(command, env)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    raise SystemExit(main())
