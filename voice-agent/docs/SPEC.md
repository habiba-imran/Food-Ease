# VOICE AGENT — REQUIREMENTS & FINAL DELIVERABLES

**Project:** Accessible Multimodal Food Ordering Website (working name: *FoodEase*)  
**Document owner / voice agent:** Habiba  
**UI/UX counterpart:** Zainab  
**Shared responsibility:** Final orchestration and end-to-end integration  
**Specification version:** 1.0 | **Date:** 01 October 2026  
**Document type:** Requirements and acceptance specification — **not an implementation plan**

---

## 1. The product Habiba is contributing to

The team is building an HCI-focused food-ordering website that works through a conventional graphical interface **and** an optional, conversational accessibility interface. The primary intended persona is someone who is blind or has low vision; other users may freely choose the voice assistant. Users must not have to identify or disclose a disability. The website will also expose equivalent text-based interactions; speech is not the sole route to complete a task.

The voice assistant must be capable of **understanding natural language, explaining the current interface, suggesting relevant next actions, issuing structured requests to the website, acknowledging verified results, and gracefully recovering from mistakes**. It must feel like a cooperative guide, not a voice recording that reads every button aloud.

**Illustrative journey:** A person opts into voice guidance → assistant proactively welcomes them → person asks for spicy food below Rs. 1,000 → assistant requests filtering using actual catalog data → describes a small number of matches → person chooses the second item → assistant requests opening it → person says “add two” → cart is updated by the application → assistant announces the confirmed new total → person changes their mind → system updates the quantity → assistant summarizes the cart before checkout.

**Fundamental design invariant:** The **application/orchestration layer owns factual state and executes domain actions**. The voice agent owns conversation, speech processing, intent interpretation, and structured action requests. It must never imply that an order, navigation, or cart update succeeded merely because the language model generated words claiming success.

---

## 2. Scope and boundaries

### Habiba owns

- A reusable LiveKit-based real-time voice-agent service, usable against a **mock application adapter** before the final website exists.
- Spoken onboarding; proactive-but-respectful interaction; turn-taking; STT; conversational reasoning; expressive TTS; interruption/cancellation; silence and recovery behaviors.
- The agent's requirements-compliant instruction/policy and the domain intent/action **interface contract**, exposed independently of UI implementation details.
- Bidirectional state, control, transcription and action-result communication needed by the shared orchestration layer.
- Repeatable demonstrations and evidence against the acceptance criteria in this document.

### Habiba does not own

- Page layout, Figma screens, React components, styling, graphical navigation, cart calculations, product inventory, payment processing, authentication, or persistence.
- DOM clicking by browser coordinates/selectors. The agent requests **semantic actions** (e.g., `cart.set_quantity`), not arbitrary clicks.
- Independent decisions on final checkout, prices, stock, item identity, or delivery details. These are verified by the application.

### Agreed demonstration scope

A realistic but **mock-data** food-ordering workflow is sufficient. Orders are **simulated**, not charged, and the agent must explicitly distinguish demonstration checkout from an actual purchase. A database is **not required** for the voice-agent deliverable.

---

## 3. Required provider and capability profile

| Layer | Requirement | Constraints / expected capability |
|---|---|---|
| Real-time conversation | **LiveKit Agents** | Browser-accessible room/session, streamed audio, agent state, transcripts, interruptions, and structured frontend/agent communication. |
| STT | **Deepgram** | Streaming transcripts and end-of-turn detection; preserve interim/final distinction; correctly recognize common food terms, prices and quantities. **Flux English** is a preferred evaluation candidate for conversational turn-taking; **Nova-3** is an alternative when vocabulary/language accuracy warrants it. |
| LLM | **A low-latency tool/function-calling text model with accessible free tier or student trial** | Preferred first candidate: **Google Gemini 3.1 Flash-Lite** (stable, function-calling, structured output; verify actual account eligibility/quotas). Habiba may substitute a demonstrably better accessible model. The app interface must **not depend on a particular LLM vendor**. |
| TTS | **Cartesia** | Low-latency streaming and naturally paced, expressive speech. **Sonic 3.6** is the first candidate to evaluate. Voice selection must be comfortable, clear, consistent and intelligible rather than overly dramatic. |
| Turn/interruption | LiveKit-compatible VAD and turn detection | Detect meaningful user interruptions without frequently cutting off natural pauses or short acknowledgements; reconcile interrupted speech and any in-flight action. |

