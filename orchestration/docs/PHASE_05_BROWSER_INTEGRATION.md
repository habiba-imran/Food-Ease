# Final orchestration Phase 5: browser bridge and one application view

Phase 5 connects the existing website to the bound app/user seats and the Phase 4
worker. It replaces the page's mock assistant execution/echo path. There is one
shopping authority, one action lane and one renderer for clicks, keyboard input,
agent RPCs and authoritative refreshes. The opening spoken-choice flow remains
Phase 6. The existing styles, animations and optional visual previews are retained.

## Browser delivery and launch

The browser uses **livekit-client 2.15.4**, matching the frozen contract reference.
`website/package-lock.json` pins the complete dependency graph. `npm ci` and
`npm run build` reproduce the checked-in 397 KB ESM bundle at
`static/vendor/livekit-client.2.15.4.mjs`; the page needs no external CDN request.
The bundle includes dependency license notices. esbuild and Playwright are exact
development dependencies, not runtime website services.

After the usual website/session-service/worker server-side configuration, use the
existing `orchestration/tools/demo_up.py --integrated` launch instructions. Keep
website and session API on the same hostname so the HttpOnly shopping cookie is
available. Set `ORCHESTRATION_BASE_URL` on the website and the matching allowed
Origin/website authority URL on the session service as described in Phase 3.
Do not put provider/API secrets in browser code.

The existing panel offers explicit typed and voice start buttons. Typed start
never requests a microphone. Voice start requests audio permission after the user
clicks. Start prepares tokens, connects both seats, registers application RPCs,
publishes rendered current context, checks playback, signals readiness and waits
for the authenticated worker activation. Only then does the browser send the
selected mode and enable Send. An early SDK "listening" event cannot bypass this
gate. No automatic opening prompt or spoken mode chooser is implemented here.

Both seat identities/roles/session/generation attributes must match the service's
binding. Tokens remain in memory. The app seat subscribes to no media; the user
seat attaches only the bound agent's audio, once per track SID. Typed mode attaches
no audio. End/disconnect stops tracks and detaches audio before remote cleanup.
A remote audio playback rejection also stops local assistance, preventing a
continued voice lane whose responses cannot be heard.

## Shared action, render and context order

`application.mjs` owns serialized requests, correlation, revisions, pending action
records and rendering. The website's owner-scoped v2 API remains the sole authority.
The bridge registers the actual worker's versioned methods:

| RPC | Behavior |
|---|---|
| `foodease.action.v2` | Verify bound agent caller, forward the original full action envelope, render the authoritative outcome, publish context, return the correlated result |
| `foodease.action_status.v2` | Verify caller/session/lookup correlation, fetch the retained original result; never submit an action |
| `foodease.present_summary.v2` | Verify the current reviewed summary/hash, render its exact text, wait across a paint boundary and acknowledge only a still-visible/current connected view |

The plan's unversioned `foodease.action` wording is interpreted through Phase 1's
frozen v2 channels and Phase 4's actual adapter. No legacy v1 substitution or new
business operation is introduced. All thirteen operations retain their meaning.

Manual commands construct envelopes at their actual queue admission revision.
Agent requests retain their original IDs/revision; the browser never silently
rebases them. Explicit diagnostic replays preserve their original envelope and
cannot change arguments under the same action ID. Wrong sessions, operations,
callers and regressive/uncorrelated replies cannot change the view as successes.

The renderer derives visible IDs, filters, search, selection, dialogs and cart from
the snapshot. Display-only search/filter calculations no longer compete with the
backend. The budget includes exactly 800 PKR; the label says "800 or less".
Availability is represented by the supported semantic `available` filter tag;
backend visibility, result counts and browser cards agree. Results remain bounded
to the contract's 25 visible rows; search can find other catalog items.

Menu/cart/category anchors use semantic navigation/filter operations. Closing
item/checkout dialogs, including Escape, updates authoritative navigation. The
optional AR view remains a visual preview. Item/hero selection is painted only
after the selection operation succeeds. Cart edits during checkout refresh its
visible quantities/total and invalidate the previous confirmation token.

Only newer context can replace a newer view. An old action result cannot repaint
its old state over a current snapshot. Context publication follows completed
rendering and carries the originating turn ID. Reconnect refreshes and republishes
current context even when its revision has not changed. Mirrored data never
executes an action; execution happens only through the action RPC/API lane.

