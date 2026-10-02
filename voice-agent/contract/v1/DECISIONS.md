# Contract v1.0 — Habiba defaults (where SPEC is silent)

These are marked `x-habiba-default` in `schemas/transport_defaults.json`.
Zainab can differ on the wire; translation belongs in `LiveKitRpcAdapter`, not conversation logic.

## Transport

| Concern | Default |
|---|---|
| Agent → app actions | LiveKit **RPC** method `foodease.action`; **result = RPC response** (`app.action_result` shape) |
| Context snapshot / updates | Data topic `foodease.context` (reliable) carrying envelope events `app.context_snapshot` / `app.context_updated` |
| App control | Topic `foodease.control` |
| Typed text input | RPC method `foodease.text_input` → `app.text_input` |
| Transcripts / agent state | LiveKit native mechanisms, **mirrored** as envelope events for the contract surface |
| Max payload | **15360 bytes** (15 KiB) conservative default |

## Optional fields

- `confirmation_token`: optional on `checkout.get_summary` success and `checkout.submit_demo_order` request. Agent confirmation machine still binds to summary hash + cart revision when token is absent.
- `turn_id` / `context_revision`: nullable on envelopes where not applicable.

## IDs and quantities

- `item_id` pattern: `^[a-z][a-z0-9_\-]{1,63}$`
- `quantity`: integer **1..99**
- `visible_items`: max **25** rows per snapshot
