"""agent_adk — Google ADK based strategy evaluator.

Cấu trúc:
    core/         pure Python (data, strategies, backtest engine)
    core/tools_adk.py  ADK FunctionTool wrappers
    agents/       ADK LlmAgent definitions (Strategist, Backtest, Critic, Reporter)
    pipeline.py   LoopAgent + SequentialAgent wiring
    runner.py     InMemoryRunner + CLI
    scripts/      CLI bootstrap (download, refresh, evaluate_only)
    reports/      Markdown output
"""

__version__ = "0.1.0"
