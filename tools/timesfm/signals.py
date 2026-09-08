"""Tín hiệu BUY/HOLD/SELL từ expected return (pure logic, không phụ thuộc torch)."""

from __future__ import annotations


def compute_signal(
    expected_return: float,
    buy_threshold: float = 0.002,
    sell_threshold: float = -0.002,
) -> str:
    """Trả về "BUY" | "HOLD" | "SELL".

    Args:
        expected_return: tỷ suất sinh lợi kỳ vọng (vd: 0.012 = +1.2%).
        buy_threshold: mức trên → BUY. Mặc định +0.2%.
        sell_threshold: mức dưới → SELL. Mặc định -0.2%.

    Raises:
        ValueError: nếu `sell_threshold > buy_threshold`.

    Quy ước:
        expected >= buy_threshold           → "BUY"
        expected <= sell_threshold          → "SELL"
        còn lại                             → "HOLD"
    """
    if sell_threshold > buy_threshold:
        raise ValueError(
            f"sell_threshold ({sell_threshold}) phải <= "
            f"buy_threshold ({buy_threshold})"
        )

    if expected_return >= buy_threshold:
        return "BUY"
    if expected_return <= sell_threshold:
        return "SELL"
    return "HOLD"


def classify_returns(
    returns: list[float],
    buy_threshold: float = 0.002,
    sell_threshold: float = -0.002,
) -> list[str]:
    """Áp dụng `compute_signal` cho từng phần tử trong list."""
    return [
        compute_signal(r, buy_threshold=buy_threshold, sell_threshold=sell_threshold)
        for r in returns
    ]
