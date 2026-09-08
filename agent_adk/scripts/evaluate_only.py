"""evaluate_only — backtest nhanh 10 strategies không cần LLM.

Dùng để sanity-check pipeline core trước khi chạy full ADK loop.
"""

from __future__ import annotations

import argparse
import json
import sys

from ..config import REPORTS_DIR, TIMEFRAMES
from ..core.engine.evaluator import evaluate_all
from ..core.data_loader import refresh


def main() -> None:
    # Force UTF-8 stdout (Windows cp1252 fix)
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

    p = argparse.ArgumentParser(description="Backtest 10 strategies (khong can LLM)")
    p.add_argument("--symbol", default="XAUUSD")
    p.add_argument("--timeframe", default="1d", choices=TIMEFRAMES)
    p.add_argument("--refresh", action="store_true", help="Refresh 6 ngay truoc khi backtest")
    p.add_argument("--save-md", action="store_true",
                   help=f"Luu markdown vao {REPORTS_DIR}/latest_<symbol>_<tf>.md")
    p.add_argument("--json", action="store_true", help="In metrics dang JSON")
    args = p.parse_args()

    if args.refresh:
        refresh(args.symbol, args.timeframe, days=6)

    report = evaluate_all(args.symbol, args.timeframe)

    if args.json:
        print(json.dumps(report.to_dict(), indent=2, ensure_ascii=False))
    else:
        print(report.to_markdown())

    if args.save_md:
        REPORTS_DIR.mkdir(parents=True, exist_ok=True)
        out_path = REPORTS_DIR / f"latest_{args.symbol}_{args.timeframe}.md"
        out_path.write_text(report.to_markdown(), encoding="utf-8")
        print(f"\nSaved -> {out_path}")


if __name__ == "__main__":
    main()
