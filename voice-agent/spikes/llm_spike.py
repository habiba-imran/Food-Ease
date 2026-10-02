"""Gemini LLM spike (Phase 1). Explicit thinking_level. Stop on 429 after backoff.

Supports resume from evidence/phase-1/llm.csv. Uses inter-request pacing to
respect free-tier RPM. Does not invent metrics.
"""

from __future__ import annotations

import csv
import json
import random
import sys
import time
from pathlib import Path

from google import genai
from google.genai import types

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "spikes"))

from _env import load_env, require  # noqa: E402

PRIMARY = "gemini-3.1-flash-lite"
FALLBACK = "gemini-2.5-flash-lite"
LLM_CSV = ROOT / "evidence" / "phase-1" / "llm.csv"
SAMPLES_DIR = ROOT / "evidence" / "phase-1" / "llm_samples"
META_JSON = ROOT / "evidence" / "phase-1" / "llm_meta.json"

# Pace free-tier calls. Observed 429 under rapid fire after ~20–27 calls.
INTER_REQUEST_SLEEP_S = 8.0

FUNCTION_DECLS: list[types.FunctionDeclaration] = [
    types.FunctionDeclaration(
        name="navigate",
        description="Navigate to a named app page or back/home.",
        parameters_json_schema={
            "type": "object",
            "properties": {"target": {"type": "string"}},
            "required": ["target"],
        },
    ),
    types.FunctionDeclaration(
        name="search_menu",
        description="Search the menu by free text.",
        parameters_json_schema={
            "type": "object",
            "properties": {"query": {"type": "string"}},
            "required": ["query"],
        },
    ),
    types.FunctionDeclaration(
        name="filter_menu",
        description="Filter menu by tags and optional max price in PKR.",
        parameters_json_schema={
            "type": "object",
            "properties": {
                "tags": {"type": "array", "items": {"type": "string"}},
                "max_price_pkr": {"type": "number"},
            },
        },
    ),
    types.FunctionDeclaration(
        name="select_item",
        description="Select a menu item by application item_id.",
        parameters_json_schema={
            "type": "object",
            "properties": {"item_id": {"type": "string"}},
            "required": ["item_id"],
        },
    ),
    types.FunctionDeclaration(
        name="get_item_details",
        description="Fetch details for an item_id.",
        parameters_json_schema={
            "type": "object",
            "properties": {"item_id": {"type": "string"}},
            "required": ["item_id"],
        },
    ),
    types.FunctionDeclaration(
        name="get_cart",
        description="Fetch the current cart.",
        parameters_json_schema={"type": "object", "properties": {}},
    ),
    types.FunctionDeclaration(
        name="cart.add_item",
        description="Add an item to the cart.",
        parameters_json_schema={
            "type": "object",
            "properties": {
                "item_id": {"type": "string"},
                "quantity": {"type": "integer"},
            },
            "required": ["item_id", "quantity"],
        },
    ),
    types.FunctionDeclaration(
        name="cart.set_quantity",
        description="Set quantity for a cart line.",
        parameters_json_schema={
            "type": "object",
            "properties": {
                "item_id": {"type": "string"},
                "quantity": {"type": "integer"},
            },
            "required": ["item_id", "quantity"],
        },
    ),
    types.FunctionDeclaration(
        name="cart.remove_item",
        description="Remove an item from the cart.",
        parameters_json_schema={
            "type": "object",
            "properties": {"item_id": {"type": "string"}},
            "required": ["item_id"],
        },
    ),
    types.FunctionDeclaration(
        name="checkout.get_summary",
        description="Get checkout summary for confirmation.",
        parameters_json_schema={"type": "object", "properties": {}},
    ),
    types.FunctionDeclaration(
        name="checkout.submit_demo_order",
        description="Submit a demo (non-charging) order after confirmation.",
        parameters_json_schema={
            "type": "object",
            "properties": {"confirmed": {"type": "boolean"}},
            "required": ["confirmed"],
        },
    ),
    types.FunctionDeclaration(
        name="undo_last_reversible_action",
        description="Undo the last reversible cart/navigation action.",
        parameters_json_schema={"type": "object", "properties": {}},
    ),
    types.FunctionDeclaration(
        name="get_current_context",
        description="Refresh the current UI context snapshot.",
        parameters_json_schema={"type": "object", "properties": {}},
    ),
]

