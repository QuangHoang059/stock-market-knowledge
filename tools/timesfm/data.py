"""Pure-pandas data loader cho Yahoo Finance OHLCV.

Tách khỏi `model.py` để unit-test không cần torch/timesfm3.
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def download_ohlcv(
    symbol: str,
    interval: str = "15m",
    period: str = "60d",
) -> pd.DataFrame:
    """Tải OHLCV từ Yahoo Finance, làm phẳng MultiIndex, drop NaN, sort index.

    Raises:
        RuntimeError: nếu tải thất bại hoặc thiếu cột bắt buộc (Open/High/Low/Close).
    """
    import yfinance as yf

    df = yf.download(
        symbol,
        period=period,
        interval=interval,
        auto_adjust=False,
        progress=False,
        threads=False,
    )

    if df.empty:
        raise RuntimeError(
            f"Không tải được dữ liệu {symbol} từ Yahoo Finance. "
            f"Kiểm tra symbol / interval / period."
        )

    # yfinance trả về MultiIndex columns cho 1 số phiên bản
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

    required = ["Open", "High", "Low", "Close"]
    for col in required:
        if col not in df.columns:
            raise RuntimeError(f"Thiếu cột bắt buộc: {col}")

    keep = required + (["Volume"] if "Volume" in df.columns else [])
    df = df[keep].dropna()
    df = df[~df.index.duplicated(keep="last")]
    df = df.sort_index()

    return df


def extract_close_array(
    df: pd.DataFrame,
    column: str = "Close",
) -> np.ndarray:
    """Trả về close price dạng float32 1-D numpy array."""
    close = df[column].astype(float).to_numpy()
    return close.astype(np.float32)


def take_last_n(arr: np.ndarray, n: int) -> np.ndarray:
    """Lấy N phần tử cuối. Raise nếu thiếu."""
    if len(arr) < n:
        raise RuntimeError(
            f"Không đủ dữ liệu: cần {n}, nhưng chỉ có {len(arr)}"
        )
    return arr[-n:]
