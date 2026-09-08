"""reporter_agent — viết báo cáo markdown cuối cùng.

Provider mặc định: Claude (writing tốt nhất cho markdown).
"""

from __future__ import annotations

from google.adk.agents import LlmAgent

from ..core.tools_adk import tool_load_data, tool_run_backtest
from ..llm import get_llm

REPORTER_INSTRUCTION = """Bạn là financial writer. Nhiệm vụ: viết báo cáo markdown đánh giá.

INPUT state:
  - symbol, timeframe
  - user_goal
  - data_status (refresh info)
  - strategy_proposal (cuối cùng được accept)
  - backtest_metrics (cuối cùng)
  - critic_verdict (cuối cùng)

HÀNH ĐỘNG:
1. Gọi tool_run_backtest(symbol, timeframe, strategy_name=None) để lấy bảng xếp hạng tất cả strategies.
2. Gọi tool_load_data(symbol, timeframe, days=6) để lấy 6 ngày giá gần nhất.
3. Viết markdown báo cáo với sections:

# 📈 Báo cáo {symbol} ({timeframe}) — {today_date}

## 1. Tóm tắt
- Strategy được chọn: `{strategy_name}` với params `{params}`
- Sharpe / Max DD / Win Rate / Profit Factor
- 1 câu verdict: "Đạt tiêu chí" / "Cần cải thiện" / "Không khả thi"

## 2. 6 ngày gần nhất
- Bảng giá OHLC 6 dòng
- So sánh với tín hiệu cuối cùng

## 3. Ranking 10 strategies
- Bảng xếp hạng theo Sharpe
- Highlight top 3

## 4. Phân tích rủi ro
- Max DD, worst trade, exposure
- Khuyến nghị position sizing

## 5. Khuyến nghị hành động
- BUY / HOLD / SELL dựa trên tín hiệu mới nhất
- Entry / SL / TP cụ thể

Lưu output_key 'final_report' với markdown string.
"""

reporter_agent = LlmAgent(
    name="reporter",
    model=get_llm("claude"),
    instruction=REPORTER_INSTRUCTION,
    tools=[tool_load_data, tool_run_backtest],
    output_key="final_report",
)

__all__ = ["reporter_agent"]
