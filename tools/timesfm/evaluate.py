"""Walk-forward evaluation cho TimesFM 3.0. Refactor từ `evaluate_timesfm_xauusd.py`."""

from __future__ import annotations

import os
import time
from dataclasses import dataclass, field

# Tránh deadlock khi spawn process bên trong jupyter/parallel
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")

import numpy as np
import pandas as pd

from .data import download_ohlcv, extract_close_array
from .metrics import direction_accuracy, mae, mape, rmse
from .model import ModelLoadError, get_default_device, is_available, load_model


@dataclass
class HorizonMetric:
    """Metric cho 1 horizon."""

    horizon: int
    samples: int
    timesfm_mae: float
    timesfm_rmse: float
    timesfm_mape_pct: float
    timesfm_direction_accuracy_pct: float
    naive_direction_accuracy_pct: float
    direction_improvement_pct: float

    def to_dict(self) -> dict:
        return {
            "horizon": self.horizon,
            "samples": self.samples,
            "timesfm_mae": round(self.timesfm_mae, 6),
            "timesfm_rmse": round(self.timesfm_rmse, 6),
            "timesfm_mape_pct": round(self.timesfm_mape_pct, 4),
            "timesfm_direction_accuracy_pct": round(
                self.timesfm_direction_accuracy_pct, 4
            ),
            "naive_direction_accuracy_pct": round(
                self.naive_direction_accuracy_pct, 4
            ),
            "direction_improvement_pct": round(
                self.direction_improvement_pct, 4
            ),
        }


@dataclass
class EvaluationResult:
    """Kết quả walk-forward evaluation."""

    symbol: str
    interval: str
    period: str
    context_length: int
    horizons: list[int]
    step: int
    n_windows: int
    device: str
    elapsed_seconds: float
    metrics: list[HorizonMetric]
    caveats: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "symbol": self.symbol,
            "interval": self.interval,
            "period": self.period,
            "context_length": self.context_length,
            "horizons": list(self.horizons),
            "step": self.step,
            "n_windows": self.n_windows,
            "device": self.device,
            "elapsed_seconds": round(self.elapsed_seconds, 2),
            "metrics": [m.to_dict() for m in self.metrics],
            "caveats": list(self.caveats),
        }


def _forecast_one(model, context: np.ndarray, horizon: int) -> np.ndarray:
    """Gọi TimesFM 1 lần, trả về forecast array (1-D)."""
    outputs = list(
        model.predict_batch(
            [context],
            horizon=horizon,
            return_quantiles=False,
            use_symmetric_averaging=False,
        )
    )
    if not outputs:
        raise RuntimeError("TimesFM không trả về output")
    return np.asarray(outputs[0].forecast, dtype=float)


def _walk_forward(
    model,
    close: np.ndarray,
    context_length: int,
    horizons: list[int],
    step: int,
    max_samples: int | None,
) -> pd.DataFrame:
    """Chạy walk-forward. Trả về DataFrame với 1 row / window."""
    max_horizon = max(horizons)

    first_origin = context_length
    last_origin = len(close) - max_horizon
    if last_origin <= first_origin:
        raise RuntimeError(
            f"Không đủ dữ liệu cho walk-forward: cần >= "
            f"{first_origin + max_horizon} candles, có {len(close)}"
        )

    origins = list(range(first_origin, last_origin, step))

    if (
        max_samples is not None
        and max_samples > 0
        and len(origins) > max_samples
    ):
        origins = origins[-max_samples:]

    records = []
    total = len(origins)

    for i, origin in enumerate(origins, 1):
        context = close[origin - context_length : origin]
        current_price = float(close[origin - 1])

        try:
            forecast = _forecast_one(model=model, context=context, horizon=max_horizon)
        except Exception as exc:
            print(f"[WARN] window {i}/{total} skip: {exc}")
            continue

        row = {"origin_index": origin, "current_price": current_price}

        for h in horizons:
            pred = float(forecast[h - 1])
            actual = float(close[origin + h - 1])

            row[f"forecast_t{h}"] = pred
            row[f"actual_t{h}"] = actual
            row[f"naive_t{h}"] = current_price  # naive baseline = current price
            row[f"actual_return_t{h}"] = (actual - current_price) / current_price
            row[f"forecast_return_t{h}"] = (pred - current_price) / current_price

        records.append(row)

    if not records:
        raise RuntimeError("Không có window nào hoàn tất walk-forward")

    return pd.DataFrame(records)


