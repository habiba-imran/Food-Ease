# FoodEase shared contract

Pure contract 2.0 validation and projections, with Pydantic as the only runtime
dependency. No website, voice, provider or network imports. Both sibling packages
install this directory as the editable `foodease-contract==2.0.0` dependency.

Canonical models live in `foodease_contract.models`. The original agent v2 import
paths re-export them for compatibility. Frozen v1 models and artifacts remain in
the agent and are unchanged. The legacy projection helpers are for v1 data;
the current website authority already emits validated 2.0 context/results.

`startup.py` validates private dispatch binding for the Phase 3 lifecycle. Its
worker proof is server/worker data and must not be published as a browser event.

Verify through `website/tests/test_session_authority.py`, the agent v1/v2 contract
suite and `orchestration/tools/phase2_verify.py`. See the
[authority document](../orchestration/docs/PHASE_02_APPLICATION_AUTHORITY.md).