SYSTEM = (
    "You are FoodEase, a concise food-ordering voice guide. "
    "Use tools for app actions. Never invent prices. Keep spoken replies short."
)

TOOL_CASES: list[tuple[str, str, dict]] = [
    ("show burgers", "search_menu", {"query": "burgers"}),
    ("vegetarian under eight hundred", "filter_menu", {}),
    ("add two of item burger_01", "cart.add_item", {"item_id": "burger_01", "quantity": 2}),
    ("make it one of item burger_01", "cart.set_quantity", {"item_id": "burger_01", "quantity": 1}),
    ("remove item wrap_01", "cart.remove_item", {"item_id": "wrap_01"}),
    ("what's in my cart", "get_cart", {}),
    ("go to checkout", "navigate", {"target": "checkout"}),
    ("go back", "navigate", {"target": "back"}),
    ("item details for wrap_02", "get_item_details", {"item_id": "wrap_02"}),
    ("select item zinger_01", "select_item", {"item_id": "zinger_01"}),
    ("checkout summary", "checkout.get_summary", {}),
    ("place the demo order, yes", "checkout.submit_demo_order", {"confirmed": True}),
    ("undo that", "undo_last_reversible_action", {}),
    ("where am I", "get_current_context", {}),
    ("filter spicy max 1000", "filter_menu", {}),
    ("search karahi", "search_menu", {"query": "karahi"}),
    ("add one dessert_01", "cart.add_item", {"item_id": "dessert_01", "quantity": 1}),
    ("set quantity of burger_01 to 3", "cart.set_quantity", {"item_id": "burger_01", "quantity": 3}),
    ("remove burger_01", "cart.remove_item", {"item_id": "burger_01"}),
    ("open home", "navigate", {"target": "home"}),
]

SAMPLE_PROMPTS: list[str] = [
    "I want something spicy but not too expensive.",
    "What can you help me with?",
    "The second one please.",
    "Actually make it one.",
    "Is this a real payment?",
    "Tell me what's on the screen.",
    "I changed my mind about the wrap.",
    "How do I stop you talking?",
    "Any vegetarian wraps?",
    "Thanks, that's all for now.",
]


class RateLimitHit(Exception):
    def __init__(self, message: str, observed: dict) -> None:
        super().__init__(message)
        self.observed = observed


def _is_429(exc: BaseException) -> bool:
    text = str(exc).lower()
    if "429" in text or "resource_exhausted" in text:
        return True
    code = getattr(exc, "code", None) or getattr(exc, "status_code", None)
    return code == 429


def call_with_backoff(fn, *, label: str, max_retries: int = 3):  # noqa: ANN001
    delays = [5.0, 15.0, 45.0]
    for attempt in range(max_retries + 1):
        try:
            return fn()
        except Exception as exc:  # noqa: BLE001
            if not _is_429(exc):
                raise
            if attempt >= max_retries:
                raise RateLimitHit(
                    f"429 on {label} after {max_retries} backoffs — stopping (no loop).",
                    observed={
                        "label": label,
                        "attempts": attempt + 1,
                        "error_type": type(exc).__name__,
                        "error": str(exc)[:400],
                        "inter_request_sleep_s": INTER_REQUEST_SLEEP_S,
                    },
                ) from exc
            delay = delays[min(attempt, len(delays) - 1)] + random.uniform(0, 1.0)
            print(f"429 on {label}; backoff {delay:.1f}s (attempt {attempt + 1}/{max_retries})")
            time.sleep(delay)
    raise RuntimeError("unreachable")


def pace() -> None:
    time.sleep(INTER_REQUEST_SLEEP_S)


def load_rows() -> list[dict]:
    if not LLM_CSV.exists():
        return []
    with LLM_CSV.open(encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


def write_csv(rows: list[dict]) -> None:
    LLM_CSV.parent.mkdir(parents=True, exist_ok=True)
    keys: list[str] = []
    for row in rows:
        for k in row:
            if k not in keys:
                keys.append(k)
    with LLM_CSV.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=keys)
        writer.writeheader()
        writer.writerows(rows)


