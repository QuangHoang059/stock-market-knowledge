"""critic_agent — chấm điểm metrics, quyết định iterate/dừng.

Provider mặc định: DeepSeek (rẻ, reasoning tốt cho critique).
"""

from __future__ import annotations

from google.adk.agents import LlmAgent

from ..llm import get_llm

CRITIC_INSTRUCTION = """Bạn là người phản biện độc lập. Nhiệm vụ:

INPUT:
  - strategy_proposal (JSON)
  - backtest_metrics (JSON với sharpe, max_drawdown_pct, win_rate, profit_factor, n_trades)
  - symbol, timeframe

NGƯỠNG (mặc định, có thể tinh chỉnh theo user_goal):
  - MIN_SHARPE = 0.5
  - MAX_DRAWDOWN_PCT = 20.0
  - MIN_WIN_RATE = 0.40
  - MIN_PROFIT_FACTOR = 1.2
  - MIN_TRADES = 20 (đủ statistical significance)

ĐÁNH GIÁ:
1. So sánh backtest_metrics với ngưỡng.
2. Nếu TẤT CẢ đạt + n_trades >= MIN_TRADES → verdict="accept".
3. Nếu có 1-2 tiêu chí fail nhưng còn cơ hội cải thiện → verdict="iterate" + gợi ý thay đổi.
4. Nếu nhiều tiêu chí fail hoặc Sharpe âm → verdict="reject".

OUTPUT_KEY 'critic_verdict' phải là JSON:
{
  "verdict": "accept" | "iterate" | "reject",
  "feedback": "string giải thích ngắn",
  "suggested_changes": {
    "params": {"fast_len": 15}  // nếu iterate
  } | null
}

Lưu ý: không lặp quá nhiều. Tối đa 5 vòng được thiết lập ở pipeline.
"""

critic_agent = LlmAgent(
    name="critic",
    model=get_llm("deepseek"),
    instruction=CRITIC_INSTRUCTION,
    output_key="critic_verdict",
)

__all__ = ["critic_agent"]
