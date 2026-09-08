"""Base classes cho chiến lược Python (port từ Pine Script v6).

Mỗi strategy phải implement `generate_signals(df, params=None) -> list[Signal]`.
Trả về tín hiệu LONG/SHORT/EXIT, mỗi signal có entry/stop/target.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable

import pandas as pd


@dataclass(frozen=True)
class Signal:
    ts: pd.Timestamp
    side: str            # "LONG" | "SHORT" | "EXIT"
    entry: float
    stop: float | None = None
    target: float | None = None
    reason: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "ts": str(self.ts),
            "side": self.side,
            "entry": round(self.entry, 4),
            "stop": round(self.stop, 4) if self.stop is not None else None,
            "target": round(self.target, 4) if self.target is not None else None,
            "reason": self.reason,
        }


class BaseStrategy:
    """Lớp cơ sở cho tất cả chiến lược.

    Attributes:
        name: tên duy nhất (same as registry key).
        default_tf: timeframe gợi ý ('1d' | '4h' | '1h').
        default_params: dict tham số mặc định.
        supports_short: chiến lược có cho phép short không.
    """
    name: str = "base"
    default_tf: str = "1d"
    default_params: dict[str, Any] = {}
    supports_short: bool = True

    def __init__(self, params: dict[str, Any] | None = None) -> None:
        self.params = {**self.default_params, **(params or {})}

    def generate(self, df: pd.DataFrame) -> list[Signal]:
        """Wrapper gọi `generate_signals` rồi sắp xếp theo thời gian."""
        out = list(self.generate_signals(df))
        out.sort(key=lambda s: s.ts)
        return out

    def generate_signals(self, df: pd.DataFrame) -> Iterable[Signal]:
        raise NotImplementedError


def require_columns(df: pd.DataFrame, cols: Iterable[str]) -> None:
    missing = [c for c in cols if c not in df.columns]
    if missing:
        raise ValueError(f"DataFrame thiếu columns: {missing}")


def swing_low(df: pd.DataFrame, lookback: int) -> pd.Series:
    return df["low"].rolling(lookback, min_periods=1).min()


def swing_high(df: pd.DataFrame, lookback: int) -> pd.Series:
    return df["high"].rolling(lookback, min_periods=1).max()
