"""09. Opening Range Breakout (intraday).

Port từ strategies/09-opening-range-breakout.md.
Lưu ý: Opening Range (NYSE 09:30-09:45) chỉ áp dụng cho equities Mỹ. Với XAUUSD/BTC
chúng ta dùng opening range của "ngày giao dịch" (00:00 UTC) → 4 giờ đầu, hoặc với khung 1h
lấy bar đầu tiên của ngày làm OR high/low.

Để đơn giản và tái sử dụng cho nhiều symbol, định nghĩa OR = high/low của n bar đầu trong ngày.
"""

from __future__ import annotations

import pandas as pd

from .base import BaseStrategy, Signal


class S09OpeningRange(BaseStrategy):
    name = "09-opening-range-breakout"
    default_tf = "1h"
    default_params = {"or_bars": 4, "rr": 2.0}  # 4 bars đầu = 4 giờ đầu của ngày UTC
    supports_short = False

    def generate_signals(self, df: pd.DataFrame) -> list[Signal]:
        p = self.params
        or_n = int(p["or_bars"])
        rr = float(p["rr"])

        ts = pd.to_datetime(df["timestamp"], utc=True, errors="coerce")
        date = ts.dt.date

        # OR high/low = high/low của n bar đầu tiên mỗi ngày
        # Group by date, lấy running max/min trong nhóm đầu tiên
        or_high = df.groupby(date)["high"].transform(
            lambda s: s.head(or_n).cummax()
        )
        or_low = df.groupby(date)["low"].transform(
            lambda s: s.head(or_n).cummin()
        )

        # Chỉ phát tín hiệu SAU khi đã pass `or_n` bar đầu
        grp_idx = df.groupby(date).cumcount()
        past_or = grp_idx >= or_n

        cond_long = (
            past_or
            & (df["close"] > or_high)
            & (df["close"].shift(1) <= or_high.shift(1))
        )

        signals: list[Signal] = []
        for i in range(len(df)):
            if not bool(cond_long.iloc[i]):
                continue
            entry = float(df["close"].iloc[i])
            stop = float(or_low.iloc[i])
            if stop >= entry:
                continue
            signals.append(Signal(
                ts=df["timestamp"].iloc[i], side="LONG", entry=entry,
                stop=stop, target=entry + rr * (entry - stop),
                reason=f"Breakout OR high (first {or_n} bars of day)",
            ))
        return signals
