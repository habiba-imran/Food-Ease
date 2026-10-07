# Open decisions — defaults we will keep unless Zainab objects

**Pack note (Habiba → Zainab):** These are Habiba’s frozen defaults for the joint integration.
**They apply as written unless you object at integration time.**  
Changing a default = contract minor bump and/or `LiveKitRpcAdapter` translation — **not** a rewrite of the voice conversation engine.

Source of truth in Habiba’s repo: `voice-agent/docs/handover/OPEN_DECISIONS.md` (this file is a pack copy with keep-unless-object framing).

| ID | Topic | Default we keep unless you object | Notes |
|---|---|---|---|
| L1 | Action transport | LiveKit RPC `foodease.action`; result = RPC response | See `contract/v1/schemas/transport_defaults.json` |
| L2 | Context updates | Data topic `foodease.context` | App publishes after every revision bump |
| L3 | Control (mute/pause/end) | Data topic `foodease.control` | App → agent |
| L4 | Typed input | RPC `foodease.text_input` **or** envelope `app.text_input` on data | Both accepted in Habiba’s stack; prefer **one** in production |
| L5 | Transcripts / agent state | LiveKit native streams, mirrored as envelope events | UI may listen to either |
| L6 | App participant discovery | Attribute `foodease.role=app`, else first non-agent | |
| L7 | Max payload | 15360 bytes | Raise only after measuring installed LiveKit |
| L8 | `confirmation_token` | **Optional** on summary result + submit | If omitted, explicit spoken/UI yes + revision still required |
| L9 | Mute ownership | Client mic mute owned by browser; app control is additive | Mic mute ≠ cancel in-flight mutation |
| L10 | Speed preference | Agent acknowledges; TTS speed applied when API supports it | If unsupported: say so honestly |
| L11 | Volume preference | Not claimed as TTS volume; optional frontend honor later | No fake “volume changed” without UI support |
| L12 | Results-list identification | Soft refs (“second one”) via agent resolver + presented list | App should still send stable `item_id`s in `visible_items` |
| L13 | Topic / method names | `foodease.*` prefix as above | Rename only via adapter mapping |
| L14 | Contract review | v1.0 frozen in `contract/v1/` | Feedback → v1.1 via adapter, not brain rewrite |
| L15 | Post-handover conformance | Run Habiba’s adapter conformance suite against your ops | Task 11.8 when your adapter is ready |
| L16 | Urdu / multilingual | English demo only | Stretch; not promised |
| L17 | LiveKit Inference vs own keys | Own keys in `.env` for this project | Billing/limits live in Habiba’s `docs/provider-limits.md` |
| L18 | Session / token mint | Habiba-owned `orchestration/` service (`POST /v1/session` + `/v1/assist/*`) | Browser never sees LiveKit API secrets; see `SESSION_API.md`. Transport L1–L6 unchanged. |
| L19 | Room topology | Three seats: user + app (`foodease.role=app`) + agent in one room | Habiba rehearses with MockApp `--livekit`; Zainab replaces only the app seat (`TOPOLOGY.md`). |
| L20 | Joint IR suite | IR-01…IR-05 (stale, dup action_id, checkout confirm, mic→manual, cart invalidates confirm) | Auto column passes on MockApp; Live column = your adapter — see `JOINT_ACCEPTANCE.md`. |

**Also keep unless jointly changed:**

- Exact **13 operation strings** in `contract/v1` (do not rename).
- Catalog **`item_id`s** in `../catalog-seed.json` (or jointly lock a replacement seed before either side hard-codes a second menu).
- Result statuses: `success`, `failed`, `rejected`, `stale_context`, `requires_confirmation`, `timeout_unknown`.

**Phrase for PRs / meetings:** “default applies unless changed at integration.”