**Provider constraints:** Record the *actual* model identifiers, SDK versions, selected voice, known quotas and any trial limitations in the handover. No hard-coded secret in source or browser. No guarantee that a provider's free tier lasts for the whole project. Free-tier model providers may have distinct data-use terms; use fabricated demo data and assess those terms before sending personal information.

**Primary demo language:** English, with support for common Pakistani food names, natural variations in accent, and prices expressed in PKR. Urdu/English bilingual speech is a **stretch**, not a core promise: Cartesia Sonic 3.6 supports Urdu synthesis, while the selected STT/turn model must also independently support the required language and be tested. Do not promise multilingual behavior based on TTS support alone.

---

## 4. Mandatory conversational experience

Requirements labeled **MUST** are acceptance conditions. **SHOULD** items are quality goals. **STRETCH** items are optional and must not compromise core behavior.

### VA-01 — Explicit activation and immediate welcome (MUST)

- Voice begins **only after** the person explicitly chooses voice guidance, appropriate browser audio/microphone permissions are available, and the session is ready.
- The agent **initiates the first greeting without waiting for the user to speak**. A cold start cannot require “Hello?” from the user.
- Suggested content, not a fixed script: “Welcome. I can help you explore the menu and place a demo order. You can interrupt me, say ‘go back,’ or browse normally at any point. Would you like to browse categories or tell me what you feel like eating?”
- The greeting must be short, spoken naturally and **interruptible from its first audible moment**.
- On a return to voice mode during the same session, offer a **brief resume**, not the whole onboarding again.
- Do not start listening or autoplaying sound before consent, and do not claim that a refused microphone permission is user speech.

### VA-02 — Useful even when the user is silent (MUST)

- A user may be silent, unfamiliar with voice assistants, or unsure what to say. After the initial invitation, the assistant remains visibly/audibly ready and can **offer one brief contextual example** after a configurable idle interval (initial product target: ~10–15 seconds).
- It may offer a **second, different and brief** help prompt after a longer interval (~25–35 seconds), then enters a **quiet listening/idle state**. It must not repeat prompts endlessly, interpret silence as consent, or invent a purchase.
- Prompts must be context-aware: on the menu suggest browsing/searching; on an item page suggest details/add/back; in cart suggest review/edit/checkout.
- Any actual user utterance, manual UI operation, text input, mute, stop request, disconnection, or active screen-reader reading cancels irrelevant pending prompts. Where screen-reader activity cannot be detected reliably, the user still has an accessible **Pause tips** option.
- A prompt must not speak over a user who has begun speaking. Silence does not justify an unsolicited cart action.

### VA-03 — True barge-in and turn-taking (MUST)

- A user can interrupt **the greeting, a long description, a clarification, or a normal reply** with “stop,” “next,” “actually…”, etc.
- On a valid interruption, the currently audible output stops promptly; queued old audio and irrelevant response text must not continue playing after the user's correction.
- Detect normal hesitations and short thinking pauses without consistently stealing the user's turn. Avoid treating background voices, speaker echo and mere “mm-hmm” as definite requests.
- The agent must handle **false interruptions** sensibly (resume only when relevant) and avoid repeating an entire already-heard paragraph.
- An interruption of **speech** is not automatically a rollback of an **application mutation**. The agent must query/reconcile the action's actual result before speaking about its status; no duplicate order or add-to-cart requests.
- It must recover gracefully from quick successive commands and from a user correcting the assistant mid-sentence.

### VA-04 — Humanized speech and dialogue (MUST)

