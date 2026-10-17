# FoodEase final orchestration runbook

Current path: **real website → owner-bound session service → LiveKit app/user/agent
seats → integrated worker → the same website authority**. Habiba owns orchestration
and voice; Zainab owns the shopping UI. This runbook supersedes earlier MockApp,
harness and `/v1` bring-up instructions for the final website demo.

Implementation checks and live acceptance are separate. See
[Phase 9 evidence](../evidence/final/phase-09/report.md). No deployment or provider
usage is performed by reading this document or printing commands.

## 1. Install from the locked packages

Use ordinary PowerShell. Change the root only if the checkout is elsewhere:

```powershell
Set-Location -LiteralPath 'C:\HCI-PROJECT'
uv sync --locked --project voice-agent --python 3.12
uv sync --locked --project orchestration --python 3.12
uv sync --locked --project website --python 3.11
Push-Location -LiteralPath '.\website'
npm ci
npm run build
Pop-Location
```

The existing locks pin Python LiveKit agents/plugins 1.8.4, API 1.2.1 and browser
client 2.15.4. Do not upgrade these during a demonstration. If sandboxed Python says
`No Python at ...`, test the interpreter in ordinary PowerShell before rebuilding
the environment; sandbox access can cause that message. Node/uv must be installed.

## 2. Verify independent manual operation

```powershell
.\orchestration\.venv\Scripts\python.exe orchestration/tools/demo_up.py --mode manual --launch
```

Open **http://127.0.0.1:8080**. The helper starts the real website and an unconfigured
session HTTP service on 8090. It strips provider credentials, disables dotenv and
dispatch, and launches no worker. Manual search/cart/review/demo checkout work;
voice/typed assistance correctly reports unavailable. It is an offline manual
mode, not a simulated assistant. Default recording and mock-agent flags are off.

Stop with Ctrl+C. The helper requests graceful shutdown over private child stdin,
waits for the exact owned processes and never kills a port's unknown owner. It
reports a forced-stop fallback if grace fails; that cannot prove remote cleanup.
The bounded smoke below starts fresh temporary ports and verifies real HTTP and
port release without changing an existing running cart:

```powershell
.\orchestration\.venv\Scripts\python.exe orchestration/tools/manual_launch_smoke.py --output orchestration/evidence/final/phase-09/manual-local
```

Use a new evidence directory for each run.

## 3. Configure the live stack privately

Use existing private `voice-agent/.env` and `orchestration/.env` files, or copy the
package `.env.example` once if missing. Never overwrite an existing private file
with a template. Do not paste keys into chat, browser JavaScript, CLI arguments,
screenshots or evidence. The assistant did not inspect these private files.

The worker requires these names (the template and `docs/versions.md` hold the
selected nonsecret values):

| Category | Required configuration |
| --- | --- |
| Same LiveKit project in worker and session service | `LIVEKIT_URL`, `LIVEKIT_API_KEY`, `LIVEKIT_API_SECRET` |
| Speech/model credentials | `DEEPGRAM_API_KEY`, `GOOGLE_API_KEY`, `CARTESIA_API_KEY` |
| Provider selections | `STT_MODEL`, `LLM_MODEL`, `LLM_THINKING_LEVEL`, `TTS_MODEL`, `TTS_VOICE_ID` |
| Runtime settings | `VOICE_PIPELINE_CONFIG`, `IDLE_PROMPT_1_SECONDS`, `IDLE_PROMPT_2_SECONDS`, `SNAPSHOT_TIMEOUT_SECONDS` |
| Explicit safe flags | `RECORD_AUDIO=false`, `DEV_MODE=false`, `PREEMPTIVE_GENERATION=false`, plus `NOISE_CANCELLATION`, `GREETING_CACHE` |

The session service loads its own private file, falling back to missing values
from the worker file. The worker now loads its package configuration before SDK
CLI authentication/name resolution. The helper supplies matching `foodease` agent
names and explicit website transport. It sets recording off regardless of a stale
file setting. The integrated worker also passes `record=False` directly to the
public SDK `AgentSession.start()` API, so a Cloud project's recording default
cannot enable session recording. It passes `session_host=False` because browser
control uses the authenticated FoodEase transport rather than RemoteSession.
Config A uses Flux STT turn detection; Config B adds a turn detector
and requires its dependencies. Model availability and billing are live dependencies.
The SDK's supported job-initialization budget is 60 seconds for cold local VAD
loading, replacing its 10-second default. HTTP health may precede VAD readiness and
Cloud registration; check the actual `registered worker` event before a live demo.

