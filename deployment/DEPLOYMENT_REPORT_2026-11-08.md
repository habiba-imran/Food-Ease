# Zara production deployment — 2026-11-08

**Cloud deployment succeeded. Full production activation and voice-ordering acceptance
remain open.** The user confirmed the frontend is
<https://food-ease-seven.vercel.app> and that no backend is hosted yet. The Cloud
worker intentionally rejects jobs until its public backend callback is configured.
The user will host that backend on Render; follow the
[exact Render/Vercel guide](RENDER_VERCEL_GUIDE.md).

## Deployed artifact and evidence

| Field | Verified value |
|---|---|
| FoodEase Cloud project | `foodease-nb0qr57x` |
| Agent ID | `CA_gibAwTdK3sjn` |
| Dispatch name | `foodease` |
| Region | `ap-south`, Mumbai / India South |
| Final version | `ckhnpPJ2Lg5h` |
| Status | **Running**, one replica |
| Image digest | `sha256:f2902feb241a005781fa05a108edf94141ba29ccf09a97730ffce622474b0e02` |
| Startup | SDK 1.8.4, HTTP health server on 8081, VAD prewarmed, worker registered |

See [status](evidence/cloud-status.txt), [final deploy](evidence/cloud-deploy.txt)
and [final startup logs](evidence/cloud-logs.txt). Final prewarm processes initialized
in 0.30 and 0.29 seconds. These are process startup times, not response latency.
The CLI's existing Windows global-config permissions warning was retained; no unrelated
project or global CLI configuration was changed.

The deployment uses existing Groq LLM/Urdu Whisper STT and Cartesia TTS. The invalid
local voice configuration resolves through the existing validated default; no new voice
provider was introduced. Provider credentials are Cloud secrets. Cloud supplies its own
LiveKit connection credentials. No credentials were printed, committed or baked into an
image. Recording and development mode are disabled.

## Implemented production path

- Root Dockerfile: locked dependencies, nonroot worker, cached model assets, SDK health
  endpoint, production entrypoint and credential-free allowlisted build context.
- Secure Cloud helper binds the existing agent ID and explicitly selects FoodEase,
  stages only approximately 0.96 MB before requesting the CLI upload policy, uses a
  temporary secrets file outside that context and redacts captured output.
- Single-process Render backend combines the existing actual cart authority and
  owner-bound assistance/token service. It preserves readiness, generation, cleanup,
  authorization and checkout safeguards; it does not replace them with a mock.
- Vercel serves a stateless same-origin gateway. Fixed HTTPS upstream, owner-cookie
  filtering, origin/body/header validation, no-cache responses, redirect rejection and
  no automatic mutation retries keep credentials and state on the backend.
- Worker startup requires a public HTTPS callback in Cloud. Missing hosting fails closed.
- Reuse the prewarmed VAD instead of loading it again per session. Supported SDK message
  metrics log allowlisted timing fields without transcripts. Explicit Urdu quantity
  guidance was added after the provider probe, but the retest still failed that scenario.

No Render service, Vercel deployment, Git commit or push was performed. The Cloud image
was built from this checkout, including the earlier Zara review changes. Render/Vercel
must receive the new source before their configuration can take effect.

## Commands actually executed

Commands below omit private environment values; the helper supplies them internally.

```powershell
docker version
lk --version
docker build -t foodease-zara:production .
docker build -f deployment/backend.Dockerfile -t foodease-backend:production .
.\voice-agent\.venv\Scripts\python.exe deployment/cloud.py list
.\voice-agent\.venv\Scripts\python.exe deployment/cloud.py create
.\voice-agent\.venv\Scripts\python.exe deployment/cloud.py deploy
.\voice-agent\.venv\Scripts\python.exe deployment/cloud.py status
.\voice-agent\.venv\Scripts\python.exe deployment/cloud.py secrets
.\voice-agent\.venv\Scripts\python.exe deployment/cloud.py logs
.\voice-agent\.venv\Scripts\python.exe deployment/cloud_room_check.py
.\voice-agent\.venv\Scripts\python.exe deployment/provider_probe.py
```

The helper invokes `lk agent create/deploy/status/secrets/logs` with the correct
project environment and agent ID. Initial creation needed a root SDK-detection
manifest. One full-checkout upload expired with HTTP 403 after creating the agent;
subsequent staged deployments reused that ID and succeeded. No duplicate agent was
created. The final image was built successfully by LiveKit Cloud. Local worker and
backend images also built; a backend container returned health, catalog and shopping
session responses successfully after correcting editable-package asset paths.

## Verification results and limits

