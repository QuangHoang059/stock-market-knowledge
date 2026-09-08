"""Lazy loader cho TimesFM 3.0 model.

Cố ý KHÔNG import torch/timesfm3 ở module top-level. Probe 1 lần khi import
module này để set cờ `_TORCH_OK` / `_TIMESFM_OK`. Import thật chỉ xảy ra bên
trong `load_model()` — cho phép MCP server khởi động kể cả khi user chưa copy
`timesfm3/` vào repo.
"""

from __future__ import annotations

from typing import Any

_TIMESFM_OK: bool = False
_TORCH_OK: bool = False
_PROBE_DONE: bool = False


class ModelLoadError(RuntimeError):
    """Raised khi torch hoặc timesfm3 chưa sẵn sàng."""


def _probe_dependencies() -> None:
    """Set cờ global 1 lần. Không raise — để MCP server vẫn khởi động được.

    Catch cả `ImportError` VÀ `OSError`/`RuntimeError` vì torch có thể đã cài
    nhưng DLL init fail (thiếu CUDA runtime trên VPS không GPU).
    """
    global _TORCH_OK, _TIMESFM_OK, _PROBE_DONE
    if _PROBE_DONE:
        return

    try:
        __import__("torch")
        _TORCH_OK = True
    except (ImportError, OSError, RuntimeError):
        _TORCH_OK = False

    try:
        __import__("timesfm3")
        _TIMESFM_OK = True
    except (ImportError, OSError, RuntimeError):
        _TIMESFM_OK = False

    _PROBE_DONE = True


_probe_dependencies()


def is_available() -> bool:
    """True nếu cả `torch` lẫn `timesfm3` đều đã cài."""
    return _TORCH_OK and _TIMESFM_OK


def get_default_device() -> str:
    """`"cuda"` nếu có GPU, else `"cpu"`. Trả `"cpu"` khi thiếu torch."""
    if not _TORCH_OK:
        return "cpu"
    try:
        import torch

        return "cuda" if torch.cuda.is_available() else "cpu"
    except Exception:
        return "cpu"


def get_availability_status() -> dict[str, Any]:
    """Trả về dict chi tiết — dùng cho MCP error JSON."""
    return {
        "torch_ok": _TORCH_OK,
        "timesfm3_ok": _TIMESFM_OK,
        "available": _TORCH_OK and _TIMESFM_OK,
        "default_device": get_default_device(),
        "hint": (
            "pip install -r requirements-ml.txt để cài torch CPU-only. "
            "Sau đó copy thư mục timesfm3/ từ Google upstream (google-research/timesfm) "
            "vào stock-market-knowledge/timesfm3/."
        ),
    }


def load_model(device: str | None = None) -> Any:
    """Lazy-load TimesFM 3.0 evaluator. Raise `ModelLoadError` nếu thiếu dep."""
    if not _TORCH_OK:
        raise ModelLoadError(
            "torch chưa cài. Chạy: pip install -r requirements-ml.txt"
        )
    if not _TIMESFM_OK:
        raise ModelLoadError(
            "timesfm3 chưa có trong repo. Copy thư mục timesfm3/ từ Google "
            "upstream (google-research/timesfm) vào stock-market-knowledge/timesfm3/"
        )

    # Import động — chỉ fail ở đây nếu torch/timesfm3 thực sự lỗi.
    # Dùng `__import__` + `getattr` để tránh Pyright báo missing import
    # (timesfm3 được copy vào repo sau khi merge xong).
    timesfm3_mod = __import__(
        "timesfm3",
        fromlist=["TimesFM3Evaluator", "ModelConfig"],
    )
    TimesFM3Evaluator = getattr(timesfm3_mod, "TimesFM3Evaluator")
    ModelConfig = getattr(timesfm3_mod, "ModelConfig")

    dev = device or get_default_device()

    config = ModelConfig(
        checkpoint_path="google/timesfm-3.0-pytorch",
        per_core_batch_size=1,
        device=dev,
    )

    return TimesFM3Evaluator(config)
