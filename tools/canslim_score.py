"""
Bảng điểm tăng trưởng CANSLIM (William O'Neil) — bài 03.

C – Current quarterly EPS (YoY ≥ 25%): vnstock chỉ cho 4 quý gần nhất nên ưu tiên
    tăng trưởng EPS quý YoY; nếu không có → dùng tăng trưởng EPS năm gần nhất.
A – Annual EPS (≥ 25%/năm trong 3 năm).
N – New high: giá gần đỉnh 52 tuần (điểm mua lý tưởng khi bứt phá cúp-tay-cầm).
S – Supply/Demand: khối lượng ngày tăng > ngày giảm.
L – Leader/Laggard: RS rank ≥ 70 (lý tưởng 80–90).
I – Institutional: dữ liệu tổ chức thường thiếu ở VN → cờ NA + yêu cầu kiểm tra thủ công.
M – Market direction: chỉ số uptrend (giá > MA50 > MA200).

Trọng số nhấn mạnh C, A, L, M (O'Neil coi đây là các yếu tố quyết định).
"""

from __future__ import annotations

import pandas as pd

from .value_score import Check, Scorecard, PASS, WARN, FAIL, NA, _finalize


def score_canslim(f: dict, hist: pd.DataFrame, rs_rank: float | None,
                  index_trend: dict) -> Scorecard:
    """Bảng điểm CANSLIM.

    Tham số:
      f            — dict fundamentals (data.get_fundamentals); {} nếu không phải VN.
      hist         — DataFrame OHLCV (data.get_history) cho N, S.
      rs_rank      — điểm sức mạnh giá 0–100 (indicators.rs_rank) cho L.
      index_trend  — dict từ data.get_index_trend cho M.
    """
    f = f or {}
    checks: list[Check] = []

    def num(v):
        return v if isinstance(v, (int, float)) else None

    # ---------------- C — EPS quý YoY ≥ 25% (fallback EPS năm gần nhất) ----
    q_yoy = num(f.get("eps_q_yoy_growth"))
    ann_g = num(f.get("eps_growth_3y"))
    if q_yoy is not None:
        if q_yoy >= 0.25:
            checks.append(Check("C", "EPS quý YoY", PASS, f"+{q_yoy*100:.1f}%", "≥ 25%", 2.0))
        elif q_yoy >= 0.15:
            checks.append(Check("C", "EPS quý YoY", WARN, f"+{q_yoy*100:.1f}%", "≥ 25%", 2.0))
        else:
            checks.append(Check("C", "EPS quý YoY", FAIL, f"+{q_yoy*100:.1f}%", "≥ 25%", 2.0))
    elif ann_g is not None:
        # Không có quý YoY → dùng tăng trưởng năm gần nhất làm xấp xỉ.
        st = PASS if ann_g >= 0.25 else (WARN if ann_g >= 0.15 else FAIL)
        checks.append(Check("C", "EPS (dùng tăng trưởng năm)", st,
                            f"+{ann_g*100:.1f}%/năm (vnstock chỉ có 4 quý)", "≥ 25% YoY", 2.0))
    else:
        checks.append(Check("C", "EPS quý/năm", NA, "Thiếu dữ liệu EPS", "≥ 25%", 2.0))

    # ---------------- A — EPS năm ≥ 25%/năm trong 3 năm ----------------------
    if ann_g is not None:
        if ann_g >= 0.25:
            checks.append(Check("A", "EPS năm (3 năm)", PASS, f"+{ann_g*100:.1f}%/năm", "≥ 25%/năm", 2.0))
        elif ann_g >= 0.15:
            checks.append(Check("A", "EPS năm (3 năm)", WARN, f"+{ann_g*100:.1f}%/năm", "≥ 25%/năm", 2.0))
        else:
            checks.append(Check("A", "EPS năm (3 năm)", FAIL, f"+{ann_g*100:.1f}%/năm", "≥ 25%/năm", 2.0))
    else:
        checks.append(Check("A", "EPS năm", NA, "Thiếu dữ liệu", "≥ 25%/năm", 2.0))

    # ---------------- N — Gần đỉnh 52 tuần (cơ sở cho điểm mua) --------------
    high52 = num(f.get("high52"))
    price = num(f.get("price"))
    if high52 and price:
        pct_off = (high52 - price) / high52
        if pct_off <= 0.05:        # trong 5% đỉnh → gần điểm mua bứt phá
            checks.append(Check("N", "Gần đỉnh 52 tuần", PASS,
                                f"-{pct_off*100:.1f}% so đỉnh", "≤ ~5%", 1.5))
        elif pct_off <= 0.15:
            checks.append(Check("N", "Gần đỉnh 52 tuần", WARN,
                                f"-{pct_off*100:.1f}%", "≤ ~5%", 1.5))
        else:
            checks.append(Check("N", "Gần đỉnh 52 tuần", FAIL,
                                f"-{pct_off*100:.1f}% (xa đỉnh)", "≤ ~5%", 1.5))
    else:
        checks.append(Check("N", "Gần đỉnh 52 tuần", NA, "Thiếu giá/đỉnh 52 tuần", "≤ ~5%", 1.5))

    # ---------------- S — Supply/Demand: volume ngày tăng > ngày giảm --------
    if hist is not None and not hist.empty and len(hist) >= 30:
        up = hist["volume"].where(hist["close"] > hist["close"].shift(1), 0).tail(20)
        down = hist["volume"].where(hist["close"] < hist["close"].shift(1), 0).tail(20)
        ratio = (up.sum() / down.sum()) if down.sum() else None
        if ratio is None:
            checks.append(Check("S", "Volume tăng vs giảm", NA, "Không có ngày giảm", "Tăng > Giảm", 1.0))
        elif ratio >= 1.2:
            checks.append(Check("S", "Volume tăng vs giảm", PASS, f"{ratio:.2f}× (tích lũy)", "Tăng > Giảm", 1.0))
        elif ratio >= 1.0:
            checks.append(Check("S", "Volume tăng vs giảm", WARN, f"{ratio:.2f}×", "Tăng > Giảm", 1.0))
        else:
            checks.append(Check("S", "Volume tăng vs giảm", FAIL, f"{ratio:.2f}× (phân phối)", "Tăng > Giảm", 1.0))
    else:
        checks.append(Check("S", "Volume tăng vs giảm", NA, "Thiếu dữ liệu OHLCV", "Tăng > Giảm", 1.0))

    # ---------------- L — RS rank ≥ 70 (lý tưởng 80–90) ---------------------
    if rs_rank is None:
        checks.append(Check("L", "RS rank", NA, "Thiếu dữ liệu so sánh", "≥ 70 (80–90 lý tưởng)", 2.0))
    elif rs_rank >= 80:
        checks.append(Check("L", "RS rank", PASS, f"{rs_rank:.0f} (dẫn đầu)", "≥ 70 (80–90 lý tưởng)", 2.0))
    elif rs_rank >= 70:
        checks.append(Check("L", "RS rank", PASS, f"{rs_rank:.0f}", "≥ 70 (80–90 lý tưởng)", 2.0))
    elif rs_rank >= 50:
        checks.append(Check("L", "RS rank", WARN, f"{rs_rank:.0f}", "≥ 70 (80–90 lý tưởng)", 2.0))
    else:
        checks.append(Check("L", "RS rank", FAIL, f"{rs_rank:.0f} (tụt hậu)", "≥ 70 (80–90 lý tưởng)", 2.0))

    # ---------------- I — Institutional (thường thiếu ở VN) -----------------
    checks.append(Check("I", "Tổ chức mua vào", NA,
                        "Dữ liệu tổ chức VN hạn chế — kiểm tra CTĐT lớn",
                        "Có CTĐT lớn, lượng nắm giữ tăng", 0.5))

    # ---------------- M — Hướng thị trường (chỉ số uptrend) -----------------
    if not index_trend.get("available"):
        checks.append(Check("M", "Hướng thị trường", NA, "Không lấy được chỉ số", "Giá > MA50 > MA200", 2.0))
    elif index_trend.get("uptrend"):
        checks.append(Check("M", "Hướng thị trường", PASS,
                            f"{index_trend.get('index','?')} uptrend (giá>MA50>MA200)",
                            "Giá > MA50 > MA200", 2.0))
    else:
        checks.append(Check("M", "Hướng thị trường", FAIL,
                            f"{index_trend.get('index','?')} chưa uptrend", "Giá > MA50 > MA200", 2.0))

    notes = []
    if index_trend.get("available"):
        notes.append(f"Chỉ số {index_trend.get('index')}: giá {index_trend.get('price'):,.0f}"
                     f", {'uptrend' if index_trend.get('uptrend') else 'không uptrend'}"
                     f", {index_trend.get('pct_off_high52')*100:+.1f}% so đỉnh 52 tuần.")
    return _finalize("growth", checks, notes)
