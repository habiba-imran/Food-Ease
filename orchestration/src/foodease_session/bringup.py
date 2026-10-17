"""Owned localhost processes for the final website stack; no mock fallback."""

from __future__ import annotations

import math
import os
import signal
import socket
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path

import httpx

PROVIDER_KEYS = (
    "LIVEKIT_URL",
    "LIVEKIT_API_KEY",
    "LIVEKIT_API_SECRET",
    "DEEPGRAM_API_KEY",
    "CARTESIA_API_KEY",
    "GOOGLE_API_KEY",
    "GEMINI_API_KEY",
    "OPENAI_API_KEY",
)


@dataclass(frozen=True)
class Service:
    name: str
    cwd: Path
    command: list[str]
    port: int
    env: dict[str, str]
    offline: bool = False

    def environment(self, inherited: dict[str, str] | None = None) -> dict[str, str]:
        result = dict(os.environ if inherited is None else inherited)
        if self.offline:
            for key in PROVIDER_KEYS:
                result.pop(key, None)
        result.update(self.env)
        return result


@dataclass(frozen=True)
class StackPlan:
    root: Path
    mode: str = "manual"
    website_port: int = 8080
    session_port: int = 8090
    worker_port: int = 8081

    def __post_init__(self):
        ports = (self.website_port, self.session_port, self.worker_port)
        if self.mode not in {"manual", "live"}:
            raise ValueError("Mode must be manual or live")
        if len(set(ports)) != 3 or any(not 1 <= port <= 65535 for port in ports):
            raise ValueError("Choose three distinct ports between 1 and 65535")

    @property
    def website_url(self) -> str:
        return f"http://127.0.0.1:{self.website_port}"

    @property
    def session_url(self) -> str:
        return f"http://127.0.0.1:{self.session_port}"

    def services(self) -> list[Service]:
        base = {
            "RECORD_AUDIO": "false",
            "DEV_MODE": "false",
            "ENABLE_MOCK_AGENT": "false",
            "HOST": "127.0.0.1",
            "FOODEASE_LEGACY_DEV_API": "false",
            "FOODEASE_AGENT_NAME": "foodease",
            "PYTHONUNBUFFERED": "1",
        }
        if self.mode == "manual":
            base.update(
                PYTHON_DOTENV_DISABLED="1",
                LIVEKIT_AGENT_DISPATCH="false",
                FOODEASE_EVIDENCE_KIND="offline",
            )
        else:
            base["LIVEKIT_AGENT_DISPATCH"] = "true"
            base["FOODEASE_EVIDENCE_KIND"] = "live_requested"
            base["PYTHON_DOTENV_DISABLED"] = "0"

        def service(name, package, module, port, extra, args=()):
            cwd = self.root.resolve() / package
            python = cwd / ".venv" / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
            return Service(
                name,
                cwd,
                [str(python), "-m", module, *args],
                port,
                {**base, "PORT": str(port), **extra},
                self.mode == "manual",
            )

        services = [
            service(
                "website",
                "website",
                "foodease_website.main",
                self.website_port,
                {"ORCHESTRATION_BASE_URL": self.session_url},
            )
        ]
        session_env = {"FOODEASE_WEBSITE_URL": self.website_url, "CORS_ORIGINS": self.website_url}
        if self.mode == "live":
            services.append(
                service(
                    "session",
                    "orchestration",
                    "foodease_session.main",
                    self.session_port,
                    session_env,
                )
            )
            services.append(
                service(
                    "worker",
                    "voice-agent",
                    "foodease_agent.worker",
                    self.worker_port,
                    {
                        "FOODEASE_APP_TRANSPORT": "website",
                        "FOODEASE_SESSION_API": self.session_url,
                        "FOODEASE_WORKER_PORT": str(self.worker_port),
                    },
                    ("start", "--log-level", "info", "--drain-timeout", "20"),
                )
            )
        else:
            services.append(
                service(
                    "session",
                    "orchestration",
                    "uvicorn",
                    self.session_port,
                    session_env,
                    (
                        "foodease_session.app:create_app",
                        "--factory",
                        "--host",
                        "127.0.0.1",
                        "--port",
                        str(self.session_port),
                        "--log-level",
                        "warning",
                    ),
                )
            )
        return services


def occupied_ports(ports: list[int]) -> list[int]:
    occupied = []
    for port in ports:
        with socket.socket() as probe:
            try:
                probe.bind(("127.0.0.1", port))
            except OSError:
                occupied.append(port)
    return occupied