- Sound approachable, respectful and concise, like a patient shopping guide; do not imitate a human identity or claim to be a person.
- Use context-sensitive phrasing, varied but restrained acknowledgments, comfortable pauses, natural pacing and suitable intonation. **Do not inject fake stutters or repeated fillers to manufacture humanness.**
- Prefer 1–3 short spoken sentences per response, expanding only at user request or for essential confirmation. Avoid reading exhaustive lists, raw JSON, IDs, URLs, code or internal status names.
- Announce small result sets in a navigable way, e.g., “I found four options. The first is … Want the next one?” Include item position and total where it improves orientation.
- Pronounce brand/product names, quantities, PKR amounts and menu modifiers clearly; test ambiguous numbers such as “one fifty” versus “one thousand five hundred.”
- The user can request **repeat, slower/faster speech, quieter/louder playback** (where supported), more detail, less detail, and speech pause/resume. Honor preference changes in the session.
- A synthetic “thinking…” filler must not hide a stalled system or make the agent appear faster without real progress. Brief truthful processing feedback is acceptable on longer waits.

### VA-05 — Context and orientation (MUST)

- Understand deictic references in context: “the second one,” “add that,” “make it two,” “go back there,” “what's in my cart?”
- **Never guess a referent** after the visual selection/page state has changed or multiple items are equally plausible. Ask a concise clarification.
- Answer “Where am I?”, “What can I do here?”, “What's selected?”, “What changed?”, and “How do I go back?” using the **latest confirmed UI/application snapshot**, not the model's imagined page.
- Explain available actions using **progressive disclosure**, not a linear reading of every header, link or button.
- Preserve relevant session-level conversational preferences (e.g., vegetarian, budget) only while the user wants them; allow “clear that preference.”
- If the person operates the GUI during voice mode, the assistant must absorb the **new application context** and not continue to describe a previous page/product.

### VA-06 — Domain behavior and safe actions (MUST)

The assistant must understand natural equivalents of the following **semantic intent families**; exact product/currency values are supplied by the application.

| Family | Required examples | Expected agent behavior |
|---|---|---|
| Orientation | “Where am I?”, “What can I do?” | Speak current confirmed location and a few useful options. |
| Navigation | “Open burgers”, “Go home”, “Go back”, “Next item” | Request semantic navigation/selection, then announce confirmed result. |
| Discover/filter | “Vegetarian under 800”, “Something spicy”, “Show desserts” | Request structured filters; report only returned actual matches. |
| Item details | “What's in this?”, “How much?”, “Tell me more” | Use actual item detail: name, price, available description, ingredients/options when provided. |
| Cart operations | “Add two”, “Remove the wrap”, “Make that one” | Resolve item and quantity; issue approved action; announce verified cart state. |
| Cart review | “What's my total?”, “Read my cart” | Summarize authoritative cart data and fees as returned. |
| Checkout | “Checkout”, “Place my order” | Read order summary; require explicit confirmation; execute **simulated** order only following confirmation and valid orchestration authorization. |
| Assistance | “Repeat”, “Slower”, “Stop”, “Undo”, “Help” | Fulfill universal control or request safe, reversible app action. |
| Modality | “I'll do it myself”, “Switch to typing” | Pause/exit speech and signal UI to offer standard/text interaction without discarding confirmed cart state. |

**Critical rules:**

1. Prices, totals, taxes/fees, menu choices, stock, ingredients and order status are **tool/application facts**, never generated from memory or invented by the LLM.
2. The agent must not directly alter website business state outside the authorized orchestration interface.
3. Item-changing actions must be unambiguous; clarification is required if “that” or an item name resolves to several choices.
4. Explicit **confirmation is required before simulated checkout** and before destructive actions whose scope is ambiguous. Read the total and selected items first. No confirmation by silence.
5. A user correction (“no, one instead of two”) applies to the **latest verified state**. “Undo” applies only when a valid reversible last action exists; otherwise explain what can be edited.
6. If an action fails or times out, say so plainly. Do not claim success, and do not blindly repeat the mutation.
7. Stay within shopping assistance. Off-topic small talk can receive a brief response and a gentle invitation back to the task; never fabricate functions the application lacks.

---

## 5. Voice-agent state and synchronization requirements

