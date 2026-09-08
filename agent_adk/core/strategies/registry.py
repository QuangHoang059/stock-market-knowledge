"""Strategy registry — tra cứu & instantiate theo tên."""

from __future__ import annotations

from typing import Any

from .base import BaseStrategy
from .s01_ema_cross import S01EmaCross
from .s02_breakout_volume import S02BreakoutVolume
from .s03_breakout_retest import S03BreakoutRetest
from .s04_ema20_pullback import S04Ema20Pullback
from .s05_rsi_boll_mr import S05RsiBollMeanReversion
from .s06_boll_squeeze import S06BollSqueeze
from .s07_vwap_pullback import S07VwapPullback
from .s08_macd_ema200 import S08MacdEma200
from .s09_opening_range import S09OpeningRange
from .s10_donchian import S10Donchian

STRATEGY_CLASSES: dict[str, type[BaseStrategy]] = {
    "01-ema-20-50-crossover": S01EmaCross,
    "02-breakout-plus-volume": S02BreakoutVolume,
    "03-breakout-retest": S03BreakoutRetest,
    "04-ema20-pullback": S04Ema20Pullback,
    "05-rsi-bollinger-mean-reversion": S05RsiBollMeanReversion,
    "06-bollinger-squeeze-breakout": S06BollSqueeze,
    "07-vwap-pullback": S07VwapPullback,
    "08-macd-ema200-trend-filter": S08MacdEma200,
    "09-opening-range-breakout": S09OpeningRange,
    "10-donchian-channel-breakout": S10Donchian,
}


def get(name: str, params: dict[str, Any] | None = None) -> BaseStrategy:
    if name not in STRATEGY_CLASSES:
        raise KeyError(f"Unknown strategy '{name}'. Available: {list(STRATEGY_CLASSES)}")
    return STRATEGY_CLASSES[name](params=params)


def all_strategies(params: dict[str, Any] | None = None) -> list[BaseStrategy]:
    return [cls(params=params) for cls in STRATEGY_CLASSES.values()]


__all__ = ["STRATEGY_CLASSES", "get", "all_strategies"]