def powershell_commands(plan: StackPlan) -> str:
    def quote(value):
        return "'" + str(value).replace("'", "''") + "'"

    lines = [
        f"FoodEase final stack: {plan.mode}",
        "Ownership: docs/OWNERSHIP.md",
        "Each block uses a separate PowerShell terminal; foodease-session is the Session API.",
    ]
    for service in plan.services():
        lines += [f"\n# {service.name}", f"Set-Location -LiteralPath {quote(service.cwd)}"]
        if service.offline:
            lines += [
                f"Remove-Item -LiteralPath 'Env:{key}' -ErrorAction SilentlyContinue"
                for key in PROVIDER_KEYS
            ]
        lines += [f"$env:{name} = {quote(value)}" for name, value in service.env.items()]
        lines.append("& " + quote(service.command[0]) + " " + " ".join(service.command[1:]))
    lines += [f"\nOpen {plan.website_url}", "Health checks do not start assistance."]
    return "\n".join(lines)


def check_stack(plan: StackPlan) -> dict[str, bool]:
    results = {}
    with httpx.Client(timeout=3, trust_env=False, follow_redirects=False) as client:
        for service in plan.services():
            try:
                path = "/" if service.name == "worker" else "/healthz"
                response = client.get(f"http://127.0.0.1:{service.port}{path}")
                results[service.name] = response.status_code == 200
            except httpx.HTTPError:
                results[service.name] = False
    return results


def stop_owned(process: subprocess.Popen, timeout: float = 25) -> bool:
    if process.poll() is not None:
        return True
    try:
        if process.stdin is not None:
            process.stdin.write("stop\n")
            process.stdin.flush()
        elif os.name == "nt":
            process.send_signal(signal.CTRL_BREAK_EVENT)
        else:
            process.send_signal(signal.SIGTERM)
        process.wait(timeout=timeout)
        return True
    except (OSError, subprocess.TimeoutExpired):
        process.kill()  # Exact owned handle only; never kill a port's unknown owner.
        process.wait(timeout=5)
        return False


def run_stack(
    plan: StackPlan,
    *,
    allow_live: bool = False,
    duration: float | None = None,
    startup_timeout: float = 180,
) -> int:
    if not math.isfinite(startup_timeout) or not 0 < startup_timeout <= 600:
        raise ValueError("Startup timeout must be finite, positive and at most 600 seconds")
    if plan.mode == "live" and not allow_live:
        raise ValueError("Live launch requires --allow-live; Cloud/providers may incur costs")
    services = plan.services()
    busy = occupied_ports([s.port for s in services])
    if busy:
        raise ValueError(f"Ports already occupied: {busy}. Choose others; no process was stopped.")
    for service in services:
        if not Path(service.command[0]).is_file():
            raise ValueError(f"Missing interpreter for {service.name}; follow FINAL_RUNBOOK.md")
    processes: list[subprocess.Popen] = []
    try:
        for service in services:
            process = subprocess.Popen(
                [
                    service.command[0],
                    str(plan.root.resolve() / "orchestration/tools/launch_child.py"),
                    *service.command[1:],
                ],
                cwd=service.cwd,
                env=service.environment(),
                shell=False,
                stdin=subprocess.PIPE,
                text=True,
                creationflags=subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.CREATE_NO_WINDOW
                if os.name == "nt"
                else 0,
                start_new_session=os.name != "nt",
            )
            processes.append(process)
            deadline = time.monotonic() + startup_timeout
            with httpx.Client(timeout=1, trust_env=False) as client:
                while True:
                    if process.poll() is not None:
                        raise RuntimeError(
                            f"{service.name} exited during startup; inspect terminal"
                        )
                    try:
                        path = "/" if service.name == "worker" else "/healthz"
                        if client.get(f"http://127.0.0.1:{service.port}{path}").status_code == 200:
                            break
                    except httpx.HTTPError:
                        pass
                    if time.monotonic() > deadline:
                        raise RuntimeError(f"{service.name} startup timed out")
                    time.sleep(0.1)
            print(f"READY {service.name} port={service.port}; health only", flush=True)
        print(f"OPEN {plan.website_url}; Ctrl+C stops this owned stack", flush=True)
        started = time.monotonic()
        while duration is None or time.monotonic() - started < duration:
            if any(process.poll() is not None for process in processes):
                raise RuntimeError("A stack process exited; stopping only owned processes")
            time.sleep(0.1)
        return 0
    except KeyboardInterrupt:
        return 0
    finally:
        # Session teardown disconnects rooms while worker and website still exist.
        order = [1, 2, 0] if len(processes) == 3 else list(reversed(range(len(processes))))
        forced = False
        for index in order:
            if index < len(processes):
                if not stop_owned(processes[index]):
                    forced = True
                    print(
                        "WARNING forced owned-process stop; remote cleanup remains unverified",
                        flush=True,
                    )
        if forced:
            raise RuntimeError("Owned process required a forced stop; remote cleanup unverified")