The team needs two state views: (a) the **conversation/audio lifecycle**, and (b) the **authoritative shopping/application context**. They are related but not interchangeable.

### VA-07 — Exposed conversation/audio states (MUST)

At minimum the frontend/orchestrator must be able to distinguish:

`off/awaiting_consent` · `connecting` · `ready/listening` · `user_speaking` · `thinking` · `assistant_speaking` · `waiting_for_action_result` · `idle` · `muted/paused` · `reconnecting` · `error` · `ended`.

These are **product-level UI meanings**; Habiba may map LiveKit's native agent states/events to them. Transitions should be observable, and a fatal error must not leave the UI incorrectly displaying “listening.”

### VA-08 — Text parity (MUST)

- Send interim/final **user speech transcriptions** with clear status; the final user utterance must replace, not duplicate, interim text.
- Send assistant text matching the speech the user actually receives. Interrupted, never-heard continuation must not be presented as something already spoken.
- The same high-level interaction must be possible with **typed input**; typed input can enter the conversational interpretation layer without spoofing microphone audio.
- Agent audio may be muted or absent while captions/transcripts and approved action requests remain available, subject to the user's selected interaction mode.
- Expose enough state to drive visual listening/thinking/speaking feedback and accessible text announcements.

### VA-09 — Browser/application context subscription (MUST)

The agent receives a current, structured context snapshot at session start and context updates after relevant manual/agent-driven UI changes. Required conceptual fields:

- Schema version, `session_id`, monotonically increasing `revision`, current route/page/section, focus/selected item when known.
- Valid current actions and navigation targets **by semantic ID**, plus concise accessible labels.
- Filter/search state and a bounded list of visible catalog items (`item_id`, display name, factual price/currency, descriptors/availability when supplied).
- Cart summary and item quantities, current total/fee breakdown when available.
- Whether checkout is available, whether an action is pending, language and spoken-feedback preferences.

The agent must not treat a stale context revision as current. It may request a refreshed context before a consequential action. Large catalog dumps are **not** required to be placed in the model prompt.

---

## 6. Agent ↔ orchestration interface contract

**This section specifies the required externally observable interface, not how to code it.** Names below are a proposed **version 1 shared contract**; Habiba and Zainab must freeze any adjustments together before final integration. Transport may use LiveKit's supported state synchronization, transcriptions/text streams, RPC and/or data messages; the frontend should not need to know Cartesia/Deepgram/Gemini internals.

### VA-10 — Shared event envelope (MUST)

Every application-level request/event must carry sufficient metadata to be traceable and safely deduplicated:

- `schema_version`: e.g., `1.0`;
- `session_id`: current voice/session identity;
- `event_id`: unique message ID;
- `turn_id`: conversational turn identity where applicable;
- `timestamp`: consistent machine-readable time;
- `context_revision`: the app snapshot on which the request was based (when applicable);
- `type`: one of the agreed event types;
- `payload`: typed data for that event.

Action requests additionally require a **unique `action_id` / idempotency key** so a reconnect or retry cannot inadvertently create a duplicate cart/order mutation.

### VA-11 — Required outgoing agent events (MUST)

| Event | What it communicates |
|---|---|
| `agent.status` | Agent lifecycle, ready/error and listening/speaking/thinking status. |
| `transcript.user.partial` / `transcript.user.final` | Recognized words and final utterance with `turn_id`. |
| `transcript.assistant` | Assistant text, with started/updated/completed/interrupted indication. |
| `agent.action_request` | A validated semantic operation request, arguments, current context revision and `action_id`. |
| `agent.clarification_required` | Clear question and constrained candidate choices when identity/action is ambiguous. |
| `agent.control` | Mute/pause/resume/end or switch-mode intent, as applicable. |
| `agent.error` | Recoverable/fatal reason in user-safe terms; no secrets or provider stack traces. |

### VA-12 — Required incoming application/orchestrator events (MUST)

