"""download_data — tải dataset lần đầu cho XAUUSD + BTCUSD × 3 timeframes.

Không cần LLM. Chạy được ngay cả khi chưa có API key.
"""

from __future__ import annotations

import argparse

from ..config import DATA_DIR, TIMEFRAMES, get_symbol_meta
from ..core.data_loader import download


def download_symbol(symbol: str, timeframes: list[str]) -> None:
    meta = get_symbol_meta(symbol)
    print(f"\n[{symbol}] {meta['name_vi']} (yahoo={meta['yahoo']}, tv={meta['tradingview']})")
    for tf in timeframes:
        print(f"  -> {tf}...", end=" ", flush=True)
        try:
            res = download(symbol, tf, overwrite=True)
            print(f"OK ({res.rows} rows, {res.first_date.date()} -> {res.last_date.date()})")
        except Exception as e:
            print(f"FAIL: {e}")


def main() -> None:
    p = argparse.ArgumentParser(description="Tải dataset OHLCV cho XAUUSD và BTCUSD")
    p.add_argument("--symbols", nargs="+", default=["XAUUSD", "BTCUSD"])
    p.add_argument("--timeframes", nargs="+", default=TIMEFRAMES, choices=TIMEFRAMES)
    args = p.parse_args()

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    print(f"Data dir: {DATA_DIR}")

    for sym in args.symbols:
        try:
            download_symbol(sym, args.timeframes)
        except KeyError as e:
            print(f"Skip {sym}: {e}")


if __name__ == "__main__":
    main()
