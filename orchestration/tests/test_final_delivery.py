"""Final launch and acceptance logic; no credentials, provider or Cloud access."""

from __future__ import annotations

import importlib.util
import json
import os
import socket
import subprocess
import sys
import time
from pathlib import Path
from types import SimpleNamespace

import pytest

from foodease_session import bringup
from foodease_session.bringup import StackPlan, occupied_ports, powershell_commands, run_stack

ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.parametrize("package", ["orchestration", "website"])
def test_owned_child_can_inspect_stdin_then_receive_private_graceful_stop(tmp_path, package):
    # Native imports inspect stdin. A concurrent buffered readline can hold its
    # lock indefinitely while the parent deliberately keeps the control pipe open.
    (tmp_path / "uvicorn.py").write_text(
        "import sys, time\n"
        "def main():\n"
        "    time.sleep(0.1)\n"
        "    try: sys.stdin.buffer.tell()\n"
        "    except OSError: pass\n"
        "    print('ready', sys.stdin.isatty(), flush=True)\n"
        "    try:\n"
        "        while True: time.sleep(0.02)\n"
        "    except KeyboardInterrupt:\n"
        "        print('graceful-stop', flush=True)\n"
    )
    env = StackPlan(ROOT).services()[0].environment()
    env["PYTHONPATH"] = str(tmp_path)
    interpreter = (
        Path(sys.executable) if package == "orchestration"
        else ROOT / package / ".venv" / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    )
    if not interpreter.is_file():
        pytest.skip("Delivery interpreter is not installed")
    output = tmp_path / "child.log"
    with output.open("w", encoding="utf-8") as log:
        process = subprocess.Popen(
            [str(interpreter), str(ROOT / "orchestration/tools/launch_child.py"), "-m", "uvicorn"],
            cwd=tmp_path,
            env=env,
            stdin=subprocess.PIPE,
            stdout=log,
            stderr=subprocess.STDOUT,
            text=True,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
        )
        try:
            deadline = time.monotonic() + 5
            while "ready False" not in output.read_text(encoding="utf-8"):
                assert process.poll() is None, output.read_text(encoding="utf-8")
                assert time.monotonic() < deadline, "Child blocked inspecting its open stdin"
                time.sleep(0.02)
            assert process.stdin is not None
            process.stdin.write("stop\n")
            process.stdin.flush()
            assert process.wait(timeout=5) == 0
        finally:
            if process.poll() is None:
                process.kill()
                process.wait(timeout=5)
            if process.stdin is not None:
                process.stdin.close()
    assert "graceful-stop" in output.read_text(encoding="utf-8")


