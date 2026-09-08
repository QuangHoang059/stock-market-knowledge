"""Cấu hình tập trung cho agent_adk.

Symbol universe: XAUUSD (ưu tiên) + BTCUSD.
Timeframes: 1d, 4h, 1h.
Dataset refresh: 6 ngày gần nhất.
"""

from __future__ import annotations

import os
from pathlib import Path

# --- Đường dẫn ---
ROOT = Path(__file__).resolve().parent.parent  # stock-market-knowledge/
AGENT_DIR = Path(__file__).resolve().parent     # stock-market-knowledge/agent_adk/
CORE_DIR = AGENT_DIR / "core"
DATA_DIR = CORE_DIR / "data"
REPORTS_DIR = AGENT_DIR / "reports"
HISTORY_DIR = REPORTS_DIR / "history"
STRATEGIES_DIR = CORE_DIR / "strategies"
PROVIDERS_ENV = AGENT_DIR / "providers.env"

DATA_DIR.mkdir(parents=True, exist_ok=True)
HISTORY_DIR.mkdir(parents=True, exist_ok=True)


def load_providers_env() -> None:
    """Load GEMINI_API_KEY/ANTHROPIC_API_KEY/DEEPSEEK_API_KEY từ providers.env nếu có."""
    if not PROVIDERS_ENV.exists():
        return
    for raw in PROVIDERS_ENV.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        key, _, val = line.partition("=")
        key = key.strip()
        val = val.strip().strip('"').strip("'")
        if key and val and key not in os.environ:
            os.environ[key] = val


load_providers_env()


# --- Universe ---
SYMBOLS: dict[str, dict[str, str]] = {
    # symbol_key -> {tradingview, yahoo, name_vi, kind}
    "XAUUSD": {
        "tradingview": "TVC:GOLD",
        "yahoo": "GC=F",
        "name_vi": "Vàng spot (USD/oz)",
        "kind": "commodity",
    },
    "BTCUSD": {
        "tradingview": "BINANCE:BTCUSDT",
        "yahoo": "BTC-USD",
        "name_vi": "Bitcoin spot (USD)",
        "kind": "crypto",
    },
}

TIMEFRAMES = ["1d", "4h", "1h"]
TIMEFRAME_TO_YF_INTERVAL = {
    "1d": "1d",
    "4h": "1h",   # yfinance không có 4h native → dùng 1h rồi resample
    "1h": "1h",
}
TIMEFRAME_TO_YF_PERIOD = {
    "1d": "2y",
    "4h": "60d",
    "1h": "60d",
}

# --- Backtest / agent defaults ---
REFRESH_DAYS = 6                    # số ngày gần nhất luôn được refresh
DEFAULT_CAPITAL = 100_000.0         # USD
DEFAULT_RISK_PCT = 0.01             # 1% / lệnh (theo bài 06)
DEFAULT_LOOKBACK_BARS = 252         # ~1 năm dữ liệu daily
MAX_LOOP_ITERATIONS = 5             # vòng lặp tối đa cho LoopAgent

# --- Evaluation thresholds (Critic dùng) ---
MIN_SHARPE = 0.5
MAX_DRAWDOWN_PCT = 20.0
MIN_WIN_RATE = 0.40
MIN_PROFIT_FACTOR = 1.2

# --- Providers ---
SUPPORTED_PROVIDERS = ("claude", "gemini", "deepseek")
DEFAULT_PROVIDER = "claude"


def get_symbol_meta(key: str) -> dict[str, str]:
    if key not in SYMBOLS:
        raise KeyError(f"Unknown symbol '{key}'. Available: {list(SYMBOLS)}")
    return SYMBOLS[key]


def csv_path(symbol: str, timeframe: str) -> Path:
    return DATA_DIR / f"{symbol}_{timeframe}.csv"
