"""Pure-numpy evaluation metrics. Tách khỏi model để unit-test không cần torch."""

from __future__ import annotations

import numpy as np


def mae(actual: np.ndarray | list[float], predicted: np.ndarray | list[float]) -> float:
    """Mean Absolute Error."""
    actual_arr = np.asarray(actual, dtype=float)
    predicted_arr = np.asarray(predicted, dtype=float)
    return float(np.mean(np.abs(actual_arr - predicted_arr)))


def rmse(actual: np.ndarray | list[float], predicted: np.ndarray | list[float]) -> float:
    """Root Mean Squared Error."""
    actual_arr = np.asarray(actual, dtype=float)
    predicted_arr = np.asarray(predicted, dtype=float)
    return float(np.sqrt(np.mean((actual_arr - predicted_arr) ** 2)))


def mape(actual: np.ndarray | list[float], predicted: np.ndarray | list[float]) -> float:
    """Mean Absolute Percentage Error (%). NaN nếu mọi `|actual| < 1e-12`."""
    actual_arr = np.asarray(actual, dtype=float)
    predicted_arr = np.asarray(predicted, dtype=float)

    mask = np.abs(actual_arr) > 1e-12
    if not np.any(mask):
        return float("nan")

    return float(
        np.mean(np.abs((actual_arr[mask] - predicted_arr[mask]) / actual_arr[mask])) * 100
    )


def direction_accuracy(
    current: np.ndarray | list[float],
    actual: np.ndarray | list[float],
    predicted: np.ndarray | list[float],
) -> float:
    """Tỷ lệ (%) forecast ĐÚNG chiều (lên/xuống) so với ground-truth.

    Bỏ qua các mẫu mà `actual` không đổi so với `current` (direction = 0).
    """
    current_arr = np.asarray(current, dtype=float)
    actual_arr = np.asarray(actual, dtype=float)
    predicted_arr = np.asarray(predicted, dtype=float)

    actual_direction = np.sign(actual_arr - current_arr)
    predicted_direction = np.sign(predicted_arr - current_arr)

    mask = actual_direction != 0
    if not np.any(mask):
        return float("nan")

    return float(np.mean(actual_direction[mask] == predicted_direction[mask]) * 100)


def naive_direction_accuracy(
    current: np.ndarray | list[float],
    actual: np.ndarray | list[float],
) -> float:
    """Baseline: luôn đoán "không đổi" → direction luôn sai khi actual đổi.

    Trả về 0% (vì predicted = current → predicted_direction = 0).
    """
    _ = (current, actual)  # Tránh unused
    return 0.0
