# Open decisions ([LATER])

Each item has a **Habiba default**. Default applies unless changed at integration with Zainab. Changing a default = contract minor bump and/or `LiveKitRpcAdapter` translation — **not** a rewrite of the conversation engine.

| ID | Topic | Habiba default | Notes |
|---|---|---|---|
| L1 | Action transport | LiveKit RPC `foodease.action`; result = RPC response | See `transport_defaults.json` |
| L2 | Context updates | Data topic `foodease.context` | App publishes after every revision bump |
| L3 | Control (mute/pause/end) | Data topic `foodease.control` | App → agent |
| L4 | Typed input | RPC `foodease.text_input` **or** envelope `app.text_input` on data | Both accepted in stack; prefer one in production |
| L5 | Transcripts / agent state | LiveKit native streams, mirrored as envelope events | UI may listen to either |
| L6 | App participant discovery | Attribute `foodease.role=app`, else first non-agent | |
| L7 | Max payload | 15360 bytes | Raise only after measuring installed LiveKit |
| L8 | `confirmation_token` | **Optional** on summary result + submit | If omitted, explicit spoken yes + revision still required |
| L9 | Mute ownership | Client mic mute owned by browser; app control is additive | Mic mute ≠ cancel in-flight mutation (R5) |
| L10 | Speed preference | Agent acknowledges; TTS speed applied when API supports it | If unsupported: say so honestly (ADR-0006) |
| L11 | Volume preference | Not claimed as TTS volume; optional frontend honor later | Default: no fake “volume changed” without UI support |
| L12 | Results-list identification | Soft refs (“second one”) via agent `ReferenceResolver` + presented list | App may also send stable `item_id`s in `visible_items` |
| L13 | Topic / method names | `foodease.*` prefix as above | Rename only via adapter mapping |
| L14 | Contract review | v1.0 frozen in `contract/v1/` | Zainab feedback → v1.1 via adapter, not brain rewrite |
| L15 | Post-handover conformance | Run suite against Zainab adapter when ready | Plan task 11.8; outside this handover tag |
| L16 | Urdu / multilingual | English demo only | Stretch; not promised |
| L17 | LiveKit Inference vs own keys | Own keys in `.env` for this project | Billing/limits: see `docs/provider-limits.md` |
| L18 | Session / token mint | Habiba-owned `orchestration/` service (`POST /v1/session` + `/v1/assist/*`) | Browser never sees LiveKit API secrets; see `zainab-pack/handover/SESSION_API.md`. Transport L1–L6 unchanged. |
| L19 | Room topology | Three seats: user + app (`foodease.role=app`) + agent in one room | Rehearse with MockApp `--livekit` + `FOODEASE_APP_TRANSPORT=livekit`; Zainab replaces only the app seat. |
| L20 | Joint IR suite | IR-01…IR-05 (stale, dup action_id, checkout confirm, mic→manual, cart invalidates confirm) | Auto on MockApp; Live = Zainab adapter — `zainab-pack/handover/JOINT_ACCEPTANCE.md`. |

**Phrase for PRs:** “default applies unless changed at integration.”
