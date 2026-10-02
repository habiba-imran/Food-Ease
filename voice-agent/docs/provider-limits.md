# Provider limits (DRAFT for V0.5)

Researched 02 Oct 2026 from public pages and third-party summaries. **Nothing here is confirmed until you tick
the box from your own dashboard.** Do not put keys in this file. Account holder: Habiba. Location: Pakistan.
Everything on the free tier, no card.

How to read the status column: `reported` = found online, not yet seen in my dashboard. Change to `confirmed (date)` after checking.

## 1. LiveKit Cloud (Build plan)

| Item | Value | Status |
|---|---|---|
| Price / card | $0, no card | reported |
| Agent session minutes | 1,000 / month | reported |
| WebRTC minutes | 5,000 / month | reported |
| Inference credits | $2.50 / month (about 50 min of pipeline) | reported |
| Overage on Build | None; service stops at the cap | reported |
| Region | Cannot be chosen on Build. Region pinning is Scale plan only. Default routing goes to the closest server. | reported (LiveKit docs) |
| Where my agent runs | On my own laptop in Pakistan (worker connects to LiveKit Cloud), not deployed on LiveKit Cloud | design choice |

- [ ] Confirm in dashboard whether a locally run worker consumes **agent session minutes** or only **WebRTC minutes**.
- [ ] Note the project URL region shown in the dashboard (if any).
- [ ] Demo-venue network session planned (0.2): date / place: ______

## 2. Deepgram

| Item | Value | Status |
|---|---|---|
| Free credit | $200 one-time, no card | reported |
| Credit expiry | **Sources disagree** (1 year vs no expiry). Check the console. | check |
| Flux English streaming | about $0.0065 / min, so $200 is roughly 30,000 min | reported |
| Nova-3 mono streaming | about $0.0048 / min | reported |
| Concurrency (streaming) | ______ | check |
| Data-use terms (free credit) | ______ (check model-improvement / data retention settings) | check |

- [ ] Confirm balance and expiry date: ______

## 3. Cartesia (Free plan): **the tight one**

| Item | Value | Status |
|---|---|---|
| Free credits | 20,000 / month (1 credit = 1 character of input text) | reported (pricing page) |
| Speech per month | about 27 minutes of Sonic-3.6 | reported |
| Credits roll over | No, they expire each cycle | reported |
| Concurrency | 1 or 2 (sources differ) | check |
| Commercial use | Not included; fine for a course demo | reported |
| Paid option | Pro $5 / month = 100,000 credits (about 133 min) | reported |
| Sonic 3.6 available on my account | ______ | **confirm in playground / API** |
| Speed / volume controls work on Sonic 3.6 | ______ | Phase 1 spike (ADR) |

- [ ] Credits remaining at start of Phase 1: ______  Reset date: ______

### Cartesia credit budget (my estimate, not measured)

| Use | Rough credits |
|---|---|
| Phase 1: audition (4 voices x 8 lines), TTFB runs, number sheet | 8,000 to 9,000 |
| Phase 5/7/8: voice test sessions | 10,000 to 15,000 |
| Phase 6D: pronunciation sheet, 50 lines x about 3 passes | about 9,000 |
| Phase 6D: dogfooding, about 15 sessions | about 18,000 |
| Phase 9: measurement passes (about 7 x 40 turns) | about 28,000 |
| Phase 10: live tests and usability | about 15,000 |
| **Total** | **about 100,000 (about 5 free months)** |

Rules to stay inside the free plan:
1. Phases 2, 3 and 4 need no TTS (text mode). Do not spend credits there.
2. Generate audition and pronunciation clips **once**, save the audio locally (git-ignored), replay from disk.
3. Run TTFB timing on the 2 finalist voices only.
4. Use a cheaper TTS (for example Deepgram Aura, billed against the Deepgram credit) **only** for logic and soak tests.
   Never for audition, pronunciation, panel or any number reported in Phase 9. Log it as an ADR.
5. Check remaining credits at the start of every voice session. Stop and wait for the reset if a phase can't finish.

## 4. Google AI Studio / Gemini

| Item | Value | Status |
|---|---|---|
| Available in Pakistan | Yes, Pakistan is on Google's supported list | reported (Google docs) |
| Free tier | No billing needed | reported |
| Per-model limits | **Not published on the docs page now**; shown per project in the AI Studio rate-limit console | check |
| gemini-3.1-flash-lite free limits | One third-party site reports 500 requests/day (Sept 2026). Unverified. | **confirm in console** |
| Daily quota reset | Midnight Pacific time | reported |
| Free-tier data use | Free-tier requests may be used to improve Google products, so **fictional data only** (R13) | reported |

- [ ] RPM: ______  TPM: ______  RPD: ______  (from AI Studio rate-limit console, date: ______)
- [ ] Fallback model chosen and its limits (needed for Phase 1.3 / 8.2): ______

### LLM request budget, Phases 1 to 10 (my estimate, not measured)

Assumption: a turn that calls a tool costs about 2 LLM requests, a plain reply 1, so about 1.6 requests per turn on average.

| Phase | What | Approx. requests |
|---|---|---|
| 1 | LLM spike, two thinking levels, fallback model | 250 |
| 4 | V4.2 to V4.5 text tests, repeated runs | 480 |
| 5 | Voice tests, 20-min soak, free conversation | 400 |
| 6 | Dialogue suite per prompt version (about 5 versions), safety re-runs, dogfooding | 1,600 |
| 7 | Scripted sessions over real transport | 160 |
| 8 | VA-17 tests, 30-min chaos run | 320 |
| 9 | Baseline, 5 tuning levers, final campaign, Mode 2 | 590 |
| 10 | T01 to T20, live runs, dialogue re-run, usability | 560 |
| **Total** | | **about 4,400 (plus or minus 50%)** |

- [ ] Compare against RPD and RPM above. If the real limit is about 500/day, heavy days are fine; plan the Phase 9 campaign and Phase 6 suite runs across separate days.
- [ ] **RPM is the real risk for voice**: a tool turn fires 2 requests within seconds. If RPM is single digits, test early in Phase 1.3.
- [ ] Replace this estimate with real counts after Phase 4 (from the metrics log).

## 5. Open items

- Free-tier data-use terms for LiveKit, Deepgram and Cartesia: not checked yet.
- Trial/credit end dates: ______
- Everything above marked `check` or `confirm` must be resolved before closing V0.5.
