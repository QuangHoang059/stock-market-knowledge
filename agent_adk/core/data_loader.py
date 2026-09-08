"""Data loader — fetch OHLCV từ Yahoo Finance, cache thành CSV.

Hỗ trợ:
    download(symbol, tf, period)  → tải toàn bộ, ghi đè CSV
    refresh(symbol, tf, days)     → append bars mới, dedupe theo timestamp
    load(symbol, tf)              → đọc CSV thành DataFrame

Timeframe 4h: yfinance không có native 4h; resample từ 1h.
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from ..config import (
    DATA_DIR,
    REFRESH_DAYS,
    TIMEFRAME_TO_YF_INTERVAL,
    TIMEFRAME_TO_YF_PERIOD,
    csv_path,
    get_symbol_meta,
)

DATA_DIR.mkdir(parents=True, exist_ok=True)


@dataclass
class LoadResult:
    symbol: str
    timeframe: str
    rows: int
    first_date: pd.Timestamp
    last_date: pd.Timestamp
    source: str  # "csv" hoặc "downloaded"


def _normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Chuẩn hoá columns thành: timestamp, open, high, low, close, volume (lowercase).

    Hỗ trợ cả DataFrame có index là DateTimeIndex và DataFrame có cột 'Date'.
    """
    # Nếu có DateTimeIndex → lấy làm timestamp
    if isinstance(df.index, pd.DatetimeIndex):
        ts = df.index.copy()
        df = df.reset_index(drop=True)
    else:
        cols = {c.lower(): c for c in df.columns}
        ts = pd.to_datetime(df[cols.get("date", cols.get("timestamp", "Date"))], utc=True, errors="coerce")

    cols = {c.lower(): c for c in df.columns}

    def _series(name_lower: str) -> pd.Series:
        src = cols.get(name_lower)
        if src is None:
            return pd.Series([None] * len(df))
        return pd.to_numeric(df[src], errors="coerce")

    out = pd.DataFrame({
        "timestamp": pd.to_datetime(ts, utc=True, errors="coerce"),
        "open": _series("open"),
        "high": _series("high"),
        "low": _series("low"),
        "close": _series("close"),
    })
    out["volume"] = _series("volume").fillna(0.0)
    out = out.dropna(subset=["timestamp", "close"]).sort_values("timestamp").reset_index(drop=True)
    return out


def _fetch_yahoo(symbol: str, timeframe: str, period: str | None = None) -> pd.DataFrame:
    """Tải OHLCV từ Yahoo Finance qua HTTP trực tiếp (yfinance lib đang hỏng).

    Resample 1h → 4h nếu cần.
    """
    import json
    import time
    import urllib.parse
    import urllib.request

    meta = get_symbol_meta(symbol)
    yf_ticker = meta["yahoo"]
    interval = TIMEFRAME_TO_YF_INTERVAL[timeframe]
    period = period or TIMEFRAME_TO_YF_PERIOD[timeframe]

    # Map period sang range (Yahoo chart API)
    range_map = {
        "1d": "1d", "5d": "5d", "1mo": "1mo", "3mo": "3mo", "6mo": "6mo",
        "1y": "1y", "2y": "2y", "5y": "5y", "10y": "10y", "ytd": "ytd", "max": "max",
    }
    rng = range_map.get(period, period)
    if rng not in range_map:
        rng = "1y"

    interval_map = {"1m": "1m", "5m": "5m", "15m": "15m", "30m": "30m",
                    "1h": "60m", "1d": "1d", "1wk": "1wk", "1mo": "1mo"}
    iv = interval_map.get(interval, interval)

    url = (
        f"https://query1.finance.yahoo.com/v8/finance/chart/{urllib.parse.quote(yf_ticker)}"
        f"?interval={iv}&range={rng}&events=history"
    )
    req = urllib.request.Request(url, headers={
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "application/json",
    })

    last_err = None
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                payload = json.loads(resp.read())
            break
        except Exception as e:
            last_err = e
            time.sleep(1 + attempt)
    else:
        raise RuntimeError(f"Yahoo API thất bại cho {yf_ticker}: {last_err}")

    chart = payload.get("chart", {})
    result_list = chart.get("result") or []
    if chart.get("error") or not result_list:
        err = chart.get("error") or {}
        raise RuntimeError(f"Yahoo không có data cho {yf_ticker}: {err.get('description', 'unknown')}")

    result = result_list[0]
    ts = result.get("timestamp") or []
    ind = result.get("indicators", {}).get("quote", [{}])[0]
    if not ts or not ind.get("close"):
        raise RuntimeError(f"Yahoo trả rỗng cho {yf_ticker} ({iv}, {rng})")

    df = pd.DataFrame({
        "Open": ind.get("open", [None] * len(ts)),
        "High": ind.get("high", [None] * len(ts)),
        "Low": ind.get("low", [None] * len(ts)),
        "Close": ind.get("close", [None] * len(ts)),
        "Volume": ind.get("volume", [0] * len(ts)),
    }, index=pd.to_datetime(ts, unit="s", utc=True))
    df = df.dropna(subset=["Close"])

    if timeframe == "4h":
        df = df.resample("4h", label="right", closed="right").agg({
            "Open": "first", "High": "max", "Low": "min", "Close": "last", "Volume": "sum",
        }).dropna()
    return df


def download(symbol: str, timeframe: str, period: str | None = None,
             overwrite: bool = True) -> LoadResult:
    """Tải dataset cho symbol/tf, ghi CSV."""
    df = _fetch_yahoo(symbol, timeframe, period=period)
    norm = _normalize_columns(df)
    path = csv_path(symbol, timeframe)
    if overwrite or not path.exists():
        norm.to_csv(path, index=False)
    return LoadResult(
        symbol=symbol,
        timeframe=timeframe,
        rows=len(norm),
        first_date=norm["timestamp"].iloc[0],
        last_date=norm["timestamp"].iloc[-1],
        source="downloaded",
    )