| Check | Outcome |
|---|---|
| Cloud status, startup, health listener, registered dispatch | Passed on final version |
| Actual RTC room connection and named agent dispatch | Passed on initial deployed version; disposable room and dispatch deleted |
| Missing-backend Cloud guard | Expected rejection observed in Cloud logs |
| Website suite | 45 passed |
| Backend/orchestration suite | 55 passed, 3 inherited failures from a missing requirements document |
| Worker suite | 472 passed, 1 inherited mock-boundary failure |
| New actual gateway-to-authority shopping/session integration | Passed; real local cart total and owner-bound assistance preparation |
| Current browser voice/wake activation suite | 18 passed using fake RTC/provider/recognition boundaries |
| New Cloud-startup/metrics focused checks | 6 passed |
| Prompt safety/dialogue and related focused checks | 20 passed |
| Scoped lint/types and whitespace check | Passed |
| Real provider synthetic Urdu ordering/consecutive turns | **Failed**: unnecessary quantity question, then Groq HTTP 429 |
| Production frontend voice connection | Pending Render hosting and Vercel redeployment |
| Cloud STT → LLM → TTS conversation with real cart | Pending backend and successful provider acceptance |
| Physical microphone, interruption/reconnect, natural Urdu listening acceptance | Unverified |

Final worker suite results are recorded in [worker-tests.txt](evidence/worker-tests.txt).
Website and backend raw summaries are in [website-tests.txt](evidence/website-tests.txt)
and [backend-tests.txt](evidence/backend-tests.txt). The inherited backend failures
reference `Zainab_Web_Application_UI_UX_Requirements_Specification (1).md`; no fabricated
replacement document or acceptance result was added. The worker's inherited mock-boundary
failure is `test_no_mock_leak.py`, because `integration/scenarios.py` imports mock code.

[Room evidence](evidence/cloud-room-check.json) records a real RTC connection in
3,653.22 ms, named dispatch creation/lookup and successful cleanup. The worker received
the dispatched job and rejected it because `FOODEASE_SESSION_API` was not configured.
No microphone was used and this was not a conversation test. The final version was then
verified by status and fresh startup logs; the room result belongs to the initial version.

## Measured provider latency and failures

[Final synthetic probe](evidence/provider-probe.json) used real provider APIs with
generated Urdu input and the actual local website cart authority. No audio was saved,
no order was submitted, and this did not run inside the Cloud room.

| Sample | STT request | Model/tools to completed reply | Response TTS first frame | Serialized total |
|---|---:|---:|---:|---:|
| Clarification despite explicit one cola | 488.92 ms | 800.57 ms | 330.52 ms | 1,620.01 ms |
| Cart-total turn ending in rate-limit warning | 283.73 ms | 1,523.12 ms | 330.82 ms | 2,137.67 ms |

These are two serialized diagnostic samples after synthetic input is available, not
streaming caller-heard response times, not successful-order latency, and not p50/p95.
The first turn performed no tool call and left the cart empty. The second executed
`get_cart` but Groq returned HTTP 429 during the follow-up. The account reported an
8,000-token-per-minute limit; the current prompt/tool/context size makes consecutive
turns vulnerable to that limit. Provider changes, higher-cost plans and quota upgrades
were not performed. Explicit quantity instructions did not establish reliable shopping;
this remains an acceptance failure requiring further evaluation after capacity is adequate.

## Required user steps

1. Publish the reviewed source to the Git branch connected to Render and Vercel.
2. Create the single-instance Render service using `deployment/backend.Dockerfile` and
   the exact environment settings in the guide. Review the always-on plan charge yourself.
3. With its actual HTTPS origin, run `deployment/cloud.py configure-backend --backend-url
   https://YOUR-ACTUAL-SERVICE.onrender.com`. This updates only the callback secret and
   restarts the existing Cloud agent; it does not overwrite provider keys.
4. In Vercel → FoodEase → Settings → Environment Variables, set the following for
   **Production**, then redeploy the new source:

   | Exact variable | Value/source | Classification |
   |---|---|---|
   | `FOODEASE_BACKEND_URL` | Actual Render HTTPS origin | Nonsecret, server-side |
   | `ORCHESTRATION_BASE_URL` | `/assist` | Nonsecret, visible path |
   | `ENABLE_MOCK_AGENT` | `false` | Nonsecret, server-side |

   Select Preview only when needed and allow that exact Preview origin on Render.
   No LiveKit API secret or provider key belongs on Vercel in this configuration.
5. Resolve Groq capacity and rerun the live shopping/consecutive-turn test. Complete
   the device/Urdu/interruption/reconnection acceptance in the guide before calling
   the system production-ready.

The backend retains existing in-memory state: one process and one replica are required;
restarts expire carts and assistance generations. Durable storage is separate work.
**Full setup guide: [RENDER_VERCEL_GUIDE.md](RENDER_VERCEL_GUIDE.md).**
