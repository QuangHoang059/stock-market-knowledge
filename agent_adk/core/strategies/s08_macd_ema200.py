"""08. MACD + EMA200 Trend Filter.

Port từ strategies/08-macd-ema200-trend-filter.md.
"""

from __future__ import annotations

import pandas as pd

from .base import BaseStrategy, Signal
from tools.indicators import ema, macd


class S08MacdEma200(BaseStrategy):
    name = "08-macd-ema200-trend-filter"
    default_tf = "1d"
    default_params = {
        "fast": 12, "slow": 26, "signal": 9,
        "ema_len": 200, "swing": 5, "rr": 2.0,
    }
    supports_short = True

    def generate_signals(self, df: pd.DataFrame) -> list[Signal]:
        p = self.params
        macd_line, signal_line, hist = macd(df["close"], int(p["fast"]), int(p["slow"]), int(p["signal"]))
        ema200 = ema(df["close"], int(p["ema_len"]))
        swing_lo = df["low"].rolling(int(p["swing"]), min_periods=1).min()
        swing_hi = df["high"].rolling(int(p["swing"]), min_periods=1).max()
        rr = float(p["rr"])

        long_cond = (df["close"] > ema200) & (macd_line > signal_line) & (macd_line.shift(1) <= signal_line.shift(1)) & (hist > 0)
        short_cond = (df["close"] < ema200) & (macd_line < signal_line) & (macd_line.shift(1) >= signal_line.shift(1)) & (hist < 0)

        signals: list[Signal] = []
        for i in range(len(df)):
            entry = float(df["close"].iloc[i])
            ts = df["timestamp"].iloc[i]
            if bool(long_cond.iloc[i]):
                stop = float(swing_lo.iloc[i])
                if stop < entry:
                    signals.append(Signal(
                        ts=ts, side="LONG", entry=entry,
                        stop=stop, target=entry + rr * (entry - stop),
                        reason="Giá trên EMA200 + MACD cross up",
                    ))
            elif bool(short_cond.iloc[i]):
                stop = float(swing_hi.iloc[i])
                if stop > entry:
                    signals.append(Signal(
                        ts=ts, side="SHORT", entry=entry,
                        stop=stop, target=entry - rr * (stop - entry),
                        reason="Giá dưới EMA200 + MACD cross down",
                    ))
        return signals