| Event | What it communicates |
|---|---|
| `app.context_snapshot` | Initial authoritative page/catalog/cart snapshot. |
| `app.context_updated` | New versioned page/focus/search/cart context, including GUI-driven changes. |
| `app.action_result` | The success/failure/needs-confirmation result for a specific `action_id`, plus verified state/data or failure reason. |
| `app.control` | Start/pause/mute/unmute/end speech, request a brief explanation, or switch modality. |
| `app.text_input` | A typed user utterance supplied through the same conversational layer. |

### VA-13 — Allowed semantic action vocabulary (MUST)

The agent requests operations from a **small allowlist**; it must not produce arbitrary JavaScript, browser coordinates, or database writes.

`navigate` · `search_menu` · `filter_menu` · `select_item` · `get_item_details` · `get_cart` · `cart.add_item` · `cart.set_quantity` · `cart.remove_item` · `checkout.get_summary` · `checkout.submit_demo_order` · `undo_last_reversible_action` · `get_current_context`.

Generic navigation/action arguments must use the **application's IDs/field names** (e.g., `item_id`), not fragile natural-language label matching when exact IDs are available. The application may refuse any request that is disallowed, stale, ambiguous or out of scope.

### Contract illustration — *message shapes, not source code*

The following illustrative records define expected information flow. Actual transport method is jointly selectable.

**Agent requests an action:**

```json
{
  "schema_version": "1.0",
  "type": "agent.action_request",
  "session_id": "demo-session-7",
  "event_id": "event-42",
  "turn_id": "turn-15",
  "timestamp": "2026-10-01T13:18:00+05:00",
  "context_revision": 8,
  "payload": {
    "action_id": "action-123",
    "operation": "cart.set_quantity",
    "arguments": { "item_id": "wrap-hot-chicken", "quantity": 1 }
  }
}
```

**Application responds with authority:**

```json
{
  "schema_version": "1.0",
  "type": "app.action_result",
  "session_id": "demo-session-7",
  "event_id": "event-43",
  "turn_id": "turn-15",
  "timestamp": "2026-10-01T13:18:01+05:00",
  "context_revision": 9,
  "payload": {
    "action_id": "action-123",
    "status": "success",
    "verified_state": {
      "cart": [{ "item_id": "wrap-hot-chicken", "name": "Hot Chicken Wrap", "quantity": 1, "unit_price": 850 }],
      "currency": "PKR",
      "total": 850
    }
  }
}
```

Only **after** receiving this success may the agent say: “Changed to one Hot Chicken Wrap. Your current total is 850 rupees.” If the app returns `failed`, `rejected`, `stale_context`, `requires_confirmation`, or `timeout/unknown`, the spoken response must reflect that actual status. `Unknown` must **not** trigger automatic resubmission of a mutating action.

### VA-14 — Confirmation and interruption across the boundary (MUST)

- Confirmation question and user's explicit answer are tied to a **particular current summary/intent**, not a generic persistent “yes.” If the cart changes before checkout, the old confirmation expires.
- Pending app mutations survive interruption according to actual application status, not guessed speech completion. Speech cancellation and mutation cancellation are distinct concepts.
- Duplicate `action_id` values must not create duplicate effects; the application returns the prior operation outcome where supported.
- An action must be correlated with its result before the agent announces success; context revisions prevent a stale response from overwriting newer GUI activity.
- The agent must be able to recover/reconnect using the latest context rather than replaying uncertain actions.

---

## 7. Low-latency and audio-quality acceptance goals

These are **project performance targets**, not promises that a third-party vendor guarantees. Habiba must measure and report actual results, test conditions and limitations. Evaluate on a stated browser/device, stable broadband connection and account tier. Report at least **p50 and p95** from a meaningful sample (target: 30 ordinary turns plus 10 interruptions), separating initial/cold connection from warm conversation.

