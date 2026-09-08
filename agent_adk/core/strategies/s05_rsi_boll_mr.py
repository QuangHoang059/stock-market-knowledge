"""05. RSI + Bollinger Mean Reversion.

Port từ strategies/05-rsi-bollinger-mean-reversion.md.
"""

from __future__ import annotations

import pandas as pd

from .base import BaseStrategy, Signal
from tools.indicators import bollinger, rsi


class S05RsiBollMeanReversion(BaseStrategy):
    name = "05-rsi-bollinger-mean-reversion"
    default_tf = "1d"
    default_params = {"n": 20, "k": 2.0, "rsi_n": 14, "rsi_th": 30, "swing": 5, "rr": 1.5}
    supports_short = False

    def generate_signals(self, df: pd.DataFrame) -> list[Signal]:
        p = self.params
        _bb = bollinger(df["close"], int(p["n"]), float(p["k"]))
        lower = _bb[2]
        rsi_v = rsi(df["close"], int(p["rsi_n"]))
        swing_lo = df["low"].rolling(int(p["swing"]), min_periods=1).min()
        rr = float(p["rr"])

        # Long khi bar trước chạm dưới lower band VÀ RSI < 30, bar hiện tại đóng trên lower
        cond = (df["close"].shift(1) < lower.shift(1)) & (rsi_v.shift(1) < float(p["rsi_th"])) & (df["close"] > lower)
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
                reason="Mean reversion: giá dưới lower band + RSI<30, đóng trên lower",
            ))
        return signals
