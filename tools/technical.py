"""
Phân tích kỹ thuật tổng hợp — bài 01, 04, 05.

Gộp nhiều nhóm tín hiệu vào một lượt:
  - Xu hướng (MA stack, HH/HL)                      — bài 01
  - Hỗ trợ / kháng cự (swing cluster)               — bài 01
  - Nến Nhật (Marubozu, Doji, Hammer, Star, Engulf) — bài 01
  - RSI quá mua/bán + phân kỳ                       — bài 01
  - MACD cắt / phân kỳ                              — bài 01
  - Bollinger squeeze                               — bài 01
  - Wyckoff/VSA (selling climax, spring, effort-vs-result) — bài 04
  - Elliott/Fibonacci (thoái lui 23.6/38.2/50/61.8 + mở rộng 161.8) — bài 05

Mỗi tín hiệu: {category, name, bias (bull/bear/neutral), detail}.
Bias tổng hợp = nặng theo điểm kỹ thuật + xác nhận khối lượng.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from . import indicators as ind


def _swing_pivots(series: pd.Series, k: int = 3):
    """Trả danh sách (idx, price, 'H'|'L') — đỉnh/đáy xoay với cửa sổ k mỗi bên."""
    highs, lows = [], []
    arr = series.to_numpy()
    idx = series.index
    for i in range(k, len(arr) - k):
        window = arr[i - k:i + k + 1]
        if arr[i] == window.max() and np.count_nonzero(window == arr[i]) == 1:
            highs.append((idx[i], float(arr[i]), "H"))
        if arr[i] == window.min() and np.count_nonzero(window == arr[i]) == 1:
            lows.append((idx[i], float(arr[i]), "L"))
    return highs, lows


def _fib_levels(p1: float, p2: float):
    """Tính các mức thoái lui Fibonacci từ p1 -> p2 (khoảng delta = p2-p1)."""
    d = p2 - p1
    return {f: round(p2 - f * d, 2) for f in (0.236, 0.382, 0.5, 0.618, 0.786)}


# --------------------------------------------------------------------------- #
# Nhóm tín hiệu
# --------------------------------------------------------------------------- #
def _trend_signals(df: pd.DataFrame) -> list[dict]:
    sig: list[dict] = []
    c = df["close"]
    if len(c) < 200:
        sig.append({"category": "Xu hướng", "name": "MA",
                    "bias": "neutral",
                    "detail": f"Dữ liệu {len(c)} bar — chưa đủ MA200, dùng MA20/50."})
    m20 = ind.sma(c, 20).iloc[-1]
    m50 = ind.sma(c, 50).iloc[-1]
    m200 = ind.sma(c, 200).iloc[-1] if len(c) >= 200 else None
    price = c.iloc[-1]
    if m200 is not None:
        if price > m20 > m50 > m200:
            sig.append({"category": "Xu hướng", "name": "MA stack",
                        "bias": "bull", "detail": "Giá > MA20 > MA50 > MA200 — uptrend mạnh."})
        elif price < m20 < m50 < m200:
            sig.append({"category": "Xu hướng", "name": "MA stack",
                        "bias": "bear", "detail": "Giá < MA20 < MA50 < MA200 — downtrend."})
        else:
            sig.append({"category": "Xu hướng", "name": "MA stack",
                        "bias": "neutral",
                        "detail": f"MA đan nhau (Giá {price:.2f}, MA20 {m20:.2f}, "
                                  f"MA50 {m50:.2f}, MA200 {m200:.2f}) — đi ngang/xác nhận lại."})
    else:
        bias = "bull" if price > m20 > m50 else ("bear" if price < m20 < m50 else "neutral")
        sig.append({"category": "Xu hướng", "name": "MA20/50",
                    "bias": bias,
                    "detail": f"Giá {price:.2f}, MA20 {m20:.2f}, MA50 {m50:.2f}."})

    # HH/HL vs LH/LL qua 2 đỉnh & 2 đáy gần nhất
    highs, lows = _swing_pivots(c, k=3)
    if len(highs) >= 2 and len(lows) >= 2:
        hh = highs[-1][1] > highs[-2][1]
        hl = lows[-1][1] > lows[-2][1]
        lh = highs[-1][1] < highs[-2][1]
        ll = lows[-1][1] < lows[-2][1]
        if hh and hl:
            sig.append({"category": "Xu hướng", "name": "Cấu trúc HH/HL",
                        "bias": "bull", "detail": "Đỉnh cao hơn + đáy cao hơn."})
        elif lh and ll:
            sig.append({"category": "Xu hướng", "name": "Cấu trúc LH/LL",
                        "bias": "bear", "detail": "Đỉnh thấp hơn + đáy thấp hơn."})
    return sig


def _sr_levels(df: pd.DataFrame) -> dict:
    """Hỗ trợ/kháng cự gộp từ swing cluster + MA + Fib gần nhất."""
    c = df["close"]
    levels: list[tuple[float, str]] = []  # (price, nguồn)
    highs, lows = _swing_pivots(c, k=3)
    if highs:
        levels.append((highs[-1][1], "kháng cự (đỉnh xoay)"))
    if lows:
        levels.append((lows[-1][1], "hỗ trợ (đáy xoay)"))
    if len(c) >= 50:
        levels.append((ind.sma(c, 50).iloc[-1], "MA50"))
    return {"levels": [(round(p, 2), src) for p, src in levels],
            "resistance": round(highs[-1][1], 2) if highs else None,
            "support": round(lows[-1][1], 2) if lows else None,
            "fib": _nearest_fib(df)}


def _nearest_fib(df: pd.DataFrame) -> dict | None:
    """Chiếu Fibonacci thoái lui + mở rộng 161.8% lên nhịp gần nhất hoàn thành."""
    c = df["close"]
    highs, lows = _swing_pivots(c, k=4)
    if not highs or not lows:
        return None
    # Nhịp gần nhất: lấy đỉnh & đáy gần nhau nhất (1 đỉnh, 1 đáy kế tiếp).
    pts = sorted(highs + lows, key=lambda x: x[0])
    if len(pts) < 2:
        return None
    p1_pt, p2_pt = pts[-2], pts[-1]
    p1, p2 = p1_pt[1], p2_pt[1]
    retr = _fib_levels(p1, p2)
    impulse = abs(p2 - p1)
    direction = "up" if p2 > p1 else "down"
    ext = round(p2 + 1.618 * impulse, 2) if direction == "up" else round(p2 - 1.618 * impulse, 2)
    return {"from": round(p1, 2), "to": round(p2, 2), "direction": direction,
            "retracement": retr, "ext_1618": ext}


def _candle_signals(df: pd.DataFrame) -> list[dict]:
    sig: list[dict] = []
    if len(df) < 3:
        return sig
    o, h, l, c = df["open"], df["high"], df["low"], df["close"]
    i = len(df) - 1
    body = abs(c.iloc[i] - o.iloc[i])
    rng = (h.iloc[i] - l.iloc[i]) or 1e-9
    upper = h.iloc[i] - max(o.iloc[i], c.iloc[i])
    lower = min(o.iloc[i], c.iloc[i]) - l.iloc[i]
    bull = c.iloc[i] > o.iloc[i]

    # Marubozu
    if body / rng >= 0.9:
        sig.append({"category": "Nến", "name": "Marubozu",
                    "bias": "bull" if bull else "bear",
                    "detail": f"Thân nến {body/rng*100:.0f}% khoảng — áp lực mạnh một chiều."})
    # Doji
    if body / rng <= 0.1:
        sig.append({"category": "Nến", "name": "Doji",
                    "bias": "neutral", "detail": "Thân nến rất nhỏ — do dự, có thể đảo chiều."})
    # Hammer / Shooting Star
    if lower >= 2 * body and upper <= 0.3 * body:
        sig.append({"category": "Nến", "name": "Hammer",
                    "bias": "bull", "detail": "Bóng dưới dài — từ chối giá thấp (sau downtrend thì mạnh)."})
    if upper >= 2 * body and lower <= 0.3 * body:
        sig.append({"category": "Nến", "name": "Shooting Star",
                    "bias": "bear", "detail": "Bóng trên dài — từ chối giá cao (sau uptrend thì mạnh)."})
    # Engulfing
    prev_body = abs(c.iloc[i - 1] - o.iloc[i - 1])
    if bull and c.iloc[i] > o.iloc[i - 1] and o.iloc[i] < c.iloc[i - 1] and body > prev_body:
        sig.append({"category": "Nến", "name": "Bullish Engulfing",
                    "bias": "bull", "detail": "Nến tăng bao trùm nến giảm trước."})
    if (not bull) and o.iloc[i] > c.iloc[i - 1] and c.iloc[i] < o.iloc[i - 1] and body > prev_body:
        sig.append({"category": "Nến", "name": "Bearish Engulfing",
                    "bias": "bear", "detail": "Nến giảm bao trùm nến tăng trước."})
    return sig


def _rsi_signals(df: pd.DataFrame) -> list[dict]:
    sig: list[dict] = []
    r = ind.rsi(df["close"], 14)
    last = r.iloc[-1]
    if np.isnan(last):
        return sig
    if last > 70:
        sig.append({"category": "RSI", "name": "Quá mua",
                    "bias": "bear", "detail": f"RSI {last:.1f} > 70 — cẩn thận điều chỉnh."})
    elif last < 30:
        sig.append({"category": "RSI", "name": "Quá bán",
                    "bias": "bull", "detail": f"RSI {last:.1f} < 30 — khu vực phục hồi."})
    else:
        sig.append({"category": "RSI", "name": "Trung tính",
                    "bias": "neutral", "detail": f"RSI {last:.1f}."})
    # Phân kỳ RBear/Bull (50 bar)
    seg = df["close"].tail(50)
    rseg = r.tail(50).dropna()
    if len(rseg) >= 20:
        price_trend = seg.iloc[-1] - seg.iloc[len(seg) // 2]
        rsi_trend = rseg.iloc[-1] - rseg.iloc[len(rseg) // 2]
        if price_trend > 0 and rsi_trend < 0:
            sig.append({"category": "RSI", "name": "Phân kỳ giảm",
                        "bias": "bear", "detail": "Giá lên mà RSI xuống — động lượng yếu."})
        elif price_trend < 0 and rsi_trend > 0:
            sig.append({"category": "RSI", "name": "Phân kỳ tăng",
                        "bias": "bull", "detail": "Giá xuống mà RSI lên — động lượng tích lũy."})
    return sig


def _macd_signals(df: pd.DataFrame) -> list[dict]:
    sig: list[dict] = []
    _, _, hist = ind.macd(df["close"])
    if hist.dropna().empty:
        return sig
    h = hist.dropna()
    if len(h) >= 2 and h.iloc[-1] > 0 >= h.iloc[-2]:
        sig.append({"category": "MACD", "name": "Cắt lên",
                    "bias": "bull", "detail": "Histogram MACD cắt lên 0 — tín hiệu mua."})
    elif len(h) >= 2 and h.iloc[-1] < 0 <= h.iloc[-2]:
        sig.append({"category": "MACD", "name": "Cắt xuống",
                    "bias": "bear", "detail": "Histogram MACD cắt xuống 0 — tín hiệu bán."})
    else:
        sig.append({"category": "MACD", "name": "Histogram",
                    "bias": "bull" if h.iloc[-1] > 0 else "bear",
                    "detail": f"Histogram {'dương' if h.iloc[-1] > 0 else 'âm'} ({h.iloc[-1]:.4f})."})
    return sig


def _bollinger_signals(df: pd.DataFrame) -> list[dict]:
    sig: list[dict] = []
    _, _, _, width, pct_b = ind.bollinger(df["close"])
    w = width.dropna()
    if w.empty:
        return sig
    sig.append({"category": "Bollinger", "name": "%B",
                "bias": "bull" if pct_b.iloc[-1] > 0.8 else ("bear" if pct_b.iloc[-1] < 0.2 else "neutral"),
                "detail": f"%B {pct_b.iloc[-1]:.2f} ({'chạm dải trên' if pct_b.iloc[-1] > 0.8 else 'chạm dải dưới' if pct_b.iloc[-1] < 0.2 else 'giữa'})."})
    # Squeeze: width ở phân vị thấp so 120 bar
    lookback = min(len(w), 120)
    if w.tail(lookback).iloc[-1] <= w.tail(lookback).quantile(0.2):
        sig.append({"category": "Bollinger", "name": "Squeeze",
                    "bias": "neutral",
                    "detail": "Dải Bollinger thu hẹp (volatility thấp) — chờ bứt phá."})
    return sig


def _wyckoff_vsa_signals(df: pd.DataFrame) -> list[dict]:
    sig: list[dict] = []
    if len(df) < 20:
        return sig
    vol_sma = ind.volume_sma(df["volume"], 20)
    o, h, l, c, v = df["open"], df["high"], df["low"], df["close"], df["volume"]
    i = len(df) - 1
    body = c.iloc[i] - o.iloc[i]
    rng = (h.iloc[i] - l.iloc[i]) or 1e-9
    avg_v = vol_sma.iloc[-1]
    high_vol = v.iloc[i] > 1.8 * avg_v if avg_v else False

    # Selling climax: thanh giảm lớn + volume lớn + đóng gần giữa/dưới-dai (off the low)
    if body < 0 and abs(body) / rng > 0.6 and high_vol and (c.iloc[i] - l.iloc[i]) > abs(body) * 0.5:
        sig.append({"category": "Wyckoff/VSA", "name": "Selling climax",
                    "bias": "bull",
                    "detail": "Thanh giảm mạnh + volume lớn + đóng bật lên — hút mua (dấu tích lũy)."})

    # Effort vs Result: volume lớn nhưng thân nến nhỏ (nỗ lực lớn, kết quả nhỏ)
    if high_vol and abs(body) / rng < 0.3:
        sig.append({"category": "Wyckoff/VSA", "name": "Effort > Result",
                    "bias": "bull" if body >= 0 else "bear",
                    "detail": "Volume lớn mà nến nhỏ — lực mua/bán bị hấp thụ, dễ đảo."})

    # No demand: thanh tăng nhỏ, volume thấp hơn trung bình rõ rệt
    if body > 0 and abs(body) / rng < 0.4 and v.iloc[i] < 0.6 * avg_v:
        sig.append({"category": "Wyckoff/VSA", "name": "No Demand",
                    "bias": "bear",
                    "detail": "Thanh tăng nhưng volume cạn — thiếu lực mua."})

    # Spring (false breakdown): giá xuyên qua đáy gần nhất rồi đóng lại phía trên
    lows, _ = _swing_pivots(df["low"], k=3)
    if lows:
        last_low = lows[-1][1]
        if l.iloc[i] < last_low and c.iloc[i] > last_low:
            sig.append({"category": "Wyckoff/VSA", "name": "Spring",
                        "bias": "bull",
                        "detail": f"Giá xuyên đáy {last_low:.2f} rồi đóng lại trên — phá vỡ giả (Spring)."})
    return sig


# --------------------------------------------------------------------------- #
# API chính
# --------------------------------------------------------------------------- #
def analyze(hist: pd.DataFrame) -> dict:
    """Trả dict: bias, signals[], levels{}, indicators{}, summary.

    (RS rank so chỉ số được tính riêng trong evaluate.py qua indicators.rs_rank,
    không lặp lại ở đây để tránh gọi dữ liệu chỉ số hai lần.)
    """
    out: dict = {"bias": "neutral", "signals": [], "levels": {},
                 "indicators": {}, "summary": ""}
    if hist is None or hist.empty:
        out["summary"] = "Không có dữ liệu OHLCV."
        return out
    df = hist.copy()

    groups = [
        _trend_signals(df), _candle_signals(df), _rsi_signals(df),
        _macd_signals(df), _bollinger_signals(df), _wyckoff_vsa_signals(df),
    ]
    signals = [s for g in groups for s in g]
    out["signals"] = signals
    out["levels"] = _sr_levels(df)

    # Tóm tắt chỉ báo chính
    c = df["close"]
    r = ind.rsi(c, 14).iloc[-1]
    macd_l, sig_l, _ = ind.macd(c)
    out["indicators"] = {
        "price": round(float(c.iloc[-1]), 2),
        "ma20": round(float(ind.sma(c, 20).iloc[-1]), 2),
        "ma50": round(float(ind.sma(c, 50).iloc[-1]), 2),
        "ma200": round(float(ind.sma(c, 200).iloc[-1]), 2) if len(c) >= 200 else None,
        "rsi14": round(float(r), 1) if not np.isnan(r) else None,
        "macd_hist": round(float((macd_l - sig_l).iloc[-1]), 1),
        "atr_pct": _atr_pct(df),
    }

    # Bias tổng hợp theo điểm kỹ thuật
    score = {"bull": 0, "bear": 0}
    for s in signals:
        score[s["bias"]] = score.get(s["bias"], 0) + 1
    net = score["bull"] - score["bear"]
    out["bias"] = "bull" if net >= 2 else ("bear" if net <= -2 else "neutral")
    out["summary"] = (f"{len(signals)} tín hiệu | tăng {score['bull']} / giảm {score['bear']} "
                      f"/ trung tính {score.get('neutral', 0)} → bias: {out['bias'].upper()}.")
    return out


def _atr_pct(df: pd.DataFrame) -> float | None:
    a = ind.atr(df, 14)
    if a.empty or not df["close"].iloc[-1]:
        return None
    return round(float(a.iloc[-1] / df["close"].iloc[-1] * 100), 2)
