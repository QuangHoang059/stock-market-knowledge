"""01. EMA 20/50 Crossover — Trend Following.

Port từ strategies/01-ema-20-50-crossover.md (Pine Script v6).
"""

from __future__ import annotations

import pandas as pd

from .base import BaseStrategy, Signal, swing_high, swing_low

# Reuse từ tools/indicators.py — không tự code lại
from tools.indicators import ema


class S01EmaCross(BaseStrategy):
    name = "01-ema-20-50-crossover"
    default_tf = "1d"
    default_params = {
        "fast_len": 20,
        "slow_len": 50,
        "rr": 2.0,
        "swing": 5,
    }
    supports_short = True

    def generate_signals(self, df: pd.DataFrame) -> list[Signal]:
        p = self.params
        fast = ema(df["close"], int(p["fast_len"]))
        slow = ema(df["close"], int(p["slow_len"]))

        long_cross = (fast.shift(1) <= slow.shift(1)) & (fast > slow)
        short_cross = (fast.shift(1) >= slow.shift(1)) & (fast < slow)

        sl_long = swing_low(df, int(p["swing"]))
        sl_short = swing_high(df, int(p["swing"]))

        rr = float(p["rr"])
        signals: list[Signal] = []
        for i in range(len(df)):
            ts = df["timestamp"].iloc[i]
            close = float(df["close"].iloc[i])
            if bool(long_cross.iloc[i]):
                stop = float(sl_long.iloc[i])
                if stop < close:
                    signals.append(Signal(
                        ts=ts, side="LONG", entry=close,
                        stop=stop, target=close + rr * (close - stop),
                        reason=f"EMA{self.params['fast_len']} cắt lên EMA{self.params['slow_len']}",
                    ))
            elif bool(short_cross.iloc[i]):
                stop = float(sl_short.iloc[i])
                if stop > close:
                    signals.append(Signal(
                        ts=ts, side="SHORT", entry=close,
                        stop=stop, target=close - rr * (stop - close),
                        reason=f"EMA{self.params['fast_len']} cắt xuống EMA{self.params['slow_len']}",
                    ))
        return signals
