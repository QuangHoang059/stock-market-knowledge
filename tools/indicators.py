"""
Các chỉ báo kỹ thuật tính bằng pandas/numpy thuần (không cần TA-Lib).

Tham chiếu ngưỡng theo tài liệu bài 01: RSI quá mua > 70 / quá bán < 30;
MA20 (ngắn) / MA50 (trung) / MA200 (dài); MACD (12,26,9); Bollinger (20,2).
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def sma(series: pd.Series, n: int) -> pd.Series:
    return series.rolling(n, min_periods=n).mean()


def ema(series: pd.Series, n: int) -> pd.Series:
    return series.ewm(span=n, adjust=False, min_periods=n).mean()


def rsi(series: pd.Series, n: int = 14) -> pd.Series:
    """RSI theo cách làm trơn của Wilder."""
    delta = series.diff()
    gain = delta.clip(lower=0.0)
    loss = -delta.clip(upper=0.0)
    avg_gain = gain.ewm(alpha=1 / n, adjust=False, min_periods=n).mean()
    avg_loss = loss.ewm(alpha=1 / n, adjust=False, min_periods=n).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    return (100 - 100 / (1 + rs)).fillna(100.0)  # avg_loss=0 → RSI=100


def macd(series: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9):
    """Trả (macd_line, signal_line, histogram)."""
    macd_line = ema(series, fast) - ema(series, slow)
    signal_line = macd_line.ewm(span=signal, adjust=False, min_periods=signal).mean()
    hist = macd_line - signal_line
    return macd_line, signal_line, hist


def bollinger(series: pd.Series, n: int = 20, k: float = 2.0):
    """Trả (mid, upper, lower, width, pct_b)."""
    mid = sma(series, n)
    std = series.rolling(n, min_periods=n).std(ddof=0)
    upper = mid + k * std
    lower = mid - k * std
    width = (upper - lower) / mid.replace(0, np.nan)
    pct_b = (series - lower) / (upper - lower).replace(0, np.nan)
    return mid, upper, lower, width, pct_b


def true_range(df: pd.DataFrame) -> pd.Series:
    high, low, prev_close = df["high"], df["low"], df["close"].shift(1)
    tr = pd.concat([(high - low).abs(),
                    (high - prev_close).abs(),
                    (low - prev_close).abs()], axis=1).max(axis=1)
    return tr


def atr(df: pd.DataFrame, n: int = 14) -> pd.Series:
    """ATR theo Wilder."""
    tr = true_range(df)
    return tr.ewm(alpha=1 / n, adjust=False, min_periods=n).mean()


def obv(df: pd.DataFrame) -> pd.Series:
    direction = np.sign(df["close"].diff().fillna(0))
    return (direction * df["volume"]).cumsum()


def vwap(df: pd.DataFrame, n: int = 20) -> pd.Series:
    """VWAP lăn (rolling) — xấp xỉ khi không có dữ liệu intraday."""
    typical = (df["high"] + df["low"] + df["close"]) / 3
    vol = df["volume"].replace(0, np.nan)
    return (typical * vol).rolling(n, min_periods=n).sum() / vol.rolling(n, min_periods=n).sum()


def volume_sma(vol: pd.Series, n: int = 20) -> pd.Series:
    return vol.rolling(n, min_periods=n).mean()


def relative_strength(price: pd.Series, benchmark: pd.Series) -> pd.Series:
    """Tỷ lệ giá/chiỉ số (rebased) — >1 nghĩa là cổ phiếu mạnh hơn thị trường."""
    p = price / price.iloc[0] if not price.empty else price
    b = benchmark / benchmark.iloc[0] if not benchmark.empty else benchmark
    return p / b.replace(0, np.nan)


def rs_rank(price: pd.Series, benchmark: pd.Series) -> float | None:
    """Điểm sức mạnh giá 0–100 theo biến động % của cổ phiếu so với chỉ số
    trong 1 năm (CANSLIM 'L'). >70 là dẫn đầu, 80–90 lý tưởng."""
    n = min(len(price), len(benchmark), 252)
    if n < 30:
        return None
    p_chg = price.iloc[-1] / price.iloc[-n] - 1
    b_chg = benchmark.iloc[-1] / benchmark.iloc[-n] - 1
    # Chuyển hiệu tương đối thành thang 0–100 quanh điểm hoà nhập của chỉ số.
    rel = p_chg - b_chg
    # Chuẩn hoả: cổ phiếu = chỉ số → ~50; vượt chỉ số 30% → ~90; kém 30% → ~10.
    score = 50 + rel * 100
    return float(max(0.0, min(100.0, score)))
