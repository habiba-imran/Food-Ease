"""A sleeping worker may take longer than 30s; the startup lease stays finite."""

import asyncio

from foodease_session.lifecycle import AssistanceService
from test_lifecycle import Authority, Cloud, seats, settings


def test_default_startup_budget_survives_45_seconds_and_expires_at_90():
    async def case():
        now = [0.0]
        cloud = Cloud()
        service = AssistanceService(settings(), Authority(), cloud, clock=lambda: now[0])
        prepared = await service.start("owner", "shop", "request", consent=True)
        seats(cloud, prepared)
        await service.ready("owner", "shop", "request", prepared["generation"], 1, True, True, True)
        now[0] = 45
        assert (await service.status("owner", "shop", "request"))["state"] == "waiting_worker"
        assert not cloud.deleted
        now[0] = 90
        await service.sweep()
        assert (await service.status("owner", "shop", "request"))["state"] == "ended"
        assert cloud.deleted == ["dispatch-1"]

    asyncio.run(case())