If the local VAD assets are missing, download them during setup using the installed
SDK's supported command, with network access authorized:

```powershell
Push-Location -LiteralPath '.\voice-agent'
.\.venv\Scripts\python.exe -m livekit.agents download-files
Pop-Location
```

This downloads assets; it is not a conversation or an audio acceptance result.

## 4. Launch live after cost approval

```powershell
.\orchestration\.venv\Scripts\python.exe orchestration/tools/demo_up.py --mode live
# Review the printed PowerShell blocks. To own all three processes:
.\orchestration\.venv\Scripts\python.exe orchestration/tools/demo_up.py --mode live --launch --allow-live
```

The explicit live option permits connection to the configured account; a consented
conversation can incur provider/Cloud charges. This task's offline verification
does not itself authorize a paid session. Start mode uses the installed worker CLI
with no reload watcher and a bounded drain timeout.

Each service has a 180-second startup deadline to allow cold SDK/native imports.
Override it with `--startup-timeout SECONDS` (finite, positive, at most 600).
`--duration` bounds time after all services become healthy; startup and graceful
shutdown time are additional. A timeout is a failed startup, never a readiness pass.
The services bind loopback:

| Service | Default port | Role |
| --- | --- | --- |
| Website | 8080 | Catalog, cookie/session, authoritative cart, demo receipt, browser app/user seats |
| Session API | 8090 | `/v2/assist/*`, role tokens, one dispatch/generation, cleanup |
| Worker HTTP health | 8081 | SDK health; worker connects outbound to LiveKit |

If a port is occupied, the helper refuses to start. Inspect the owner yourself or
choose all needed overrides; no arbitrary process is killed:

```powershell
.\orchestration\.venv\Scripts\python.exe orchestration/tools/demo_up.py --mode live --website-port 18080 --session-port 18090 --worker-port 18081 --launch --allow-live
```

Overrides update website/session/worker URLs and CORS together. Use the same
hostname everywhere: **127.0.0.1 and localhost are different cookie scopes**.
The helper's read-only check does not mint tokens or create a dispatch:

```powershell
.\orchestration\.venv\Scripts\python.exe orchestration/tools/demo_up.py --mode live --check
```

A healthy process is not proof of configuration, worker registration, three seats
or audible output. Open the website and explicitly choose spoken welcome, voice,
typing or manual. First-visit microphone permission and autoplay need a gesture.
Typing alone captures no microphone. The authenticated ready handshake, not a
health label, admits the opening. Verify app/user/agent identities with the same
session and generation before marking a live scenario passed. The browser receives
short-lived role tokens only; private worker proof stays server-side.

## 5. Stop and recover

Choose Browse myself/End before stopping services. Tracks/audio stop locally first;
server dispatch and room cleanup may remain pending. Then Ctrl+C in the helper.
It stops the session service while worker and website still exist, then worker,
then website. A hard process/OS exit may lose in-memory cleanup records; inspect
the project's old dispatches/rooms privately before restarting. Do not infer
successful cleanup from an empty new registry or automatically repeat an order.

Shopping and receipt retention is single-process: idle 30 minutes, absolute two
hours, at most 128 sessions / 256 actions per session. Confirmation lasts five
minutes. Assistance has its own bounded process-local registry, a 30-second start
handshake and two-hour absolute lifetime. Reload can attach within retention;
restart or expiry can make an earlier receipt irrecoverable. Uncertain actions
keep their original IDs and are checked read-only. See [recovery](PHASE_08_RECOVERY.md).

Backgrounding/pagehide ends assistance. Credential lifetime and status failure
also stop locally. Returning requires another gesture. STT/TTS failure leaves
silent typing where healthy dependencies allow; model failure leaves manual only.
If startup fails, use the error message and manual ordering rather than a mock
assistant fallback. A speech-provider failure requires a fresh generation to
try voice again. A cleanup-pending generation blocks replacement.

## 6. Acceptance and measurements

```powershell
.\orchestration\.venv\Scripts\python.exe orchestration/tools/phase9_verify.py --output orchestration/evidence/final/phase-09/run-local
.\orchestration\.venv\Scripts\python.exe orchestration/tools/final_acceptance.py prepare --output orchestration/evidence/final/phase-09/live-local
# Fill observations and attach redacted local evidence after actual live testing.
.\orchestration\.venv\Scripts\python.exe orchestration/tools/final_acceptance.py evaluate --output orchestration/evidence/final/phase-09/live-local
```

