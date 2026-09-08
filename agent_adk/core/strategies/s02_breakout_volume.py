"""02. Breakout + Volume — Breakout confirmation.

Port từ strategies/02-breakout-plus-volume.md.
"""

from __future__ import annotations

import pandas as pd

from .base import BaseStrategy, Signal
from tools.indicators import volume_sma


class S02BreakoutVolume(BaseStrategy):
    name = "02-breakout-plus-volume"
    default_tf = "1d"
    default_params = {
        "lookback": 20,
        "vol_mult": 1.5,
        "rr": 2.0,
    }
    supports_short = False  # Pine version chỉ long

    def generate_signals(self, df: pd.DataFrame) -> list[Signal]:
        p = self.params
        lookback = int(p["lookback"])
        vol_mult = float(p["vol_mult"])
        rr = float(p["rr"])

        prev_high = df["high"].rolling(lookback, min_periods=lookback).max().shift(1)
        vol_avg = volume_sma(df["volume"], lookback)

        breakout = (df["close"] > prev_high) & (df["volume"] > vol_mult * vol_avg)
        signals: list[Signal] = []
        for i in range(len(df)):
            if not bool(breakout.iloc[i]):
                continue
            entry = float(df["close"].iloc[i])
            stop = float(df["low"].iloc[i])
            if stop >= entry:
                continue
            signals.append(Signal(
                ts=df["timestamp"].iloc[i], side="LONG", entry=entry,
                stop=stop, target=entry + rr * (entry - stop),
                reason=f"Đóng cửa vượt {lookback}-bar high + volume ≥ {vol_mult}× avg",
            ))
        return signals
