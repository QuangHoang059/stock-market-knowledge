"""Runner — InMemoryRunner + CLI.

Chạy full_pipeline cho 1 symbol/timeframe.

Usage:
    python -m agent_adk.runner --symbol XAUUSD --timeframe 1d
    python -m agent_adk.runner --symbol BTCUSD --timeframe 1h --provider gemini
"""

from __future__ import annotations

import argparse
import asyncio
import os
import uuid
from datetime import datetime, timezone

from google.genai import types as genai_types

from .config import HISTORY_DIR, REPORTS_DIR, get_symbol_meta
from .pipeline import full_pipeline


async def _run(symbol: str, timeframe: str, goal: str | None = None) -> dict:
    """Chạy pipeline async và trả về state cuối."""
    from google.adk.runners import InMemoryRunner

    provider = os.environ.get("AGENT_ADK_PROVIDER", "claude")
    print(f"[runner] symbol={symbol} tf={timeframe} provider={provider}")

    runner = InMemoryRunner(agent=full_pipeline)
    user_id = "user"
    session_id = f"session-{uuid.uuid4().hex[:8]}"

    user_text = (
        f"Đánh giá chiến lược cho {symbol} ({get_symbol_meta(symbol)['name_vi']}) "
        f"trên khung {timeframe}.\n"
        f"Mục tiêu: {goal or 'tìm chiến lược Sharpe > 0.5, max DD < 20%, win rate > 40%'}.\n"
        f"Hãy refresh data 6 ngày gần nhất trước, rồi iterate tối đa 5 vòng, "
        f"cuối cùng viết báo cáo markdown."
    )
    new_message = genai_types.Content(
        role="user",
        parts=[genai_types.Part(text=user_text)],
    )

    state: dict = {}
    async for event in runner.run_async(
        user_id=user_id, session_id=session_id, new_message=new_message,
    ):
        # Capture state delta từ các actions
        if getattr(event, "actions", None) and getattr(event.actions, "state_delta", None):
            state.update(event.actions.state_delta)
        # Capture author output nếu có
        if getattr(event, "author", None) and getattr(event, "content", None):
            text = ""
            try:
                for part in event.content.parts or []:
                    if hasattr(part, "text") and part.text:
                        text += part.text
            except Exception:
                pass
            if text:
                state.setdefault(f"_log_{event.author}", []).append(text)

    return state


def save_report(state: dict, symbol: str, timeframe: str) -> None:
    """Lưu final_report markdown ra reports/latest_<symbol>_<tf>.md và snapshot history."""
    final_md = state.get("final_report", "")
    if not isinstance(final_md, str):
        # Nếu LLM trả về list các phần, ghép lại
        if isinstance(final_md, list):
            final_md = "\n\n".join(str(x) for x in final_md)
        else:
            final_md = str(final_md)

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    HISTORY_DIR.mkdir(parents=True, exist_ok=True)

    latest_path = REPORTS_DIR / f"latest_{symbol}_{timeframe}.md"
    latest_path.write_text(final_md, encoding="utf-8")

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    history_path = HISTORY_DIR / f"{today}_{symbol}_{timeframe}.md"
    history_path.write_text(final_md, encoding="utf-8")

    print(f"[runner] saved → {latest_path}")
    print(f"[runner] snapshot → {history_path}")


def main() -> None:
    p = argparse.ArgumentParser(description="agent_adk pipeline runner")
    p.add_argument("--symbol", default="XAUUSD")
    p.add_argument("--timeframe", default="1d", choices=["1d", "4h", "1h"])
    p.add_argument("--goal", default=None)
    args = p.parse_args()

    state = asyncio.run(_run(args.symbol, args.timeframe, args.goal))
    save_report(state, args.symbol, args.timeframe)


if __name__ == "__main__":
    main()
