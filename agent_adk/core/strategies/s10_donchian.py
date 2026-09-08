"""10. Donchian Channel Breakout — Multi-TF breakout.

Port từ strategies/10-donchian-channel-breakout.md.
"""

from __future__ import annotations

import pandas as pd

from .base import BaseStrategy, Signal
from tools.indicators import atr as atr_ind


class S10Donchian(BaseStrategy):
    name = "10-donchian-channel-breakout"
    default_tf = "1d"
    default_params = {"lookback": 20, "atr_n": 14, "atr_sl": 2.0, "atr_tp": 3.0}
    supports_short = True

    def generate_signals(self, df: pd.DataFrame) -> list[Signal]:
        p = self.params
        lookback = int(p["lookback"])
        atr_v = atr_ind(df, int(p["atr_n"]))

        upper = df["high"].rolling(lookback, min_periods=lookback).max().shift(1)
        lower = df["low"].rolling(lookback, min_periods=lookback).min().shift(1)

        long_cond = df["close"] > upper
        short_cond = df["close"] < lower

        atr_sl_mult = float(p["atr_sl"])
        atr_tp_mult = float(p["atr_tp"])

        signals: list[Signal] = []
        for i in range(len(df)):
            entry = float(df["close"].iloc[i])
            a = float(atr_v.iloc[i]) if pd.notna(atr_v.iloc[i]) else 0.0
            if a <= 0:
                continue
            ts = df["timestamp"].iloc[i]
            if bool(long_cond.iloc[i]):
                stop = entry - atr_sl_mult * a
                target = entry + atr_tp_mult * a
                signals.append(Signal(
                    ts=ts, side="LONG", entry=entry, stop=stop, target=target,
                    reason=f"Donchian {lookback}-bar high breakout",
                ))
            elif bool(short_cond.iloc[i]):
                stop = entry + atr_sl_mult * a
                target = entry - atr_tp_mult * a
                signals.append(Signal(
                    ts=ts, side="SHORT", entry=entry, stop=stop, target=target,
                    reason=f"Donchian {lookback}-bar low breakdown",
                ))
        return signals
