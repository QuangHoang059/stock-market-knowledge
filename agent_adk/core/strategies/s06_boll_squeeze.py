"""06. Bollinger Squeeze Breakout — Volatility expansion.

Port từ strategies/06-bollinger-squeeze-breakout.md.
"""

from __future__ import annotations

import pandas as pd

from .base import BaseStrategy, Signal
from tools.indicators import bollinger, volume_sma


class S06BollSqueeze(BaseStrategy):
    name = "06-bollinger-squeeze-breakout"
    default_tf = "1d"
    default_params = {
        "n": 20, "k": 2.0, "sma_n": 50,
        "squeeze_th": 0.8, "vol_mult": 1.5, "swing": 10, "rr": 2.0,
    }
    supports_short = False

    def generate_signals(self, df: pd.DataFrame) -> list[Signal]:
        p = self.params
        _bb = bollinger(df["close"], int(p["n"]), float(p["k"]))
        upper = _bb[1]
        width = _bb[3]
        width_sma = width.rolling(int(p["sma_n"]), min_periods=max(2, int(p["sma_n"]) // 2)).mean()
        vol_avg = volume_sma(df["volume"], int(p["n"]))
        swing_lo = df["low"].rolling(int(p["swing"]), min_periods=1).min()
        rr = float(p["rr"])

        squeeze = width < float(p["squeeze_th"]) * width_sma
        breakout = (df["close"] > upper) & (df["volume"] > float(p["vol_mult"]) * vol_avg)
        cond = squeeze.shift(1).fillna(False) & breakout

        signals: list[Signal] = []
        for i in range(len(df)):
            if not bool(cond.iloc[i]):
                continue
            entry = float(df["close"].iloc[i])
            stop = float(swing_lo.iloc[i])
            if stop >= entry:
                continue
            signals.append(Signal(
                ts=df["timestamp"].iloc[i], side="LONG", entry=entry,
                stop=stop, target=entry + rr * (entry - stop),
                reason="BB squeeze → breakout lên upper band + volume",
            ))
        return signals
