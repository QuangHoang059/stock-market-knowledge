"""TimesFM 3.0 forecasting + walk-forward evaluation.

Package này refactor lại 2 script trong repo cũ `strategy-trade/`:
- `forescast_timesfm_xauusd.py` → `tools.timesfm.forecast.run_forecast`
- `evaluate_timesfm_xauusd.py` → `tools.timesfm.evaluate.run_evaluate`

Public API:
    - `run_forecast(...)` — dự báo N bước giá + tín hiệu BUY/HOLD/SELL.
    - `run_evaluate(...)` — walk-forward evaluation với MAE/RMSE/MAPE/Direction.
    - `is_available()` — True nếu torch + timesfm3 đều sẵn sàng.
    - `get_default_device()` — "cuda" nếu có GPU, else "cpu".
    - `compute_signal(...)` — chuyển expected return → BUY/HOLD/SELL.
    - `ForecastResult`, `EvaluationResult` — dataclass + `to_dict()`.
    - `ModelLoadError` — raised khi thiếu torch/timesfm3.

Lệnh CLI:
    $ python -m tools.timesfm.cli forecast --symbol GC=F --horizon 12
    $ python -m tools.timesfm.cli evaluate --symbol GC=F --max-samples 50
"""

from .forecast import run_forecast, ForecastResult
from .evaluate import run_evaluate, EvaluationResult
from .model import (
    is_available,
    get_default_device,
    load_model,
    ModelLoadError,
)
from .signals import compute_signal
from .metrics import mae, rmse, mape, direction_accuracy

__all__ = [
    "run_forecast",
    "ForecastResult",
    "run_evaluate",
    "EvaluationResult",
    "is_available",
    "get_default_device",
    "load_model",
    "ModelLoadError",
    "compute_signal",
    "mae",
    "rmse",
    "mape",
    "direction_accuracy",
]
