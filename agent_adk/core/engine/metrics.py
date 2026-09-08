"""Metrics: Sharpe, max DD, win rate, profit factor, R-multiple trung bình."""

from __future__ import annotations

import math

import numpy as np
import pandas as pd  # noqa: F401

from .backtest import BacktestResult


def compute_metrics(result: BacktestResult, risk_free_rate: float = 0.0) -> dict[str, float]:
    """Tính metrics từ BacktestResult và gán lại vào result.metrics."""
    eq = result.equity_curve
    trades = result.trades
    metrics: dict[str, float] = {}

    if eq.empty or len(eq) < 2:
        result.metrics = {
            "total_return_pct": 0.0,
            "sharpe": 0.0,
            "sortino": 0.0,
            "max_drawdown_pct": 0.0,
            "win_rate": 0.0,
            "profit_factor": 0.0,
            "avg_r_multiple": 0.0,
            "n_trades": 0,
            "n_wins": 0,
            "n_losses": 0,
            "avg_holding_bars": 0.0,
            "expectancy": 0.0,
        }
        return result.metrics

    # Returns
    rets = eq.pct_change().dropna()
    total_return = float(eq.iloc[-1] / eq.iloc[0] - 1.0)
    metrics["total_return_pct"] = round(total_return * 100, 3)

    # Sharpe (annualized, giả định rets theo ngày)
    if rets.std(ddof=1) > 0:
        sharpe = float((rets.mean() - risk_free_rate / 252) / rets.std(ddof=1) * math.sqrt(252))
    else:
        sharpe = 0.0
    metrics["sharpe"] = round(sharpe, 4)

    # Sortino
    downside = rets[rets < 0]
    if len(downside) > 1 and downside.std(ddof=1) > 0:
        sortino = float((rets.mean() - risk_free_rate / 252) / downside.std(ddof=1) * math.sqrt(252))
    else:
        sortino = 0.0
    metrics["sortino"] = round(sortino, 4)

    # Max drawdown
    running_max = eq.cummax()
    drawdown = (eq - running_max) / running_max
    max_dd = float(drawdown.min()) if not drawdown.empty else 0.0
    metrics["max_drawdown_pct"] = round(abs(max_dd) * 100, 3)

    # Trade stats
    if trades:
        pnls = [t.pnl for t in trades]
        rs = [t.r_multiple for t in trades if t.r_multiple is not None]
        wins = [p for p in pnls if p > 0]
        losses = [p for p in pnls if p <= 0]
        n_trades = len(trades)
        n_wins = len(wins)
        n_losses = len(losses)
        win_rate = n_wins / n_trades if n_trades else 0.0
        gross_profit = sum(wins)
        gross_loss = abs(sum(losses))
        profit_factor = (gross_profit / gross_loss) if gross_loss > 0 else (float("inf") if gross_profit > 0 else 0.0)
        avg_r = float(np.mean(rs)) if rs else 0.0
        avg_hold = float(np.mean([t.bars_held for t in trades]))
        expectancy = (win_rate * (gross_profit / n_wins if n_wins else 0)
                      - (1 - win_rate) * (gross_loss / n_losses if n_losses else 0)) if n_trades else 0.0

        metrics.update({
            "win_rate": round(win_rate, 4),
            "profit_factor": round(min(profit_factor, 99.99), 4),
            "avg_r_multiple": round(avg_r, 4),
            "n_trades": n_trades,
            "n_wins": n_wins,
            "n_losses": n_losses,
            "avg_holding_bars": round(avg_hold, 2),
            "expectancy": round(expectancy, 4),
            "gross_profit": round(gross_profit, 2),
            "gross_loss": round(-gross_loss, 2),
        })
    else:
        metrics.update({
            "win_rate": 0.0, "profit_factor": 0.0, "avg_r_multiple": 0.0,
            "n_trades": 0, "n_wins": 0, "n_losses": 0, "avg_holding_bars": 0.0,
            "expectancy": 0.0, "gross_profit": 0.0, "gross_loss": 0.0,
        })

    result.metrics = metrics
    return metrics


__all__ = ["compute_metrics"]