def _calculate_metrics(
    results: pd.DataFrame,
    horizons: list[int],
) -> list[HorizonMetric]:
    """Tính MAE/RMSE/MAPE/Direction accuracy theo từng horizon."""
    out: list[HorizonMetric] = []

    current = results["current_price"].to_numpy()

    for h in horizons:
        actual = results[f"actual_t{h}"].to_numpy()
        predicted = results[f"forecast_t{h}"].to_numpy()
        naive = results[f"naive_t{h}"].to_numpy()

        out.append(
            HorizonMetric(
                horizon=h,
                samples=len(actual),
                timesfm_mae=mae(actual, predicted),
                timesfm_rmse=rmse(actual, predicted),
                timesfm_mape_pct=mape(actual, predicted),
                timesfm_direction_accuracy_pct=direction_accuracy(
                    current, actual, predicted
                ),
                naive_direction_accuracy_pct=direction_accuracy(
                    current, actual, naive
                ),
                direction_improvement_pct=0.0,  # set below
            )
        )
        # set improvement
        last = out[-1]
        last.direction_improvement_pct = (
            last.timesfm_direction_accuracy_pct - last.naive_direction_accuracy_pct
        )

    return out


def run_evaluate(
    symbol: str = "GC=F",
    interval: str = "15m",
    period: str = "60d",
    context_length: int = 256,
    horizons: list[int] | None = None,
    step: int = 12,
    max_samples: int = 100,
    device: str | None = None,
) -> EvaluationResult:
    """Walk-forward evaluation.

    Args:
        horizons: danh sách horizon cần đánh giá. Mặc định [1, 3, 6, 12].
        step: bước trượt (candles) giữa 2 window. Mặc định 12.
        max_samples: giới hạn số window cuối dùng. None = dùng tất cả.

    Raises:
        ModelLoadError: nếu thiếu torch/timesfm3.
        RuntimeError: nếu dữ liệu quá ngắn so với context_length + max(horizons).
    """
    if horizons is None:
        horizons = [1, 3, 6, 12]

    if not is_available():
        raise ModelLoadError("torch hoặc timesfm3 chưa cài đặt")

    dev = device or get_default_device()
    start_time = time.time()

    df = download_ohlcv(symbol=symbol, interval=interval, period=period)
    close = extract_close_array(df)

    minimum_required = context_length + max(horizons) + 10
    if len(close) < minimum_required:
        raise RuntimeError(
            f"Không đủ dữ liệu: cần >= {minimum_required}, có {len(close)}"
        )

    model = load_model(dev)

    walk_df = _walk_forward(
        model=model,
        close=close,
        context_length=context_length,
        horizons=list(horizons),
        step=step,
        max_samples=max_samples,
    )

    metrics = _calculate_metrics(results=walk_df, horizons=list(horizons))

    return EvaluationResult(
        symbol=symbol,
        interval=interval,
        period=period,
        context_length=context_length,
        horizons=list(horizons),
        step=step,
        n_windows=len(walk_df),
        device=dev,
        elapsed_seconds=time.time() - start_time,
        metrics=metrics,
        caveats=[
            "Walk-forward trên lịch sử KHÔNG đảm bảo future performance.",
            "Direction accuracy ~52-55% ở horizon 1-6 tốt hơn baseline naive nhưng không đủ tin cậy để giao dịch tự động.",
            "max_samples giới hạn windows lấy từ cuối — đánh giá 1 regime thị trường gần nhất.",
        ],
    )
