"""Dev-only text CLI entry (allowed to import MockAdapter — lives under adapters/)."""

from __future__ import annotations

import argparse
import asyncio
from pathlib import Path

from foodease_agent.adapters.mock import MockAdapter
from foodease_agent.engine import ConversationEngine
from foodease_agent.planner import RulePlanner


async def _run(transcript_path: Path | None) -> None:
    adapter = MockAdapter()
    engine = ConversationEngine(adapter=adapter, planner=RulePlanner())
    lines: list[str] = []
    print("FoodEase text CLI (MockAdapter). Type 'goodbye' to exit.")
    while True:
        try:
            user = input("You> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if not user:
            continue
        result = await engine.handle_text(user)
        lines.append(f"USER: {user}")
        lines.append(f"ASSISTANT: {result.assistant_text}")
        print(f"Agent> {result.assistant_text}")
        if result.ended:
            break
    if transcript_path:
        transcript_path.parent.mkdir(parents=True, exist_ok=True)
        transcript_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        print(f"Saved transcript to {transcript_path}")


def main() -> None:
    parser = argparse.ArgumentParser(description="FoodEase text conversation CLI")
    parser.add_argument("--transcript", type=Path, default=None)
    args = parser.parse_args()
    asyncio.run(_run(args.transcript))


if __name__ == "__main__":
    main()
