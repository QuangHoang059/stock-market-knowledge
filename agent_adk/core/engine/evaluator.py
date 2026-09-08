"""Evaluator — chạy backtest cho tất cả strategies, rank theo metrics, xuất markdown."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import pandas as pd

from ..strategies.registry import all_strategies, get as get_strategy
from ..data_loader import load
from .backtest import backtest, BacktestResult
from .metrics import compute_metrics

from ...config import DEFAULT_CAPITAL, DEFAULT_RISK_PCT


@dataclass
class EvaluationReport:
    symbol: str
    timeframe: str
    period_start: pd.Timestamp
    period_end: pd.Timestamp
    results: list[BacktestResult]
    ranked: list[BacktestResult] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "symbol": self.symbol,
            "timeframe": self.timeframe,
            "period_start": str(self.period_start),
            "period_end": str(self.period_end),
            "strategies": [r.metrics | {"name": r.strategy, "params": r.params} for r in self.results],
            "ranked": [r.strategy for r in self.ranked],
        }

    def to_markdown(self) -> str:
        lines: list[str] = []
        lines.append(f"# Evaluation: {self.symbol} ({self.timeframe})")
        lines.append("")
        lines.append(f"**Period:** {self.period_start.date()} -> {self.period_end.date()}")
        lines.append(f"**Capital:** ${DEFAULT_CAPITAL:,.0f}  |  **Risk/Trade:** {DEFAULT_RISK_PCT*100:.1f}%")
        lines.append("")
        lines.append("## Ranking theo Sharpe")
        lines.append("")
        lines.append("| # | Strategy | Sharpe | Sortino | Max DD % | Win Rate | Profit Factor | Avg R | Trades |")
        lines.append("|---|----------|-------:|--------:|---------:|---------:|--------------:|------:|-------:|")
        for r in self.ranked:
            m = r.metrics
            lines.append(
                f"| {self.ranked.index(r)+1} | `{r.strategy}` "
                f"| {m.get('sharpe', 0):.2f} "
                f"| {m.get('sortino', 0):.2f} "
                f"| {m.get('max_drawdown_pct', 0):.1f} "
                f"| {m.get('win_rate', 0)*100:.1f}% "
                f"| {m.get('profit_factor', 0):.2f} "
                f"| {m.get('avg_r_multiple', 0):.2f} "
                f"| {m.get('n_trades', 0)} |"
            )
        lines.append("")
        lines.append("## Top 3 chi tiết")
        lines.append("")
        for r in self.ranked[:3]:
            lines.append(f"### `{r.strategy}`")
            lines.append("")
            lines.append(f"- Params: `{r.params}`")
            lines.append(f"- Total return: **{r.metrics.get('total_return_pct', 0):.2f}%**")
            lines.append(f"- Sharpe: {r.metrics.get('sharpe', 0):.3f}")
            lines.append(f"- Max drawdown: {r.metrics.get('max_drawdown_pct', 0):.2f}%")
            lines.append(f"- Win rate: {r.metrics.get('win_rate', 0)*100:.1f}%")
            lines.append(f"- Profit factor: {r.metrics.get('profit_factor', 0):.2f}")
            lines.append(f"- Avg R-multiple: {r.metrics.get('avg_r_multiple', 0):.2f}")
            lines.append(f"- Trades: {r.metrics.get('n_trades', 0)} ({r.metrics.get('n_wins', 0)}W / {r.metrics.get('n_losses', 0)}L)")
            lines.append("")
        return "\n".join(lines)


def evaluate_all(
    symbol: str,
    timeframe: str = "1d",
    df: pd.DataFrame | None = None,
    params: dict[str, dict[str, Any]] | None = None,
    capital: float = DEFAULT_CAPITAL,
    risk_pct: float = DEFAULT_RISK_PCT,
    sort_by: str = "sharpe",
) -> EvaluationReport:
    """Chạy backtest tất cả strategies trên symbol/timeframe.

    Args:
        symbol, timeframe: nếu df=None sẽ tự load.
        df: DataFrame (đã sort, có timestamp/open/high/low/close/volume).
        params: dict override params cho từng strategy key.
    """
    if df is None:
        df = load(symbol, timeframe)
    if df.empty:
        raise ValueError(f"Empty DataFrame for {symbol}/{timeframe}")

    results: list[BacktestResult] = []
    for strat in all_strategies():
        p = (params or {}).get(strat.name, None)
        instance = get_strategy(strat.name, params=p)
        result = backtest(df, instance, symbol=symbol, timeframe=timeframe,
                          capital=capital, risk_pct=risk_pct)
        compute_metrics(result)
        results.append(result)

    ranked = sorted(results, key=lambda r: r.metrics.get(sort_by, 0.0), reverse=True)

    return EvaluationReport(
        symbol=symbol,
        timeframe=timeframe,
        period_start=df["timestamp"].iloc[0],
        period_end=df["timestamp"].iloc[-1],
        results=results,
        ranked=ranked,
    )


def evaluate_strategy(
    name: str,
    symbol: str,
    timeframe: str = "1d",
    params: dict[str, Any] | None = None,
    df: pd.DataFrame | None = None,
    capital: float = DEFAULT_CAPITAL,
    risk_pct: float = DEFAULT_RISK_PCT,
) -> BacktestResult:
    """Backtest 1 strategy cụ thể."""
    if df is None:
        df = load(symbol, timeframe)
    strat = get_strategy(name, params=params)
    result = backtest(df, strat, symbol=symbol, timeframe=timeframe,
                      capital=capital, risk_pct=risk_pct)
    compute_metrics(result)
    return result


__all__ = ["evaluate_all", "evaluate_strategy", "EvaluationReport"]
