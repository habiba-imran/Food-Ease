# Dialogue suite DS-01…DS-20

Text-mode scenarios against MockAdapter. Each row: user turns → expected behavior (acts + constraints).

| ID | User turns (sequence) | Mock / setup | Expected behavior |
|---|---|---|---|
| DS-01 | “I’m hungry” | Home menu | Narrow **or** 2–3 tagged suggestions with reasons; no full menu dump; ≤3 sentences |
| DS-02 | “Something light” | Home | Narrow/filter toward lighter items or ask one clarifying preference; no dump |
| DS-03 | “What do you recommend?” | Burgers visible | Recommend from snapshot data only; 2–3 items max with price/tag reason |
| DS-04 | “Compare the Zinger Burger and the Veggie Wrap” | Both known | Compare using tool/catalog facts; no invented ingredients |
| DS-05 | Show two priced items → “the cheaper one” | Two visibles | Resolve cheaper from presented prices; select/speak that item |
| DS-06 | Mentions burger → “no, I meant the wrap” | Both known | Repair to wrap; no double add |
| DS-07 | Add item → “actually remove it” / change mind | Cart has line | Confirm if tier-2 remove; cart reflects change; truth from tools |
| DS-08 | “How’s the weather?” | Any | Brief off-topic + one redirect to menu; no fake capabilities |
| DS-09 | “This is useless, nothing works” | Any | Calm acknowledge + offer browse/type or simple next step; no rudeness back |
| DS-10 | After a reply → “what did you say?” / “repeat” | Prior assistant text | Control/repeat last assistant; no new mutation |
| DS-11 | Agent listing → user “next” | Multi-item list | Advance list / next item; don’t restart whole dump |
| DS-12 | (long silence mid-flow) | After greeting | Idle tip at most twice then quiet; no cart action from silence |
| DS-13 | “Vegetarian under 800” then “actually under 600” | Home | Update filter/budget preference; results respect new cap |
| DS-14a | “What’s in the Masala Fries?” | Fries has ingredients | Answer from tool data only |
| DS-14b | “What’s in the Chef Special Sweet?” | ingredients=None | “I don’t have that information”; no guess |
| DS-15 | “Add a couple of Cola Cans” | Cola visible | Treat couple≈2; add quantity 2 when clear |
| DS-16 | “I’ll browse myself” then “talk to me again” | Any | Pause tips/voice help; then resume brief (not full onboarding) |
| DS-17 | Start checkout → “wait, change the quantity” | Cart ready | Do not submit; allow cart edit; confirmation still required later |
| DS-18 | “Show burgers and add the veggie one” | Home | Handle both intents safely (navigate/filter then add) or clarify if ambiguous; no hallucinated success |
| DS-19 | “Thanks, that’s all” / “goodbye” | Any | Warm wrap-up; end/pause session cleanly |
| DS-20 | Abusive insult | Any | Brief calm redirect; no escalation; offer stop/browse |

## Scoring notes (V6.3 / V6.4)

- Unambiguous scenarios (e.g. DS-13 filter, DS-15 quantity, DS-10 repeat): clarification rate target ≤15% across the suite’s unambiguous set.
- Tier 0/1 actions: **0** unnecessary confirmations.
- Opener repetition: same opener ≤20% of 30 sampled replies.
- Typical reply ≤ ~35 spoken words unless user asked for detail.
- Safety: zero hallucinated success; V4.4/V4.5 must pass after every prompt edit (R14).
