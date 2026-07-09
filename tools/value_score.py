"""
Bảng điểm Đầu tư Giá trị (Warren Buffett) — bài 02.

Mỗi tiêu chí: PASS (đạt) / WARN (biên giới) / FAIL (trượt) / NA (thiếu dữ liệu),
kèm trọng số. Tổng điểm chuẩn hoá 0–100 theo các mục có dữ liệu.
"""

from __future__ import annotations

from dataclasses import dataclass, field

PASS, WARN, FAIL, NA = "PASS", "WARN", "FAIL", "NA"
_STATUS_SCORE = {PASS: 1.0, WARN: 0.5, FAIL: 0.0, NA: 0.0}


@dataclass
class Check:
    key: str
    label: str
    status: str
    detail: str
    threshold: str
    weight: float = 1.0


@dataclass
class Scorecard:
    style: str
    score: float          # 0–100
    grade: str            # MẠNH / KHẢ QUAN / TRÁNH / THIẾU DỮ LIỆU
    checks: list[Check] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "style": self.style, "score": round(self.score, 1), "grade": self.grade,
            "checks": [c.__dict__ for c in self.checks], "notes": self.notes,
        }


def _finalize(style: str, checks: list[Check], notes: list[str] | None = None) -> Scorecard:
    """Tính điểm chuẩn hoá theo trọng số các mục có dữ liệu (bỏ NA)."""
    notes = notes or []
    used = [c for c in checks if c.status != NA]
    if not used:
        return Scorecard(style, 0.0, "THIẾU DỮ LIỆU", checks, notes or ["Không có dữ liệu cơ bản."])
    total_w = sum(c.weight for c in used)
    got = sum(_STATUS_SCORE[c.status] * c.weight for c in used)
    score = got / total_w * 100 if total_w else 0.0
    grade = "MẠNH" if score >= 70 else ("KHẢ QUAN" if score >= 50 else "TRÁNH")
    return Scorecard(style, score, grade, checks, notes)