def refresh(symbol: str, timeframe: str, days: int = REFRESH_DAYS) -> LoadResult:
    """Append bars mới (≤ `days` gần nhất), dedupe theo timestamp.

    Nếu CSV chưa tồn tại → fallback download() full.
    """
    path = csv_path(symbol, timeframe)
    existing = pd.DataFrame()
    if path.exists():
        try:
            existing = pd.read_csv(path)
            existing["timestamp"] = pd.to_datetime(existing["timestamp"], utc=True, errors="coerce")
            existing = existing.dropna(subset=["timestamp"]).sort_values("timestamp")
        except Exception:
            existing = pd.DataFrame()

    if existing.empty:
        return download(symbol, timeframe)

    last_ts = existing["timestamp"].max()
    if pd.isna(last_ts):
        return download(symbol, timeframe)
    last_ts = pd.Timestamp(last_ts).tz_convert("UTC") if last_ts.tzinfo else pd.Timestamp(last_ts).tz_localize("UTC")
    now_utc = pd.Timestamp.now(tz="UTC")
    # Nếu CSV đã là hôm nay (utc) thì thôi
    if (now_utc - last_ts).total_seconds() < 60 * 60:  # <1h
        return LoadResult(
            symbol=symbol, timeframe=timeframe, rows=len(existing),
            first_date=existing["timestamp"].iloc[0], last_date=existing["timestamp"].iloc[-1],
            source="csv",
        )

    # Lấy dữ liệu từ last_ts - days cho đến hiện tại
    fetch_start = (last_ts - pd.Timedelta(days=days)).date().isoformat()
    fetch_end = (now_utc + pd.Timedelta(days=1)).date().isoformat()

    import json
    import time
    import urllib.parse
    import urllib.request

    meta = get_symbol_meta(symbol)
    interval = TIMEFRAME_TO_YF_INTERVAL[timeframe]
    interval_map = {"1m": "1m", "5m": "5m", "15m": "15m", "30m": "30m",
                    "1h": "60m", "1d": "1d"}
    iv = interval_map.get(interval, interval)

    # Convert unix timestamps
    start_unix = int(pd.Timestamp(fetch_start).tz_localize("UTC").timestamp())
    end_unix = int(pd.Timestamp(fetch_end).tz_localize("UTC").timestamp())
    url = (
        f"https://query1.finance.yahoo.com/v8/finance/chart/{urllib.parse.quote(meta['yahoo'])}"
        f"?interval={iv}&period1={start_unix}&period2={end_unix}&events=history"
    )
    req = urllib.request.Request(url, headers={
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "application/json",
    })
    last_err = None
    df_new = pd.DataFrame()
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                payload = json.loads(resp.read())
            result = payload["chart"]["result"][0]
            ts = result["timestamp"]
            ind = result["indicators"]["quote"][0]
            df_new = pd.DataFrame({
                "Open": ind.get("open", [None] * len(ts)),
                "High": ind.get("high", [None] * len(ts)),
                "Low": ind.get("low", [None] * len(ts)),
                "Close": ind.get("close", [None] * len(ts)),
                "Volume": ind.get("volume", [0] * len(ts)),
            }, index=pd.to_datetime(ts, unit="s", utc=True))
            df_new = df_new.dropna(subset=["Close"])
            break
        except Exception as e:
            last_err = e
            time.sleep(1 + attempt)

    if df_new.empty:
        return LoadResult(
            symbol=symbol, timeframe=timeframe, rows=len(existing),
            first_date=existing["timestamp"].iloc[0], last_date=existing["timestamp"].iloc[-1],
            source="csv",
        )
    if isinstance(df_new.columns, pd.MultiIndex):
        df_new.columns = df_new.columns.get_level_values(0)
    if timeframe == "4h":
        df_new = df_new.resample("4h", label="right", closed="right").agg({
            "Open": "first", "High": "max", "Low": "min", "Close": "last", "Volume": "sum",
        }).dropna()
    new_norm = _normalize_columns(df_new)

    merged = pd.concat([existing, new_norm], ignore_index=True)
    merged = merged.drop_duplicates(subset=["timestamp"], keep="last").sort_values("timestamp").reset_index(drop=True)

    # Cắt lại còn N ngày gần nhất nếu muốn — giữ toàn bộ lịch sử để backtest
    merged.to_csv(path, index=False)

    return LoadResult(
        symbol=symbol, timeframe=timeframe, rows=len(merged),
        first_date=merged["timestamp"].iloc[0], last_date=merged["timestamp"].iloc[-1],
        source="refreshed",
    )


def load(symbol: str, timeframe: str) -> pd.DataFrame:
    """Đọc CSV đã cache. Nếu chưa có → tự động download."""
    path = csv_path(symbol, timeframe)
    if not path.exists():
        download(symbol, timeframe)
    df = pd.read_csv(path)
    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True, errors="coerce")
    df = df.dropna(subset=["timestamp"]).sort_values("timestamp").reset_index(drop=True)
    return df


def last_n_days(df: pd.DataFrame, days: int) -> pd.DataFrame:
    """Trả về `days` ngày gần nhất của DataFrame (theo timestamp UTC)."""
    if df.empty:
        return df
    last_ts = df["timestamp"].max()
    cutoff = last_ts - pd.Timedelta(days=days)
    return df[df["timestamp"] >= cutoff].reset_index(drop=True)


__all__ = ["download", "refresh", "load", "last_n_days", "LoadResult"]