## Unknown outcomes and receipts

Loss of a response after submission triggers a read-only lookup of the same action
ID. There is no automatic write retry, including after `not_seen`. Unresolved
actions block subsequent mutations. A minimal pending identity/envelope record
survives reload in sessionStorage when storage is available; checkout tokens are
removed from that persisted record. "Check pending changes" reconciles retained
results and refreshes the view without resubmitting. Blocked storage falls back to
memory-only ownership, consistent with the existing session transport.

A verified outcome whose rendering or context publication fails also remains
pending until read-only recovery restores the visible view. Recovery never rolls
back the business write or sends it again, and it clears ownership only after
successful rendering/publication.

Successful demo submission renders only the verified receipt. The browser retains
its action ID and can retrieve the original current-session receipt after reload.
This is read-only recovery, not a second order. The domain's existing process-local
retention, expiry and capacity limits still apply; browser storage is not durable
application authority or cross-process recovery.

## Worker input and output

The browser sends `app.text_input` on `foodease.text_input.v2`, with fresh turn/event
identities and the current revision. Controls use `foodease.control.v2` and the
bound user seat. Draft text is retained if delivery fails. Typed requests enter
the actual worker's existing commit/policy/SDK LLM/tool path; there is no browser
RulePlanner or parallel conversation engine.

The chosen display transport is the frozen `foodease.events.v2` channel. The
worker mirrors status, speech transcription and assistant captions through its
adapter. Native SDK caption events are deliberately not displayed again. Audio
remains native LiveKit audio; browser speech synthesis is not added.

Assistant rows have stable turn/utterance IDs. Partial updates replace text in the
same row; completed/interrupted rows reject late partials. Final caption text and
interruption come from the public SDK speech handle's actual completion/chat items,
not an assumed full intended reply. Missing STT message IDs use a product identity
shared across that utterance's partial/final events, without invented confidence.

Text updates do not recreate the input form or move focus. During typed assistance,
the existing transcript/form move into the active dialog's existing styled content
shell so the modal focus trap cannot strand typed follow-ups or checkout consent.
Their original DOM positions are restored when returning to the page. A long
verified demo receipt ID wraps instead of being clipped; there is no style redesign.

Typed summary receipts check the exact app summary revision/hash and current view,
not merely successful network publication. The worker still owns consent and
consumes it before submission. Manual changes invalidate stale approval. Missing,
hidden, stale or mismatched presentation cannot authorize a demo order.

## Verification and live boundary

From `website/`, use `npm test` for transport/model/lifecycle checks and
`npm run test:browser` for the disposable browser fixture. First run:

```powershell
cd voice-agent
uv sync --locked
cd ../website
npm ci
npx playwright install chromium
npm run build
npm run test:browser
```

The website is a **development-only** dependency of the voice-agent test environment
so one locked Python 3.12 environment can run real FastAPI/domain and LiveKit SDK
tests together. The production voice dependency group does not import the website.
The browser runner strips provider credentials, disables dotenv, directly owns its
temporary Python server and stops that exact process in `finally`.

The fixture uses real Chromium, the real website API/SessionStore, the production
browser bridge and the actual worker/SDK agent/session/tool path. RTC transport,
the assistance lifecycle service and the streaming LLM are local fakes; only SDK
RoomIO attachment is substituted because the fake room has no WebRTC tracks.
Fake audio tests prove attach/detach ownership, not audibility or real device stops.
The separately tested Phase 3 lifecycle service remains the production service.

The combined runner is `orchestration/.venv/Scripts/python.exe
orchestration/tools/phase5_verify.py` from the repository root. See Phase 5's
evidence report for commands, results, screenshots and inherited failures.
Actual Cloud signaling, provider speech, microphone capture, autoplay/device
behavior and conversational listening quality still require direct live testing.

SDK wiring was checked against the installed 2.15.4 `Room`/`LocalParticipant`/
event declarations and official
[Room](https://docs.livekit.io/reference/client-sdk-js/classes/Room.html),
[LocalParticipant](https://docs.livekit.io/reference/client-sdk-js/classes/LocalParticipant.html)
and [room event](https://docs.livekit.io/reference/client-sdk-js/enums/RoomEvent.html)
references. `Room.registerRpcMethod` is available in the pinned version and avoids
its deprecated LocalParticipant registration alias.
