"""Vectorized bar-by-bar backtest engine.

Mỗi signal mở 1 vị thế (long hoặc short). Vị thế được đóng khi:
- Chạm SL
- Chạm TP
- Có signal ngược chiều (flat → reverse)
- Hết data

Position size dùng tools.risk.position_size (1% vốn mỗi lệnh).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np  # noqa: F401
import pandas as pd

from ..strategies.base import BaseStrategy
from tools.risk import position_size

from ...config import DEFAULT_CAPITAL, DEFAULT_RISK_PCT


@dataclass
class Trade:
    side: str              # "LONG" | "SHORT"
    entry_ts: pd.Timestamp
    exit_ts: pd.Timestamp | None
    entry: float
    exit: float | None
    stop: float
    target: float | None
    qty: float
    pnl: float             # USD (đã tính phí chưa — fee 0 ở phase này)
    r_multiple: float | None   # pnl / risk_per_unit
    bars_held: int
    exit_reason: str       # "TP" | "SL" | "REVERSE" | "EOD"


@dataclass
class BacktestResult:
    strategy: str
    symbol: str
    timeframe: str
    params: dict[str, Any]
    n_signals: int
    n_trades: int
    equity_curve: pd.Series      # indexed by timestamp
    trades: list[Trade] = field(default_factory=list)
    metrics: dict[str, float] = field(default_factory=dict)


def _close_trade(
    trade: Trade, exit_price: float, exit_ts: pd.Timestamp, bars: int, reason: str, sign: int,
) -> None:
    trade.exit = exit_price
    trade.exit_ts = exit_ts
    trade.bars_held = bars
    trade.exit_reason = reason
    risk_per_unit = abs(trade.entry - trade.stop)
    if sign > 0:
        trade.pnl = (exit_price - trade.entry) * trade.qty
    else:
        trade.pnl = (trade.entry - exit_price) * trade.qty
    trade.r_multiple = (trade.pnl / (risk_per_unit * trade.qty)) if (risk_per_unit > 0 and trade.qty > 0) else None


def backtest(
    df: pd.DataFrame,
    strategy: BaseStrategy,
    symbol: str = "?",
    timeframe: str = "1d",
    capital: float = DEFAULT_CAPITAL,
    risk_pct: float = DEFAULT_RISK_PCT,
    fee_pct: float = 0.0005,     # 0.05% per side (gold spot typical)
) -> BacktestResult:
    """Chạy backtest cho 1 strategy trên DataFrame.

    Args:
        df: phải có columns timestamp, open, high, low, close, volume (đã sort).
        strategy: instance của BaseStrategy.
        symbol, timeframe: chỉ để ghi metadata.
        capital: vốn USD ban đầu.
        risk_pct: rủi ro mỗi lệnh (decimal).
        fee_pct: phí giao dịch mỗi lệnh (decimal, mỗi side).

    Returns:
        BacktestResult với trades[] và metrics dict.
    """
    if df.empty:
        return BacktestResult(strategy=strategy.name, symbol=symbol, timeframe=timeframe,
                              params=strategy.params, n_signals=0, n_trades=0,
                              equity_curve=pd.Series(dtype=float))

    signals = sorted(strategy.generate(df), key=lambda s: s.ts)
    sig_idx = {s.ts: s for s in signals}

    equity = capital
    equity_curve_pts: list[tuple[pd.Timestamp, float]] = [(df["timestamp"].iloc[0], equity)]
    trades: list[Trade] = []

    open_trade: Trade | None = None
    current_sign: int = 0   # +1 long, -1 short, 0 flat

    df_iter = df.reset_index(drop=True)
    sig_set = set(sig_idx.keys())

    for i in range(len(df_iter)):
        ts = df_iter["timestamp"].iloc[i]
        high = float(df_iter["high"].iloc[i])
        low = float(df_iter["low"].iloc[i])
        close = float(df_iter["close"].iloc[i])

        sign_at_bar = sig_set.intersection({ts})
        new_signal = sig_idx.get(ts) if sign_at_bar else None

        # 1) Mở vị thế mới (chưa có open_trade) khi có signal
        if open_trade is None and new_signal is not None:
            try:
                rp = position_size(capital=equity, risk_pct=risk_pct,
                                   entry=new_signal.entry, stop=new_signal.stop or new_signal.entry * 0.98)
                qty = rp.shares
            except Exception:
                qty = 0.0
            if qty > 0 and new_signal.stop is not None:
                open_trade = Trade(
                    side=new_signal.side, entry_ts=ts, exit_ts=None,
                    entry=new_signal.entry, exit=None,
                    stop=new_signal.stop, target=new_signal.target,
                    qty=qty, pnl=0.0, r_multiple=None,
                    bars_held=0, exit_reason="",
                )
                current_sign = 1 if new_signal.side == "LONG" else -1
                # Trừ phí vào
                equity -= abs(qty * new_signal.entry) * fee_pct

        # 2) Đóng vị thế đang mở
        elif open_trade is not None:
            sign = current_sign
            stop_price = open_trade.stop
            target_price = open_trade.target

            hit_sl = (sign > 0 and low <= stop_price) or (sign < 0 and high >= stop_price)
            hit_tp = (
                target_price is not None
                and ((sign > 0 and high >= target_price) or (sign < 0 and low <= target_price))
            )
            reverse_signal = (
                new_signal is not None
                and (
                    (sign > 0 and new_signal.side == "SHORT")
                    or (sign < 0 and new_signal.side == "LONG")
                )
            )

            # Xác định thứ tự: nếu cùng bar, ưu tiên SL trước (worst case) trừ khi TP rõ ràng trước
            exit_price = None
            exit_reason = None
            if hit_sl and hit_tp:
                # Không biết thứ tự — mặc định SL (conservative)
                exit_price = stop_price
                exit_reason = "SL"
            elif hit_sl:
                exit_price = stop_price
                exit_reason = "SL"
            elif hit_tp:
                exit_price = target_price
                exit_reason = "TP"
            elif reverse_signal:
                exit_price = close
                exit_reason = "REVERSE"

            if exit_price is not None:
                assert exit_reason is not None
                _close_trade(open_trade, exit_price, ts,
                             bars=i - df.index[df["timestamp"] == open_trade.entry_ts][0]
                             if (df["timestamp"] == open_trade.entry_ts).any() else 0,
                             reason=exit_reason, sign=sign)
                # Trừ phí ra
                equity += open_trade.pnl
                equity -= abs(open_trade.qty * exit_price) * fee_pct
                trades.append(open_trade)
                open_trade = None
                current_sign = 0

                # Nếu là reverse, mở vị thế mới ngay bar này
                if exit_reason == "REVERSE" and new_signal is not None:
                    try:
                        rp = position_size(capital=equity, risk_pct=risk_pct,
                                           entry=new_signal.entry, stop=new_signal.stop or new_signal.entry * 0.98)
                        qty = rp.shares
                    except Exception:
                        qty = 0.0
                    if qty > 0 and new_signal.stop is not None:
                        open_trade = Trade(
                            side=new_signal.side, entry_ts=ts, exit_ts=None,
                            entry=new_signal.entry, exit=None,
                            stop=new_signal.stop, target=new_signal.target,
                            qty=qty, pnl=0.0, r_multiple=None,
                            bars_held=0, exit_reason="",
                        )
                        current_sign = 1 if new_signal.side == "LONG" else -1
                        equity -= abs(qty * new_signal.entry) * fee_pct

        equity_curve_pts.append((ts, equity))

    # Đóng vị thế cuối nếu còn
    if open_trade is not None:
        last_close = float(df["close"].iloc[-1])
        _close_trade(open_trade, last_close, df["timestamp"].iloc[-1],
                     bars=len(df) - 1, reason="EOD", sign=current_sign)
        equity += open_trade.pnl
        equity -= abs(open_trade.qty * last_close) * fee_pct
        trades.append(open_trade)

    equity_curve = pd.Series(
        [v for _, v in equity_curve_pts],
        index=[t for t, _ in equity_curve_pts],
        name="equity",
    )

    return BacktestResult(
        strategy=strategy.name,
        symbol=symbol,
        timeframe=timeframe,
        params=strategy.params,
        n_signals=len(signals),
        n_trades=len(trades),
        equity_curve=equity_curve,
        trades=trades,
        metrics={},   # sẽ tính ở metrics.py
    )


__all__ = ["backtest", "BacktestResult", "Trade"]
