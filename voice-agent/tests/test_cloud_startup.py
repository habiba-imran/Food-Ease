from types import SimpleNamespace
from unittest.mock import AsyncMock

from foodease_agent import worker
from test_integrated_startup import binding


async def test_cloud_rejects_dispatch_until_the_public_backend_is_configured(monkeypatch):
    monkeypatch.setenv("FOODEASE_APP_TRANSPORT", "website")
    monkeypatch.setenv("FOODEASE_CLOUD_RUNTIME", "1")
    monkeypatch.delenv("FOODEASE_SESSION_API", raising=False)
    request = SimpleNamespace(
        job=SimpleNamespace(metadata=binding().model_dump_json()),
        accept=AsyncMock(),
        reject=AsyncMock(),
    )
    await worker.accept_job(request)
    request.reject.assert_awaited_once()
    request.accept.assert_not_awaited()


async def test_cloud_preserves_the_original_bound_agent_identity(monkeypatch):
    monkeypatch.setenv("FOODEASE_APP_TRANSPORT", "website")
    monkeypatch.setenv("FOODEASE_CLOUD_RUNTIME", "1")
    monkeypatch.setenv("FOODEASE_SESSION_API", "https://backend.onrender.com/assist")
    request = SimpleNamespace(
        job=SimpleNamespace(metadata=binding().model_dump_json()),
        accept=AsyncMock(),
        reject=AsyncMock(),
    )
    await worker.accept_job(request)
    assert request.accept.await_args.kwargs["identity"] == binding().binding.agent_identity
    request.reject.assert_not_awaited()