def test_configurable_startup_waits_for_cold_import_and_cleans_up_on_timeout(
    monkeypatch, tmp_path
):
    plan = StackPlan(tmp_path)
    for service in plan.services():
        interpreter = Path(service.command[0])
        interpreter.parent.mkdir(parents=True)
        interpreter.touch()
    clock, spawned, stopped = [0.0], [], []

    def spawn(*args, **kwargs):
        process = SimpleNamespace(poll=lambda: None)
        spawned.append(process)
        return process

    class HealthClient:
        def __init__(self, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def get(self, url):
            return SimpleNamespace(status_code=200 if clock[0] >= 100 else 503)

    monkeypatch.setattr(bringup, "occupied_ports", lambda ports: [])
    monkeypatch.setattr(bringup.subprocess, "Popen", spawn)
    monkeypatch.setattr(bringup.httpx, "Client", HealthClient)
    monkeypatch.setattr(bringup.time, "monotonic", lambda: clock[0])
    monkeypatch.setattr(bringup.time, "sleep", lambda seconds: clock.__setitem__(0, clock[0] + 10))
    monkeypatch.setattr(bringup, "stop_owned", lambda process: stopped.append(process) or True)
    with pytest.raises(RuntimeError, match="startup timed out"):
        run_stack(plan, duration=0, startup_timeout=60)
    assert stopped == spawned and len(spawned) == 1
    clock[0] = 0
    spawned.clear()
    stopped.clear()
    assert run_stack(plan, duration=0, startup_timeout=180) == 0
    assert stopped == list(reversed(spawned)) and len(spawned) == 2
    spawned.clear()
    stopped.clear()
    monkeypatch.setattr(bringup, "stop_owned", lambda process: stopped.append(process) or False)
    with pytest.raises(RuntimeError, match="forced stop"):
        run_stack(plan, duration=0, startup_timeout=180)
    assert stopped == list(reversed(spawned)) and len(spawned) == 2


@pytest.mark.parametrize("timeout", [0, float("nan"), 601])
def test_invalid_startup_deadline_never_launches_a_process(monkeypatch, timeout):
    def forbidden(*args, **kwargs):
        pytest.fail("Invalid startup deadline must fail before process creation")

    monkeypatch.setattr(bringup.subprocess, "Popen", forbidden)
    with pytest.raises(ValueError, match="Startup timeout"):
        run_stack(StackPlan(ROOT), startup_timeout=timeout)


def test_final_plan_has_real_services_distinct_ports_and_safe_environment():
    plan = StackPlan(ROOT, mode="live")
    services = plan.services()
    assert [s.name for s in services] == ["website", "session", "worker"]
    assert len({s.port for s in services}) == 3
    assert "foodease_agent.worker" in services[-1].command
    assert "start" in services[-1].command
    for service in services:
        assert service.env["RECORD_AUDIO"] == "false"
        assert service.env["DEV_MODE"] == "false"
        assert "mock_app" not in " ".join(service.command)
        assert "harness" not in " ".join(service.command)
    assert services[1].env["CORS_ORIGINS"] == plan.website_url
    assert services[-1].env["FOODEASE_APP_TRANSPORT"] == "website"
    assert services[-1].env["FOODEASE_SESSION_API"] == plan.session_url


def test_manual_mode_disables_credentials_dispatch_and_has_no_worker():
    plan = StackPlan(ROOT, mode="manual")
    assert [s.name for s in plan.services()] == ["website", "session"]
    for service in plan.services():
        env = service.environment(
            {"GOOGLE_API_KEY": "never-print-this", "LIVEKIT_API_KEY": "private"}
        )
        assert "GOOGLE_API_KEY" not in env and "LIVEKIT_API_KEY" not in env
        assert env["PYTHON_DOTENV_DISABLED"] == "1"
        assert env["LIVEKIT_AGENT_DISPATCH"] == "false"


@pytest.mark.parametrize("ports", [(8080, 8080, 8081), (0, 8090, 8081), (8080, 65536, 8081)])
def test_invalid_or_conflicting_ports_fail_before_launch(ports):
    with pytest.raises(ValueError):
        StackPlan(ROOT, website_port=ports[0], session_port=ports[1], worker_port=ports[2])


def test_port_detection_does_not_reuse_or_kill_existing_service():
    with socket.socket() as owned:
        owned.bind(("127.0.0.1", 0))
        owned.listen()
        port = owned.getsockname()[1]
        assert occupied_ports([port]) == [port]
        assert owned.fileno() >= 0


def test_live_launch_requires_explicit_cost_opt_in_before_any_process():
    with pytest.raises(ValueError, match="allow-live"):
        run_stack(StackPlan(ROOT, mode="live"), allow_live=False)


def test_printed_commands_are_powershell_root_independent_and_never_pass_secrets():
    text = powershell_commands(StackPlan(ROOT / "a path with spaces", mode="live"))
    assert "Set-Location -LiteralPath" in text
    assert "& '" in text and "-m foodease_agent.worker start" in text
    assert "$env:FOODEASE_APP_TRANSPORT = 'website'" in text
    assert "set DEV_MODE" not in text and "&&" not in text
    assert "--api-secret" not in text


def acceptance_tool():
    spec = importlib.util.spec_from_file_location(
        "final_acceptance", ROOT / "orchestration/tools/final_acceptance.py"
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_acceptance_preparation_covers_all_final_scenarios_and_never_passes_empty_evidence(
    tmp_path,
):
    tool = acceptance_tool()
    tool.prepare(tmp_path)
    observations = json.loads((tmp_path / "observations.json").read_text())
    assert len(observations["scenarios"]) == 63  # O21 + W22 + T20
    assert all(row["status"] == "not_run" for row in observations["scenarios"])
    report = tool.evaluate(tmp_path)
    assert report["live_gate"] == "pending"
    assert report["audible_samples"] == 0
    assert report["human_listeners"] == 0
    assert not report["targets_passed"]


def test_metrics_reject_nonfinite_wrong_clock_and_provider_time(tmp_path):
    tool = acceptance_tool()
    base = {
        "sample_id": "one",
        "kind": "response",
        "warmth": "warm",
        "clock_id": "browser-1",
        "source": "audible_observation",
        "onset_ms": 100,
        "playback_ms": 250,
        "completed": True,
        "genuine": True,
        "evidence": "measurement.md",
    }
    for field, value in [
        ("playback_ms", float("nan")),
        ("playback_ms", 50),
        ("source", "tts_first_byte"),
        ("clock_id", ""),
    ]:
        with pytest.raises(ValueError):
            tool.validate_sample({**base, field: value})
    assert tool.validate_sample(base)["latency_ms"] == 150


def test_percentiles_are_nearest_rank_and_failures_count_for_reliability():
    tool = acceptance_tool()
    assert tool.percentile([100, 300, 200, 400], 0.5) == 200
    assert tool.percentile([100, 300, 200, 400], 0.95) == 400
    assert tool.percentile([], 0.95) is None


def test_missing_fake_or_path_escaping_evidence_cannot_close_live_gate(tmp_path):
    tool = acceptance_tool()
    tool.prepare(tmp_path)
    data = json.loads((tmp_path / "observations.json").read_text())
    data["kind"] = "offline"
    for row in data["scenarios"]:
        row.update(status="pass", evidence="../../secret.env")
    (tmp_path / "observations.json").write_text(json.dumps(data))
    with pytest.raises(ValueError):
        tool.evaluate(tmp_path)


def synthetic_complete_manifest(tmp_path):
    """Calculator fixture only; these are not actual human/provider observations."""
    tool = acceptance_tool()
    tool.prepare(tmp_path)
    (tmp_path / "fixture.txt").write_text("SYNTHETIC UNIT FIXTURE; NOT LIVE ACCEPTANCE")
    path = tmp_path / "observations.json"
    data = json.loads(path.read_text())
    data.update(
        kind="live",
        human_observed=True,
        transport="livekit",
        providers="live",
        environment_evidence="fixture.txt",
        real_model_turns=40,
    )
    for group in ("scenarios", "devices", "accessibility", "faults"):
        for row in data[group]:
            row.update(status="pass", evidence="fixture.txt", observer="fixture-only")
    data["listeners"] = [
        {"id": str(i), "naturalness": 4, "helpfulness": 4, "evidence": "fixture.txt"}
        for i in range(3)
    ]
    for i, kind in enumerate(["response"] * 30 + ["interruption"] * 10 + ["greeting"] * 2):
        data["samples"].append(
            {
                "sample_id": str(i),
                "kind": kind,
                "warmth": "warm" if i % 2 else "cold",
                "clock_id": "unit-fixture",
                "source": "audible_observation",
                "onset_ms": 100,
                "playback_ms": 200,
                "completed": True,
                "genuine": True,
                "evidence": "fixture.txt",
            }
        )
    return tool, path, data


def test_acceptance_calculator_checks_all_targets_and_does_not_omit_failed_attempts(tmp_path):
    tool, path, data = synthetic_complete_manifest(tmp_path)
    path.write_text(json.dumps(data))
    assert tool.evaluate(tmp_path)["live_gate"] == "passed"
    for sample in data["samples"][:2]:
        sample.update(completed=False, playback_ms=None)
    path.write_text(json.dumps(data))
    report = tool.evaluate(tmp_path)
    assert report["ordinary_attempts"] == 30
    assert report["scripted_completion_fraction"] == 28 / 30
    assert not report["targets_passed"] and report["live_gate"] != "passed"
    data["kind"] = "offline"
    path.write_text(json.dumps(data))
    assert not tool.evaluate(tmp_path)["provenance_complete"]


def test_lifecycle_logs_correlate_dispatch_without_private_proof(caplog):
    import asyncio

    from test_lifecycle import seats, service

    caplog.set_level("INFO", logger="foodease.session.lifecycle")

    async def scenario():
        svc, _, cloud, _ = service()
        prepared = await svc.start("owner", "shop", "request", consent=True)
        proof = svc.current["shop"].startup.worker_proof
        seats(cloud, prepared)
        await svc.ready("owner", "shop", "request", prepared["generation"], 1, True, True, True)
        await svc.end("owner", "shop", "request", prepared["generation"])
        assert prepared["generation"] in caplog.text and "dispatch-1" in caplog.text
        assert proof not in caplog.text and "worker_proof" not in caplog.text
        assert '"session_id":"shop"' in caplog.text

    asyncio.run(scenario())
