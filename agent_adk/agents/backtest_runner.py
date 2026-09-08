"""backtest_agent — chạy backtest cho strategy_proposal và parse metrics.

Provider mặc định: Gemini (nhanh, rẻ, nhiều call).
"""

from __future__ import annotations

from google.adk.agents import LlmAgent

from ..core.tools_adk import tool_run_backtest
from ..llm import get_llm

BACKTEST_RUNNER_INSTRUCTION = """Bạn là backtest runner. Nhiệm vụ:

INPUT có sẵn trong state:
  - strategy_proposal: JSON {mode, strategy_name, params, rationale}
  - symbol, timeframe

HÀNH ĐỘNG:
1. Parse strategy_proposal để lấy strategy_name và params.
2. Gọi tool_run_backtest(symbol={symbol}, timeframe={timeframe},
                          strategy_name=strategy_name, params=params).
3. Ghi output_key 'backtest_metrics' là JSON:
   {
     "strategy": "...",
     "sharpe": float, "sortino": float, "max_drawdown_pct": float,
     "win_rate": float, "profit_factor": float, "avg_r_multiple": float,
     "n_trades": int, "total_return_pct": float
   }

QUAN TRỌNG: Chỉ chạy backtest, KHÔNG đánh giá. Critic sẽ đánh giá tiếp.
"""

backtest_agent = LlmAgent(
    name="backtest_runner",
    model=get_llm("gemini"),
    instruction=BACKTEST_RUNNER_INSTRUCTION,
    tools=[tool_run_backtest],
    output_key="backtest_metrics",
)

__all__ = ["backtest_agent"]
