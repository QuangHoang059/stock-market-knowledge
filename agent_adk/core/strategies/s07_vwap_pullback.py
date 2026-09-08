"""07. VWAP Pullback — Intraday trend.

Port từ strategies/07-vwap-pullback.md.
Lưu ý: VWAP rolling chỉ là xấp xỉ khi không có intraday volume — Pine dùng session VWAP.
"""

from __future__ import annotations

import pandas as pd

from .base import BaseStrategy, Signal
from tools.indicators import vwap


class S07VwapPullback(BaseStrategy):
    name = "07-vwap-pullback"
    default_tf = "1h"
    default_params = {"vwap_n": 20, "swing": 5, "rr": 1.5}
    supports_short = True

    def generate_signals(self, df: pd.DataFrame) -> list[Signal]:
        p = self.params
        v = vwap(df, int(p["vwap_n"]))
        v_prev = v.shift(1)
        swing_lo = df["low"].rolling(int(p["swing"]), min_periods=1).min()
        swing_hi = df["high"].rolling(int(p["swing"]), min_periods=1).max()
        rr = float(p["rr"])

        cond_long = (df["close"] > v) & (v > v_prev) & (df["low"] <= v) & (df["close"] > v)
        cond_short = (df["close"] < v) & (v < v_prev) & (df["high"] >= v) & (df["close"] < v)

        signals: list[Signal] = []
        for i in range(len(df)):
            entry = float(df["close"].iloc[i])
            ts = df["timestamp"].iloc[i]
            if bool(cond_long.iloc[i]):
                stop = float(swing_lo.iloc[i])
                if stop < entry:
                    signals.append(Signal(
                        ts=ts, side="LONG", entry=entry,
                        stop=stop, target=entry + rr * (entry - stop),
                        reason="VWAP pullback trong uptrend",
                    ))
            elif bool(cond_short.iloc[i]):
                stop = float(swing_hi.iloc[i])
                if stop > entry:
                    signals.append(Signal(
                        ts=ts, side="SHORT", entry=entry,
                        stop=stop, target=entry - rr * (stop - entry),
                        reason="VWAP pullback trong downtrend",
                    ))
        return signals