| Metric | Target | Start / stop measurement definition |
|---|---:|---|
| **Proactive first audible greeting, warm ready room** | p50 ≤ 0.8 s; p95 ≤ 1.5 s | Agent becomes ready → user actually hears first welcome audio. |
| **Cold join-to-first-audio** | p50 ≤ 2.0 s; p95 ≤ 4.0 s | After permitted session join starts → first audible greeting. Record browser autoplay/permission delays separately. |
| **Normal voice response / perceived TTFA** | p50 ≤ 1.2 s; p95 ≤ 2.5 s | User's actual speech ends → first meaningful assistant audio, not a fake filler cue. |
| **Barge-in playback stop** | p95 ≤ 350 ms where reliably measurable | Onset of detectable genuine user speech → old assistant audio stops at playback. |
| **Action feedback** | Immediate visible status; truthful speech after result | Request emitted → receipt/result UI; do not hide slow or rejected app calls. |
| **Conversation reliability** | ≥95% of scripted normal turns complete without manual restart | Over the agreed evaluation set, with failures counted and documented. |

**Quality requirements:**

- Prefer streamed processing throughout. Keep active connections/session resources ready while the user is in a consented voice session; avoid unnecessary repeated cold-start overhead.
- Balance rapid response with correct end-of-turn detection: do not cut off a user merely to meet a headline TTFA.
- Avoid clipping first/last syllables, overlapping two assistant replies, high jitter, audio echo and runaway queued speech.
- Measure the pipeline separately where available: speech endpointing/EOU, STT availability, LLM first token, TTS first byte and browser playback. End-to-end audible TTFA is the user-facing metric.
- Test on built-in laptop microphone, ordinary earphones and moderate household noise, not only in an ideal headset environment.
- If free-tier quotas or internet conditions prevent a target, report the observed value and dependency transparently; do not present simulated latency as measured real performance.

---

## 8. Accessibility, trust and privacy requirements

### VA-15 — Agency and inclusivity (MUST)

- Voice guidance must be **optional**, independently stoppable, and reversible to GUI/text browsing at any time without losing confirmed cart state.
- Never ask users to prove blindness or label their disability. Do not assume blind users cannot use a conventional screen reader or keyboard.
- Spoken details must not rely on “click the green one,” visual location alone, or color-only distinctions. Prefer semantic item/section names and option positions.
- Every assistant prompt and important result must have a corresponding accessible textual representation; do not force voice as the only way to answer a confirmation.
- When the microphone is muted/unavailable, there must be an explicit state and usable text/manual fallback.
- Do not speak over the user's explicit “stop,” “pause,” or preference to browse independently. 

### VA-16 — Trust, minimization and security (MUST)

- No raw LiveKit/provider secret, private token, billing key or system prompt is exposed to the browser or handed over in a submitted recording/document.
- Do not collect or retain recordings by default. Testing recordings/transcripts require participant consent, data minimization and appropriate deletion arrangements.
- Do not request or announce real payment-card data, passwords or sensitive information in the lab demo. Use fictional users, addresses and products.
- If personal details are later used, they must be requested only when necessary and read back selectively, never broadcast as a long unsolicited spoken monologue.
- User-provided speech and catalog content must be treated as **data**, not permission to override action boundaries or reveal internal instructions. The agent cannot execute an action outside the fixed allowlist.
- Tell the truth about the demo, the application status, prices returned by backend, uncertainty and unavailable capabilities.

---

## 9. Failure, cancellation and recovery requirements

### VA-17 — Recoverable situations (MUST)

| Situation | Required user-facing behavior |
|---|---|
| Mic permission declined | Do not simulate listening; clearly offer typed/normal browsing. |
| No user speech | Initial greeting and limited context-specific prompts; thereafter quiet listening. |
| Inaudible/low-confidence phrase | Briefly request repetition or offer a constrained choice; do not guess a consequential action. |
| Two matching items | Ask which of the two, with name/price or position. |
| Noise/false interruption | Avoid losing already-supplied context; resume appropriately if no real new request. |
| STT unavailable | Display recoverable error and offer typed input; never fabricate recognized text. |
| TTS unavailable | Retain accessible text response/status; allow retry or manual mode. |
| LLM unavailable / quota hit | State the issue plainly and preserve confirmed app state; do not claim an action occurred. |
| App action rejected | Explain the application's stated reason and provide a valid next option. |
| App action times out | Treat outcome as unknown, ask app to reconcile before any mutation retry. |
| Connection interruption | Show reconnecting/error; rejoin from latest authoritative context without duplicate checkout/cart operations. |
| User switches to GUI mid-turn | Cancel obsolete spoken guidance and align with new GUI selection/context. |
| User says “stop” during checkout | Stop speech; do not infer checkout consent or silently submit. If a submit request was already sent, reconcile authoritative outcome. |

