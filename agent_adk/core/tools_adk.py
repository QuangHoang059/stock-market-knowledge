"""ADK FunctionTool wrappers — kết nối các hàm core với ADK agents.

Mỗi tool được wrap bằng FunctionTool từ google.adk.tools, để LlmAgent có thể gọi.
"""

from __future__ import annotations

from google.adk.tools.function_tool import FunctionTool

from .data_loader import download as _download, refresh as _refresh, load as _load, last_n_days as _last_n
from .engine.evaluator import evaluate_all as _evaluate_all, evaluate_strategy as _evaluate_strategy
from .strategies.registry import all_strategies as _all_strategies

from ..config import REFRESH_DAYS


def refresh_data(symbol: str, timeframe: str = "1d", days: int = REFRESH_DAYS) -> dict:
    """Refresh dataset CSV cho symbol/timeframe — append N ngày gần nhất.

    Args:
        symbol: mã, ví dụ 'XAUUSD' hoặc 'BTCUSD'.
        timeframe: '1d' | '4h' | '1h'.
        days: số ngày overlap với CSV hiện tại (mặc định 6).

    Returns:
        dict: {symbol, timeframe, rows, first_date, last_date, source}
    """
    res = _refresh(symbol, timeframe, days=days)
    return {
        "symbol": res.symbol,
        "timeframe": res.timeframe,
        "rows": res.rows,
        "first_date": str(res.first_date),
        "last_date": str(res.last_date),
        "source": res.source,
    }


def load_data(symbol: str, timeframe: str = "1d", days: int | None = None) -> dict:
    """Load OHLCV từ CSV cache. Nếu days được truyền → chỉ lấy N ngày gần nhất.

    Returns:
        dict với 'rows', 'first_date', 'last_date', 'sample' (5 dòng đầu JSON-serializable).
    """
    df = _load(symbol, timeframe)
    if days is not None:
        df = _last_n(df, days)
    if df.empty:
        return {"rows": 0, "first_date": None, "last_date": None, "sample": []}
    sample = df.head(5).assign(timestamp=df["timestamp"].astype(str)).to_dict(orient="records")
    return {
        "rows": len(df),
        "first_date": str(df["timestamp"].iloc[0]),
        "last_date": str(df["timestamp"].iloc[-1]),
        "last_close": float(df["close"].iloc[-1]),
        "sample": sample,
    }


def run_backtest(
    symbol: str,
    timeframe: str = "1d",
    strategy_name: str | None = None,
    params: dict | None = None,
) -> dict:
    """Chạy backtest cho 1 strategy (hoặc tất cả nếu strategy_name=None).

    Returns:
        dict với 'results': list metrics, hoặc 'metrics' nếu 1 strategy.
    """
    if strategy_name:
        res = _evaluate_strategy(name=strategy_name, symbol=symbol,
                                  timeframe=timeframe, params=params)
        return {"strategy": res.strategy, "metrics": res.metrics, "n_trades": res.n_trades}
    else:
        report = _evaluate_all(symbol=symbol, timeframe=timeframe, params=params)
        return {
            "symbol": report.symbol,
            "timeframe": report.timeframe,
            "ranked": report.to_dict()["ranked"],
            "results": report.to_dict()["strategies"],
        }


def list_strategies() -> dict:
    """Liệt kê tất cả strategies đã đăng ký + params mặc định."""
    out = []
    for cls in _all_strategies():
        out.append({
            "name": cls.name,
            "default_tf": cls.default_tf,
            "default_params": cls.default_params,
            "supports_short": cls.supports_short,
        })
    return {"count": len(out), "strategies": out}


def download_data(symbol: str, timeframe: str = "1d", period: str | None = None) -> dict:
    """Tải dataset đầy đủ cho symbol/timeframe (ghi đè CSV).

    period: '1y' | '2y' | '60d' | None (mặc định theo timeframe).
    """
    res = _download(symbol, timeframe, period=period, overwrite=True)
    return {
        "symbol": res.symbol, "timeframe": res.timeframe, "rows": res.rows,
        "first_date": str(res.first_date), "last_date": str(res.last_date),
        "source": res.source,
    }


tool_refresh_data = FunctionTool(refresh_data)
tool_load_data = FunctionTool(load_data)
tool_run_backtest = FunctionTool(run_backtest)
tool_list_strategies = FunctionTool(list_strategies)
tool_download_data = FunctionTool(download_data)


__all__ = [
    "tool_refresh_data", "tool_load_data", "tool_run_backtest",
    "tool_list_strategies", "tool_download_data",
    "refresh_data", "load_data", "run_backtest", "list_strategies", "download_data",
]