def write_meta(rows: list[dict], observed_limits: dict) -> None:
    def tool_stats(model: str) -> dict:
        subset = [r for r in rows if r.get("kind") == "tool" and r.get("model") == model]
        correct = sum(1 for r in subset if str(r.get("ok")).lower() in {"1", "true", "True"})
        return {"correct": correct, "total": len(subset)}

    lat = [r for r in rows if r.get("kind") == "latency"]
    meta = {
        "primary_model": PRIMARY,
        "fallback_model": FALLBACK,
        "tool_accuracy_primary": tool_stats(PRIMARY),
        "tool_accuracy_fallback": tool_stats(FALLBACK),
        "latency_counts": {},
        "samples_dir": str(SAMPLES_DIR.relative_to(ROOT)),
        "observed_limits": observed_limits,
        "inter_request_sleep_s": INTER_REQUEST_SLEEP_S,
        "note": "ttft_ms is non-streaming total latency (API does not expose true TTFT here).",
    }
    for r in lat:
        key = f"{r.get('model')}|{r.get('thinking_level')}"
        meta["latency_counts"][key] = meta["latency_counts"].get(key, 0) + 1
    META_JSON.write_text(json.dumps(meta, indent=2), encoding="utf-8")


def gen_text(
    client: genai.Client,
    *,
    model: str,
    thinking_level: str,
    contents: str,
    tools: bool = False,
) -> tuple[object, float]:
    config_kwargs: dict = {
        "system_instruction": SYSTEM,
        "thinking_config": types.ThinkingConfig(thinking_level=thinking_level),
    }
    if tools:
        config_kwargs["tools"] = [types.Tool(function_declarations=FUNCTION_DECLS)]
        config_kwargs["automatic_function_calling"] = types.AutomaticFunctionCallingConfig(
            disable=True
        )
        config_kwargs["tool_config"] = types.ToolConfig(
            function_calling_config=types.FunctionCallingConfig(mode="ANY")
        )

    def _do():
        pace()
        t0 = time.perf_counter()
        resp = client.models.generate_content(
            model=model,
            contents=contents,
            config=types.GenerateContentConfig(**config_kwargs),
        )
        total_ms = (time.perf_counter() - t0) * 1000.0
        return resp, total_ms

    return call_with_backoff(_do, label=f"{model}/{thinking_level}")


def extract_tool(resp: object) -> tuple[str | None, dict]:
    candidates = getattr(resp, "candidates", None) or []
    for cand in candidates:
        content = getattr(cand, "content", None)
        parts = getattr(content, "parts", None) or []
        for part in parts:
            fc = getattr(part, "function_call", None)
            if fc is not None:
                name = getattr(fc, "name", None)
                args = dict(getattr(fc, "args", {}) or {})
                return name, args
    return None, {}


def percentile(values: list[float], p: float) -> float:
    if not values:
        return float("nan")
    ordered = sorted(values)
    idx = max(0, min(len(ordered) - 1, int(round(p * (len(ordered) - 1)))))
    return ordered[idx]


def latency_done(rows: list[dict], model: str, level: str) -> int:
    return sum(
        1
        for r in rows
        if r.get("kind") == "latency"
        and r.get("model") == model
        and r.get("thinking_level") == level
    )


def run_latency(
    client: genai.Client,
    rows: list[dict],
    *,
    model: str,
    thinking_level: str,
    n: int,
) -> None:
    prompt = "Say a one-sentence welcome to the FoodEase demo."
    have = latency_done(rows, model, thinking_level)
    for i in range(have, n):
        _resp, total_ms = gen_text(
            client, model=model, thinking_level=thinking_level, contents=prompt, tools=False
        )
        rows.append(
            {
                "kind": "latency",
                "model": model,
                "thinking_level": thinking_level,
                "run": str(i),
                "total_ms": f"{total_ms:.2f}",
                "ttft_ms_note": "non-streaming; same as total_ms",
                "ttft_ms": f"{total_ms:.2f}",
            }
        )
        write_csv(rows)
        if (i + 1) % 5 == 0:
            print(f"latency {model} {thinking_level}: {i + 1}/{n}")
    times = [
        float(r["total_ms"])
        for r in rows
        if r.get("kind") == "latency"
        and r.get("model") == model
        and r.get("thinking_level") == thinking_level
    ]
    if times:
        print(
            f"{model} thinking={thinking_level}: n={len(times)} "
            f"p50={percentile(times, 0.5):.0f} p95={percentile(times, 0.95):.0f} "
            f"max={max(times):.0f} ms"
        )


