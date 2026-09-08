"""strategist_agent — đề xuất tham số/chiến lược mới dựa trên goal.

Provider mặc định: Claude (mạnh về code reasoning).
"""

from __future__ import annotations

from google.adk.agents import LlmAgent

from ..core.tools_adk import tool_list_strategies, tool_run_backtest, tool_load_data
from ..llm import get_llm

STRATEGIST_INSTRUCTION = """Bạn là chiến lược gia quantitative. Nhiệm vụ:

INPUT có sẵn trong state:
  - user_goal: mục tiêu (vd: 'tìm chiến lược XAUUSD trending, max DD<15%')
  - symbol, timeframe
  - data_status: từ data_refresh_agent

QUY TRÌNH:
1. Gọi tool_list_strategies để biết 10 strategies có sẵn + params mặc định.
2. Gọi tool_run_backtest để chạy baseline cho TẤT CẢ strategies (strategy_name=None).
3. Đọc metrics → chọn 1 strategy có Sharpe cao nhất HOẶC có nhiều tín hiệu nhất.
4. Đề xuất điều chỉnh (đổi params) HOẶC đề xuất strategy mới hoàn toàn.

OUTPUT_KEY 'strategy_proposal' phải là JSON hợp lệ:
{
  "mode": "tune" | "new",
  "strategy_name": "01-ema-20-50-crossover",
  "params": {"fast_len": 20, "slow_len": 50, ...},
  "rationale": "string giải thích ngắn gọn"
}

Lưu ý:
- Mỗi lần gọi, bạn có thể đề xuất 1 thay đổi nhỏ (vd: fast_len 20→15).
- Không đề xuất thay đổi quá nhiều tham số cùng lúc (tránh overfit).
- Nếu Sharpe baseline đã > 0.8 → chỉ tinh chỉnh nhẹ, không thay đổi lớn.
"""

strategist_agent = LlmAgent(
    name="strategist",
    model=get_llm("claude"),
    instruction=STRATEGIST_INSTRUCTION,
    tools=[tool_list_strategies, tool_run_backtest, tool_load_data],
    output_key="strategy_proposal",
)

__all__ = ["strategist_agent"]
