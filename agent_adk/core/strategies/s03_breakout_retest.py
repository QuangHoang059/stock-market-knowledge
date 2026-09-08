"""03. Breakout + Retest — Breakout xác nhận bằng retest.

Port từ strategies/03-breakout-retest.md.
"""

from __future__ import annotations

import pandas as pd

from .base import BaseStrategy, Signal
from tools.indicators import atr as atr_ind


class S03BreakoutRetest(BaseStrategy):
    name = "03-breakout-retest"
    default_tf = "1d"
    default_params = {
        "lookback": 20,
        "atr_tol_mult": 0.2,
        "rr": 2.0,
        "swing": 5,
    }
    supports_short = False

    def generate_signals(self, df: pd.DataFrame) -> list[Signal]:
        p = self.params
        lookback = int(p["lookback"])
        tol = float(p["atr_tol_mult"])
        rr = float(p["rr"])

        prev_high = df["high"].rolling(lookback, min_periods=lookback).max().shift(1)
        atr = atr_ind(df, 14)

        # Bước 1: phát hiện breakout bar trong vòng 5 bar gần nhất
        was_broken = (
            (df["close"].shift(1) > prev_high) |
            (df["close"].shift(2) > prev_high.shift(1)) |
            (df["close"].shift(3) > prev_high.shift(2))
        )
        # Bước 2: giá retest về vùng brokenLevel (trong vòng ATR × tol)
        tol_band = (atr * tol).fillna(0)
        near_level = (df["low"] <= prev_high + tol_band) & (df["low"] >= prev_high - tol_band)
        # Bước 3: đóng cửa quay lại trên level
        reclaim = df["close"] > prev_high
        entry_cond = was_broken & near_level & reclaim

        signals: list[Signal] = []
        swing_lo = df["low"].rolling(int(p["swing"]), min_periods=1).min()
        for i in range(len(df)):
            if not bool(entry_cond.iloc[i]):
                continue
            entry = float(df["close"].iloc[i])
            stop = float(swing_lo.iloc[i])
            if stop >= entry:
                continue
            signals.append(Signal(
                ts=df["timestamp"].iloc[i], side="LONG", entry=entry,
                stop=stop, target=entry + rr * (entry - stop),
                reason=f"Retest level {float(prev_high.iloc[i]):.2f} sau breakout",
            ))
        return signals
