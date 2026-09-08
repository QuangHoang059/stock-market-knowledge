"""04. EMA20 Pullback — Trend pullback.

Port từ strategies/04-ema20-pullback.md.
"""

from __future__ import annotations

import pandas as pd

from .base import BaseStrategy, Signal
from tools.indicators import ema


class S04Ema20Pullback(BaseStrategy):
    name = "04-ema20-pullback"
    default_tf = "1d"
    default_params = {"fast_len": 20, "slow_len": 50, "swing": 5, "rr": 2.0}
    supports_short = True

    def generate_signals(self, df: pd.DataFrame) -> list[Signal]:
        p = self.params
        ema_fast = ema(df["close"], int(p["fast_len"]))
        ema_slow = ema(df["close"], int(p["slow_len"]))
        swing_lo = df["low"].rolling(int(p["swing"]), min_periods=1).min()
        swing_hi = df["high"].rolling(int(p["swing"]), min_periods=1).max()
        rr = float(p["rr"])

        uptrend = (ema_fast > ema_slow).fillna(False)
        pullback_long = uptrend & (df["low"] <= ema_fast) & (df["close"] > ema_fast)
        pullback_short = (~uptrend) & (df["high"] >= ema_fast) & (df["close"] < ema_fast)

        signals: list[Signal] = []
        for i in range(len(df)):
            entry = float(df["close"].iloc[i])
            ts = df["timestamp"].iloc[i]
            if bool(pullback_long.iloc[i]):
                stop = float(swing_lo.iloc[i])
                if stop < entry:
                    signals.append(Signal(
                        ts=ts, side="LONG", entry=entry,
                        stop=stop, target=entry + rr * (entry - stop),
                        reason="Pullback về EMA20 trong uptrend",
                    ))
            elif bool(pullback_short.iloc[i]):
                stop = float(swing_hi.iloc[i])
                if stop > entry:
                    signals.append(Signal(
                        ts=ts, side="SHORT", entry=entry,
                        stop=stop, target=entry - rr * (stop - entry),
                        reason="Pullback về EMA20 trong downtrend",
                    ))
        return signals