---

## 10. Demonstration / acceptance scenarios

Habiba's deliverable is accepted only if the **agent behavior** below can be demonstrated against a mock app adapter, before the real visual website is connected. This is a behavior checklist, not a task schedule.

| Test ID | Given / user input | Observable pass condition |
|---|---|---|
| T01 | Opt into voice; say nothing. | Agent speaks the welcome by itself once ready. |
| T02 | Stay silent after the welcome. | Offers limited contextual help, then remains quiet/ready rather than looping. |
| T03 | Interrupt the greeting with “Show burgers.” | Greeting stops; a current `filter_menu`/navigation request is emitted. |
| T04 | Pause naturally while saying “I want… maybe a spicy… burger.” | Does not consistently cut off the unfinished thought. |
| T05 | Ask “Vegetarian under eight hundred.” | Valid structured filter request; speaks results supplied by mock app. |
| T06 | After listing results say “the second one.” | Uses the correct current result ID and requests item selection. |
| T07 | Say “Add two” then “actually make it one.” | Correct confirmed quantity=1, with no duplicate mutations. |
| T08 | Return a failed add-to-cart result. | Assistant does not announce that the item was added. |
| T09 | Ask “Where am I?” after GUI navigates manually. | Describes the current new page, not stale conversation memory. |
| T10 | Say “Stop”, “Repeat”, “Go back”, and “Slower.” | Controls work in the applicable states without an unrelated LLM hallucination. |
| T11 | Ask to checkout; remain silent when asked to confirm. | No order submitted. |
| T12 | Explicitly confirm current checkout summary. | Only one authorized **demo** submission; speaks actual returned result. |
| T13 | Interrupt checkout confirmation with a cart change. | Earlier confirmation invalidated; revised summary requested. |
| T14 | Simulate a delayed/unknown action result. | Does not duplicate the action or falsely report success. |
| T15 | Deny microphone permission or mute audio. | Text/normal browsing fallback, honest status. |
| T16 | Type a menu request instead of speaking. | Same interpretation/action route works without microphone input. |
| T17 | Cause Deepgram/LLM/TTS provider failure. | Graceful recoverable feedback where feasible; no misleading UI state. |
| T18 | Speak with common regional pronunciation/noisy mic. | Recognition limitations logged; consequential uncertainty clarified. |
| T19 | Say “I'll browse myself.” | Stops unsolicited voice guidance; confirmed app/cart state remains intact. |
| T20 | Interrupt while a cart mutation is in flight. | Audio stops; final cart status is reconciled via matching action ID/result. |

**Performance evidence** additionally covers the targets defined in §7; record both successful and failed tests.

---

## 11. Final deliverables Habiba must hand over to Zainab

This is the definitive **output checklist**. The handoff must let Zainab connect the voice agent without reverse-engineering the bot or depending on undocumented hard-coded menu data.

