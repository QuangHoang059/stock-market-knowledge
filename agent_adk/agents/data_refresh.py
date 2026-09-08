"""data_refresh_agent — refresh dataset CSV cho symbol, chuẩn bị cho backtest."""

from __future__ import annotations

from google.adk.agents import LlmAgent

from ..core.tools_adk import tool_refresh_data, tool_load_data
from ..llm import get_llm

DATA_REFRESH_INSTRUCTION = """Bạn là data steward. Nhiệm vụ duy nhất:

1. Gọi tool refresh_data với {symbol} và {timeframe} và days=6 để cập nhật CSV.
2. Gọi tool load_data với cùng {symbol}/{timeframe} để verify dataset đã sẵn sàng.
3. Trong output_key 'data_status', ghi JSON:
   {"symbol": "...", "timeframe": "...", "rows": N, "last_date": "...", "ready": true}

Nếu rows < 50 → set ready=false và báo lỗi. Nếu OK → ready=true.
"""

data_refresh_agent = LlmAgent(
    name="data_refresh",
    model=get_llm(),
    instruction=DATA_REFRESH_INSTRUCTION,
    tools=[tool_refresh_data, tool_load_data],
    output_key="data_status",
)

__all__ = ["data_refresh_agent"]
