"""Pipeline wiring — SequentialAgent + LoopAgent.

Cấu trúc:
    data_refresh → loop(strategy_iteration) → reporter

Loop iteration:
    strategist → backtest_runner → critic (verdict accept/reject dừng loop)
"""

from __future__ import annotations

from google.adk.agents import LoopAgent, SequentialAgent

from .agents import (
    data_refresh_agent,
    strategist_agent,
    backtest_agent,
    critic_agent,
    reporter_agent,
)
from .config import MAX_LOOP_ITERATIONS


# Vòng lặp iterate: Strategist đề xuất → Backtest chạy → Critic chấm → (lặp nếu iterate)
iteration_loop = LoopAgent(
    name="strategy_iteration_loop",
    sub_agents=[strategist_agent, backtest_agent, critic_agent],
    max_iterations=MAX_LOOP_ITERATIONS,
)


# Pipeline đầy đủ: refresh data → loop iteration → reporter
full_pipeline = SequentialAgent(
    name="strategy_evaluation_pipeline",
    sub_agents=[
        data_refresh_agent,    # refresh 6 ngày + verify
        iteration_loop,        # strategist ↔ backtest ↔ critic
        reporter_agent,        # viết báo cáo cuối
    ],
)


__all__ = ["full_pipeline", "iteration_loop"]
