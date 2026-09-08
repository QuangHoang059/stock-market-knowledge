"""Forecast N bước giá bằng TimesFM 3.0. Refactor từ `forescast_timesfm_xauusd.py`."""

from __future__ import annotations

import time
from dataclasses import dataclass, field

import numpy as np

from .data import download_ohlcv, extract_close_array, take_last_n
from .model import (
    ModelLoadError,
    get_default_device,
    is_available,
    load_model,
)
from .signals import compute_signal


@dataclass
class ForecastResult:
    """Kết quả forecast N bước. `to_dict()` cho MCP JSON serialization."""

    symbol: str
    interval: str
    period: str
    context_length: int
    horizon: int
    current_price: float
    forecast_prices: list[float]
    expected_returns_pct: list[float]
    expected_return_pct: float
    signal: str
    device: str
    elapsed_seconds: float
    caveats: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "symbol": self.symbol,
            "interval": self.interval,
            "period": self.period,
            "context_length": self.context_length,
            "horizon": self.horizon,
            "current_price": round(self.current_price, 4),
            "forecast_prices": [round(p, 4) for p in self.forecast_prices],
            "expected_returns_pct": [round(r, 4) for r in self.expected_returns_pct],
            "expected_return_pct": round(self.expected_return_pct, 4),
            "signal": self.signal,
            "device": self.device,
            "elapsed_seconds": round(self.elapsed_seconds, 2),
            "caveats": list(self.caveats),
        }


def run_forecast(
    symbol: str = "GC=F",
    interval: str = "15m",
    period: str = "60d",
    context_length: int = 256,
    horizon: int = 12,
    buy_threshold: float = 0.002,
    sell_threshold: float = -0.002,
    device: str | None = None,
) -> ForecastResult:
    """Forecast N bước giá + tín hiệu BUY/HOLD/SELL.

    Raises:
        ModelLoadError: nếu thiếu torch/timesfm3.
        RuntimeError: nếu tải dữ liệu thất bại hoặc context_length > len(close).

    Note:
        Lần đầu chạy sẽ download checkpoint ~500MB từ HuggingFace
        (`google/timesfm-3.0-pytorch`). Cache ở ~/.cache/huggingface.
    """
    if not is_available():
        raise ModelLoadError("torch hoặc timesfm3 chưa cài đặt")

    dev = device or get_default_device()
    start_time = time.time()

    df = download_ohlcv(symbol=symbol, interval=interval, period=period)
    close = extract_close_array(df)
    context = take_last_n(close, context_length)

    model = load_model(dev)

    outputs = list(
        model.predict_batch(
            [context],
            horizon=horizon,
            return_quantiles=True,
            use_symmetric_averaging=False,
        )
    )

    if not outputs:
        raise RuntimeError("TimesFM không trả về output")

    forecast = np.asarray(outputs[0].forecast, dtype=float).tolist()

    current_price = float(close[-1])

    expected_returns_pct = [
        ((p - current_price) / current_price) * 100 for p in forecast
    ]

    future_price = forecast[-1]
    expected_return_pct = (future_price - current_price) / current_price * 100

    signal = compute_signal(
        expected_return=expected_return_pct / 100,  # compute_signal expects decimal
        buy_threshold=buy_threshold,
        sell_threshold=sell_threshold,
    )

    return ForecastResult(
        symbol=symbol,
        interval=interval,
        period=period,
        context_length=context_length,
        horizon=horizon,
        current_price=current_price,
        forecast_prices=forecast,
        expected_returns_pct=expected_returns_pct,
        expected_return_pct=expected_return_pct,
        signal=signal,
        device=dev,
        elapsed_seconds=time.time() - start_time,
        caveats=[
            "forecast_prices là POINT estimate — không có confidence interval trong tool này.",
            "signal BUY/HOLD/SELL dựa trên expected_return_pct vs threshold.",
            "KHÔNG phải khuyến nghị đầu tư — kiểm tra thêm với strategy + position sizing.",
        ],
    )