The first command runs offline checks, native synthetic browser media and a real
manual launch. It cannot close live acceptance. Preparation copies **21 O + 22 W +
20 T** scenarios from the unchanged specifications, all not run. Where older W/T
wording says mock app/agent, final acceptance uses the actual website domain and
bound semantic transport. Retain the original expected outcome and document that
substitution in the observation. Use one fresh run folder; never overwrite history.

Live observations require Chrome desktop, Edge desktop, a phone browser, human
keyboard and screen-reader walkthroughs, nine dependency failure cases and scenario
evidence. Record environment date, versions, device/microphone/headphones, network,
model IDs, permission/autoplay delays and observer aliases in `environment.md`.
Keep earlier failures and skipped/unmeasurable cases. Do not mark a check passed
just because a unit test or SDK health check passed. Three listeners must rate
sampled real replies, median at least 4/5 for naturalness/helpfulness, with at least
40 actual model turns for the outstanding Phase 7 gate.

Collect at least 30 ordinary live response attempts and 10 genuine interruptions.
For each sample, a common clock must observe the actual speech end/onset and the
actual audible response/silence. SDK generation, first-token and TTS-first-byte
timings are not substitutes. Keep failures in the completion denominator, leave
unmeasured times null, and report warm/cold groups with sample counts. The evaluator
uses nearest-rank percentiles and the specified thresholds:

| Metric | Required p50 / p95 |
| --- | --- |
| Warm ready-to-audible greeting | ≤800 / ≤1500 ms |
| Cold join-to-audible greeting | ≤2000 / ≤4000 ms |
| Normal speech-end to meaningful audible reply | ≤1200 / ≤2500 ms |
| Genuine interruption onset to old audible playback stopping | p95 ≤350 ms |
| Scripted ordinary completion | ≥95%, failures included |

The JSON evaluator verifies coverage, references, counts and arithmetic over
**operator-attested observations**; it cannot independently certify their truth.
Blank evidence exits 2/pending. Explicit failed scenarios exit 1/failed. A pass
requires all declared observations, samples and targets. Existing waivers are
never automatically retired; review their actual replacement evidence jointly.

Structured `foodease_action` and `foodease_lifecycle` log lines correlate session,
generation, turn/action and dispatch IDs without action arguments, cart contents,
tokens or user transcripts. `offline_browser_fixture`, `offline`, `live_requested`
and `runtime_unattested` label provenance; requested live mode is not an acceptance
pass. No console transcript/recording archive is created by the launcher. Review
SDK diagnostics before sharing them; export only redacted evidence.

## 7. Support and deployment boundary

| Surface | Verified here |
| --- | --- |
| Windows PowerShell / existing locked venvs | Offline launch, real HTTP manual operation, shutdown/ports |
| Installed Chromium / local fake RTC/providers | Automated DOM, native synthetic capture, generated playback, keyboard activation and isolation |
| Physical Chrome / Edge / phone microphone and provider playback | Not evaluated |
| Human screen reader / comfortable conversation / noise | Not evaluated |
| Configured Cloud worker registration | Verified in a bounded startup check; no room or conversation |
| Three-seat Cloud sessions, provider quotas/outages and audible timing targets | Not evaluated |

A shareable demo is optional and requires separate deployment authorization.
Use HTTPS with a deliberate same-site origin. Prefer a single public origin,
proxying website paths to the website process and `/assist/v2/*` to the session
service with the prefix removed. Configure `ORCHESTRATION_BASE_URL` to that prefix,
`FOODEASE_WEBSITE_URL` to the internal website authority, and `CORS_ORIGINS` to the
exact public origin. Preserve the owner cookie, Origin and session headers; strip
untrusted forwarding headers and trust only the local proxy so HTTPS produces
Secure cookies. The cookie is HttpOnly and SameSite=Strict. Do not expose the worker
health port or provider keys. Allow outbound provider/LiveKit HTTPS/WSS and the RTC
connectivity required by the configured project. A phone cannot use your computer's
127.0.0.1 origin; it needs that authorized secure origin and a separate device test.

Use one website and one session process; there is no durable/multi-instance state,
real payment, restaurant inventory or persistent personal order history. No public
hosting, reverse proxy or clean-machine Cloud demo was deployed/verified in this
phase. Visual polish/animations remain Zainab's separate work.

SDK modes were checked against installed agents 1.8.4 and
[official startup-mode documentation](https://docs.livekit.io/agents/server/startup-modes/).
Recording and session-host options were checked against installed source and the
[public session API](https://docs.livekit.io/reference/python/livekit/agents/index.html)
and [recording options](https://docs.livekit.io/reference/agents/session-recording-options/).
