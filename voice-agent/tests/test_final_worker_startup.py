"""Worker CLI configuration is loaded before the installed SDK resolves auth/name."""

import pytest

from foodease_agent import worker

pytest_plugins = ("test_integrated_runtime",)


def test_worker_loads_environment_before_constructing_cli_options(monkeypatch):
    calls = []

    def load(*args, **kwargs):
        calls.append("environment")
        monkeypatch.setenv("FOODEASE_AGENT_NAME", "final-worker")

    def run(options):
        calls.append("cli")
        assert options.agent_name == "final-worker"

    monkeypatch.setattr(worker, "load_dotenv", load)
    monkeypatch.setattr(worker.cli, "run_app", run)
    worker.main()
    assert calls == ["environment", "cli"]


@pytest.mark.asyncio
async def test_action_trace_contains_correlation_without_arguments_or_tokens(
    runtime, caplog, monkeypatch
):
    from test_integrated_runtime import call

    monkeypatch.delenv("FOODEASE_EVIDENCE_KIND", raising=False)
    caplog.set_level("INFO", logger="foodease.integrated.actions")
    await call(runtime, "cart_add_item", item_id="wrap-hot-chicken")
    assert runtime.snapshot.session_id in caplog.text
    assert "action_id" in caplog.text and "turn_id" in caplog.text
    assert "runtime_unattested" in caplog.text
    assert "wrap-hot-chicken" not in caplog.text
    assert "confirmation_token" not in caplog.text


def test_worker_health_port_is_configurable_without_changing_job_identity(monkeypatch):
    monkeypatch.setattr(worker, "load_dotenv", lambda *args, **kwargs: None)
    monkeypatch.setenv("FOODEASE_WORKER_PORT", "18081")

    def run(options):
        assert options.port == 18081
        assert options.initialize_process_timeout == 60
        assert options.request_fnc is worker.accept_job

    monkeypatch.setattr(worker.cli, "run_app", run)
    worker.main()