def tool_done(rows: list[dict], model: str) -> int:
    return sum(1 for r in rows if r.get("kind") == "tool" and r.get("model") == model)


def run_tools(client: genai.Client, rows: list[dict], *, model: str) -> None:
    have = tool_done(rows, model)
    for i in range(have, len(TOOL_CASES)):
        utterance, expect_name, expect_args = TOOL_CASES[i]
        resp, total_ms = gen_text(
            client,
            model=model,
            thinking_level="minimal",
            contents=(
                f"User said: {utterance!r}. Call exactly one allowlisted tool "
                f"with the best arguments. Prefer item_id when given."
            ),
            tools=True,
        )
        name, args = extract_tool(resp)
        name_ok = name == expect_name
        args_ok = all(args.get(k) == v for k, v in expect_args.items())
        ok = name_ok and args_ok
        rows.append(
            {
                "kind": "tool",
                "model": model,
                "run": str(i),
                "utterance": utterance,
                "expected": expect_name,
                "got": name or "",
                "args": json.dumps(args, sort_keys=True),
                "ok": str(ok),
                "total_ms": f"{total_ms:.2f}",
            }
        )
        write_csv(rows)
        print(f"tool {i + 1}/{len(TOOL_CASES)}: expect={expect_name} got={name} ok={ok}")


def run_samples(client: genai.Client, *, model: str) -> None:
    out = SAMPLES_DIR / model.replace("/", "_")
    out.mkdir(parents=True, exist_ok=True)
    for i, prompt in enumerate(SAMPLE_PROMPTS):
        path = out / f"{i:02d}.txt"
        if path.exists():
            continue
        resp, total_ms = gen_text(
            client, model=model, thinking_level="minimal", contents=prompt, tools=False
        )
        text = resp.text or ""
        path.write_text(
            f"PROMPT: {prompt}\nLATENCY_MS: {total_ms:.1f}\n---\n{text}\n",
            encoding="utf-8",
        )
        print(f"sample {model} {i + 1}/{len(SAMPLE_PROMPTS)}")


def main() -> int:
    load_env()
    api_key = require("GOOGLE_API_KEY")
    client = genai.Client(api_key=api_key)
    rows = load_rows()
    observed_limits: dict = {"stopped_on_429": False, "prior_429_events": []}
    if META_JSON.exists():
        prior = json.loads(META_JSON.read_text(encoding="utf-8"))
        if prior.get("observed_limits", {}).get("stopped_on_429"):
            observed_limits["prior_429_events"].append(prior["observed_limits"])

    print(f"Resuming with {len(rows)} CSV rows; sleep={INTER_REQUEST_SLEEP_S}s between calls")
    # Cool-down after a prior 429
    if observed_limits["prior_429_events"]:
        print("Prior 429 recorded — cooling down 60s before resume")
        time.sleep(60)

    try:
        # Primary: finish planned latency (may be incomplete if quota bites again).
        run_latency(client, rows, model=PRIMARY, thinking_level="minimal", n=30)
        run_latency(client, rows, model=PRIMARY, thinking_level="low", n=30)
        run_tools(client, rows, model=PRIMARY)
        run_samples(client, model=PRIMARY)

        # Fallback: smaller n to conserve quota
        run_latency(client, rows, model=FALLBACK, thinking_level="minimal", n=10)
        run_latency(client, rows, model=FALLBACK, thinking_level="low", n=10)
        run_tools(client, rows, model=FALLBACK)
        run_samples(client, model=FALLBACK)
    except RateLimitHit as exc:
        observed_limits["stopped_on_429"] = True
        observed_limits["detail"] = exc.observed
        print(str(exc))

    write_csv(rows)
    write_meta(rows, observed_limits)
    print(f"Wrote {LLM_CSV}")
    print("STOP for human read-aloud (1.3): evidence/phase-1/llm_samples/")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
