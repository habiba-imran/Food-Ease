# Golden traces (add → set quantity → checkout)

Five curated traces for Zainab’s website / mock-agent harness.  
They show the **same shopping path** Habiba’s agent already exercises against MockApp.

| # | File | What it shows | Source |
|---|---|---|---|
| 01 | `01-wire-flow-add-set-qty-checkout.json` | Full **wire** exchange: `cart.add_item` → `cart.set_quantity` → `checkout.get_summary` → `checkout.submit_demo_order` with correlated `action_id`s | Built from `contract/v1/examples/` |
| 02 | `02-spoken-happy-path.md` | Full **spoken** order + quantity correction + demo checkout | `handover/SAMPLE_DIALOGUE.md` |
| 03 | `03-filter-then-select.txt` | Filter vegetarian under 800, then select “the second one” | `evidence/phase-10/traces/t05.txt` + `t06.txt` |
| 04 | `04-set-quantity.txt` | Absolute quantity set to 1 (not incremental add) | `evidence/phase-10/traces/t07.txt` |
| 05 | `05-checkout-confirm.txt` | Explicit yes → one simulated demo order | `evidence/phase-10/traces/t12.txt` (+ phase-4 `t12.txt`) |

**How to use**

1. Implement the 13 ops so that injecting **01** against your domain API produces the same statuses / cart totals (plus your service fee rules if you adopt the seed fee).
2. Your assistance panel / mock harness should be able to display **02**–**05** as user/assistant turns without inventing a second cart.
3. After LiveKit wiring, re-run the same scenarios end-to-end with Habiba’s worker.
4. Tick joint IR-01…IR-05 Live column — see `../handover/JOINT_ACCEPTANCE.md`.

Item IDs and prices must match `../catalog-seed.json` unless jointly replaced.