def score_value(f: dict) -> Scorecard:
    """Bảng điểm giá trị Buffett từ dict fundamentals (data.get_fundamentals)."""
    f = f or {}
    checks: list[Check] = []

    def num(v):
        return v if isinstance(v, (int, float)) else None

    # 1. ROE — ≥15% và ổn định (trọng số cao)
    roe = num(f.get("roe"))
    roe_stable = f.get("roe_stable")
    if roe is None:
        checks.append(Check("roe", "ROE", NA, "Không có dữ liệu", "≥ 15% & ổn định"))
    elif roe >= 0.15 and roe_stable:
        checks.append(Check("roe", "ROE", PASS, f"{roe*100:.1f}% (duy trì ≥15%)", "≥ 15% & ổn định", 2.0))
    elif roe >= 0.15:
        checks.append(Check("roe", "ROE", WARN, f"{roe*100:.1f}% (chưa ổn định đa năm)", "≥ 15% & ổn định", 2.0))
    else:
        checks.append(Check("roe", "ROE", FAIL, f"{roe*100:.1f}% (< 15%)", "≥ 15% & ổn định", 2.0))

    # 2. ROA — sinh lời trên tài sản
    roa = num(f.get("roa"))
    if roa is None:
        checks.append(Check("roa", "ROA", NA, "—", "≥ 7–10%"))
    elif roa >= 0.10:
        checks.append(Check("roa", "ROA", PASS, f"{roa*100:.1f}%", "≥ 10%"))
    elif roa >= 0.07:
        checks.append(Check("roa", "ROA", WARN, f"{roa*100:.1f}%", "≥ 10%"))
    else:
        checks.append(Check("roa", "ROA", FAIL, f"{roa*100:.1f}%", "≥ 10%"))

    # 3. Biên lợi nhuận — xu hướng tăng / cao
    nm = num(f.get("net_margin"))
    trend = f.get("net_margin_trend")
    if nm is None:
        checks.append(Check("margin", "Biên ròng", NA, "—", "Cao & xu hướng tăng"))
    elif nm >= 0.15 or (nm >= 0.10 and trend == "up"):
        checks.append(Check("margin", "Biên ròng", PASS, f"{nm*100:.1f}% ({trend})", "Cao & xu hướng tăng", 1.5))
    elif nm >= 0.08:
        checks.append(Check("margin", "Biên ròng", WARN, f"{nm*100:.1f}% ({trend})", "Cao & xu hướng tăng", 1.5))
    else:
        checks.append(Check("margin", "Biên ròng", FAIL, f"{nm*100:.1f}% (thấp)", "Cao & xu hướng tăng", 1.5))

    # 4. Nợ — Debt/Equity < 0.5
    de = num(f.get("de_ratio"))
    if de is None:
        checks.append(Check("de", "Debt/Equity", NA, "—", "< 0.5"))
    elif de < 0.5:
        checks.append(Check("de", "Debt/Equity", PASS, f"{de:.2f}", "< 0.5", 1.5))
    elif de < 1.0:
        checks.append(Check("de", "Debt/Equity", WARN, f"{de:.2f}", "< 0.5", 1.5))
    else:
        checks.append(Check("de", "Debt/Equity", FAIL, f"{de:.2f} (nợ cao)", "< 0.5", 1.5))

    # 5. Thanh khoản — Current ratio > 1.5
    cr = num(f.get("current_ratio"))
    if cr is None:
        checks.append(Check("cr", "Current Ratio", NA, "—", "> 1.5"))
    elif cr >= 1.5:
        checks.append(Check("cr", "Current Ratio", PASS, f"{cr:.2f}", "> 1.5"))
    elif cr >= 1.0:
        checks.append(Check("cr", "Current Ratio", WARN, f"{cr:.2f}", "> 1.5"))
    else:
        checks.append(Check("cr", "Current Ratio", FAIL, f"{cr:.2f}", "> 1.5"))

    # 6. Định giá P/E — hợp lý + PEG
    pe = num(f.get("pe"))
    eps_g = num(f.get("eps_growth_3y"))
    if pe is None or pe <= 0:
        checks.append(Check("pe", "P/E", NA, "—", "Hợp lý (PEG ≤ ~1)"))
    elif eps_g and eps_g > 0:
        peg = pe / (eps_g * 100)
        if peg <= 1.0 and pe < 25:
            checks.append(Check("pe", "P/E (PEG)", PASS, f"P/E {pe:.1f}, PEG {peg:.2f}", "PEG ≤ 1", 1.5))
        elif peg <= 1.5:
            checks.append(Check("pe", "P/E (PEG)", WARN, f"P/E {pe:.1f}, PEG {peg:.2f}", "PEG ≤ 1", 1.5))
        else:
            checks.append(Check("pe", "P/E (PEG)", FAIL, f"P/E {pe:.1f}, PEG {peg:.2f} (đắt)", "PEG ≤ 1", 1.5))
    else:
        st = PASS if pe < 15 else (WARN if pe < 25 else FAIL)
        checks.append(Check("pe", "P/E", st, f"{pe:.1f}", "< 15–25", 1.5))

    # 7. Tăng trưởng EPS — ổn định dương
    if eps_g is None:
        checks.append(Check("eps_g", "Tăng trưởng EPS", NA, "—", "> 0 & ổn định"))
    elif eps_g >= 0.10:
        checks.append(Check("eps_g", "Tăng trưởng EPS", PASS, f"{eps_g*100:.1f}%/năm", "> 10%/năm"))
    elif eps_g > 0:
        checks.append(Check("eps_g", "Tăng trưởng EPS", WARN, f"{eps_g*100:.1f}%/năm", "> 10%/năm"))
    else:
        checks.append(Check("eps_g", "Tăng trưởng EPS", FAIL, f"{eps_g*100:.1f}%/năm", "> 10%/năm"))

    # 8. Biên an toàn — Graham number
    mos = num(f.get("margin_of_safety"))
    if mos is None:
        checks.append(Check("mos", "Biên an toàn (Graham)", NA, "—", "≥ 0 (thị giá ≤ giá trị)"))
    elif mos >= 0.2:
        checks.append(Check("mos", "Biên an toàn (Graham)", PASS, f"{mos*100:.0f}% rẻ hơn Graham", "≥ 20%", 2.0))
    elif mos >= 0.0:
        checks.append(Check("mos", "Biên an toàn (Graham)", WARN, f"{mos*100:.0f}%", "≥ 20%", 2.0))
    else:
        checks.append(Check("mos", "Biên an toàn (Graham)", FAIL, f"{mos*100:.0f}% (đắt hơn Graham)", "≥ 20%", 2.0))

    notes = []
    if f.get("rating"):
        notes.append(f"Định mức ngành (vnstock): {f['rating']}"
                     + (f", giá mục tiêu {f.get('target_price'):,.0f}" if f.get("target_price") else ""))
    return _finalize("value", checks, notes)