1. **Working standalone voice-agent service** — accessible in a test LiveKit session and usable without the final website, connected to a mock catalog/cart/application adapter. Demonstrates proactive greeting, real speech input/output, silence handling, interruptions and action requests/results.
2. **Full agent source project** — readable code and dependency/version manifest, with provider integrations and business-action adapter visibly separated. Do **not** include actual API keys or raw user recordings.
3. **Safe configuration template** — `.env.example` (placeholder variables only); identifies LiveKit, Deepgram, Cartesia and selected LLM credentials/configuration, chosen model IDs and voice ID, relevant rate/trial assumptions. This describes necessary settings; it is not a tutorial.
4. **Frozen integration contract** — versioned document or schema covering the event envelope, incoming/outgoing events, tool/action names, required and optional fields, type/value constraints, action-result statuses, error semantics, confirmation, `action_id`, state revisions, idempotency and cancellation. Include small sample event exchanges.
5. **Mock adapter and deterministic test data** — enough fake pages/menu/cart data and controllable action results (success, rejected, delayed, unknown) to demonstrate the contract before the real UI exists. No real backend/database dependency.
6. **Agent behavior/prompt specification** — instructions actually governing greeting, conversational tone, domain scope, proactive idle prompts, orientation, clarification, confirmation, response brevity, truthfulness, safe actions and failure recovery. A short sample dialogue covering a complete order and one correction is included.
7. **Session and transcript interfaces** — exposed, documented listening/thinking/speaking/error status; interim/final STT; assistant spoken-text lifecycle; typed-input support; mute/pause/end controls; current context ingestion. These must be inspectable independently of the final UI.
8. **Interruption and latency evidence** — recorded measured warm/cold first audio, perceived TTFA, p50/p95 barge-in stop, observed false interruptions, selected test conditions, known bottlenecks and trial limitations; no fabricated performance claims.
9. **Acceptance-test record** — pass/fail and concise observations for T01–T20, with reproducible sample utterances and mock action traces; anonymized/consented short demo evidence if captured.
10. **Integration handover note** — a concise summary of the agent entry/exit points, exposed semantic events, state synchronization requirements, expected frontend callbacks, hard constraints, supported languages and known limitations. Clearly identify anything requiring a **joint Habiba + Zainab** contract decision.

### Definition of handover complete

Habiba can demonstrate an **independent, interruption-friendly, proactively welcoming, low-latency voice agent** that sends valid shopping action requests to a mock adapter and accurately speaks only verified results. Zainab can replace that mock adapter with the website's orchestration layer **without rewriting the voice conversation logic, STT, TTS or provider-specific agent code**.

---

## 12. Out of scope for this deliverable

Actual UI implementation, visual design, database deployment, real restaurant inventory, live payment gateway, real order fulfilment, doctor appointment flows, speaker identity/voice biometrics, autonomous purchasing, unconsented audio recording, continuous unsolicited listening when voice mode is off, and a guaranteed production multilingual service. Additional capabilities are subject to joint agreement only after core voice behavior and its integration contract are stable.

---

## 13. Provider reference notes (checked for this specification, 01 October 2026)

These links substantiate the **available capability families**; the numeric targets, interface names and acceptance conditions in this specification are **the project's design requirements**, not vendor promises.

1. LiveKit — [Realtime media, text streams, state and RPC](https://docs.livekit.io/frontends/build/media-data/) and [agent state](https://docs.livekit.io/frontends/build/agent-state/).
2. LiveKit — [Forwarding tool calls to the frontend using RPC](https://docs.livekit.io/agents/logic/tools/forwarding/), [turn-taking/interruptions tuning](https://docs.livekit.io/agents/logic/turns/tuning/) and [conversation latency metrics](https://docs.livekit.io/testing/observability/data/).
3. LiveKit — [Deepgram STT compatibility and available models](https://docs.livekit.io/agents/models/stt/deepgram/) and [Cartesia TTS compatibility and controls](https://docs.livekit.io/agents/models/tts/cartesia/).
4. Deepgram — [Flux conversation-aware streaming STT](https://developers.deepgram.com/docs/flux/quickstart) and [LiveKit integration](https://developers.deepgram.com/docs/livekit-integration). **Note:** Flux English supports the English-first demo; multilingual model support must be checked specifically for the target language.
5. Cartesia — [Sonic 3.6 capabilities and available languages](https://docs.cartesia.ai/build-with-cartesia/tts-models/latest).
6. Google — [Gemini 3.1 Flash-Lite model/capabilities](https://ai.google.dev/gemini-api/docs/models/gemini-3.1-flash-lite), [API pricing/free-tier availability](https://ai.google.dev/gemini-api/docs/pricing) and [rate limits](https://ai.google.dev/gemini-api/docs/rate-limits). Verify the active account's free-tier limits and data-use terms at project time.

**End of Habiba's requirements specification.**
