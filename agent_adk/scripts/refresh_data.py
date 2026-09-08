"""refresh_data — append 6 ngày gần nhất cho symbol/timeframe.

Ưu tiên XAUUSD.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone

from ..config import HISTORY_DIR, REFRESH_DAYS, REPORTS_DIR, TIMEFRAMES
from ..core.data_loader import refresh


def refresh_symbol(symbol: str, timeframe: str, days: int) -> None:
    print(f"[refresh] {symbol}/{timeframe} (days={days})...", end=" ", flush=True)
    try:
        res = refresh(symbol, timeframe, days=days)
        print(f"{res.source.upper()} -> {res.rows} rows, last={res.last_date}")
    except Exception as e:
        print(f"FAIL: {e}")


def main() -> None:
    p = argparse.ArgumentParser(description="Refresh dataset (append N ngày gần nhất)")
    p.add_argument("--symbol", default="XAUUSD")
    p.add_argument("--timeframe", default="1d", choices=TIMEFRAMES)
    p.add_argument("--days", type=int, default=REFRESH_DAYS,
                   help=f"Số ngày gần nhất luôn được refresh (mặc định {REFRESH_DAYS})")
    p.add_argument("--all-timeframes", action="store_true",
                   help="Refresh tất cả 3 timeframes (1d, 4h, 1h)")
    args = p.parse_args()

    if args.all_timeframes:
        for tf in TIMEFRAMES:
            refresh_symbol(args.symbol, tf, args.days)
    else:
        refresh_symbol(args.symbol, args.timeframe, args.days)

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    print(f"\nDone at {today} UTC. Reports -> {REPORTS_DIR}, history -> {HISTORY_DIR}")


if __name__ == "__main__":
    main()
