"""A worker redeploy must not replace Cloud provider settings with local values."""

import importlib.util
from pathlib import Path


def test_code_only_deploy_stages_no_environment_and_sends_no_secrets(monkeypatch):
    root = Path(__file__).resolve().parents[2]
    spec = importlib.util.spec_from_file_location(
        "foodease_cloud_test", root / "deployment/cloud.py"
    )
    assert spec is not None and spec.loader is not None
    cloud = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(cloud)
    monkeypatch.setattr(
        cloud,
        "local_environment",
        lambda: {
            "LIVEKIT_URL": "wss://foodease-nb0qr57x.livekit.cloud",
            "LIVEKIT_API_KEY": "test-key",
            "LIVEKIT_API_SECRET": "test-secret",
            "LLM_PROVIDER": "do-not-copy-local-settings",
        },
    )
    captured = []

    def run_cli(arguments, env):
        assert arguments[:4] == ["agent", "deploy", "--id", "CA_gibAwTdK3sjn"]
        assert not any("secret" in argument for argument in arguments)
        stage = Path(arguments[-1])
        assert (stage / "voice-agent/src/foodease_agent/session.py").is_file()
        assert not any(path.name.startswith(".env") for path in stage.rglob("*"))
        captured.append(arguments)
        return 0

    monkeypatch.setattr(cloud, "run_cli", run_cli)
    monkeypatch.setattr("sys.argv", ["cloud.py", "deploy", "--code-only"])
    assert cloud.main() == 0 and len(captured) == 1
    assert not Path(captured[0][-1]).exists()
