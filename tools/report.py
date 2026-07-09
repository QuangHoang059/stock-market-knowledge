"""
Lắp báo cáo Markdown + chấm phán tổng hợp (verdict) cho bộ đánh giá cổ phiếu.

Verdict tổng hợp (auto) gộp các điểm số sẵn có:
  - value score      (0–100, bài 02)
  - growth/CANSLIM   (0–100, bài 03)
  - kỹ thuật → 0–100 (bull=75, neutral=50, bear=25, bài 01)
Trung bình có trọng số → KHUYẾN NGHỊ: MUA (≥65) / THEO DÕI (45–65) / TRÁNH (<45).
"""

from __future__ import annotations

from .value_score import Scorecard


def _fmt_vnd(v, suffix=""):
    if v is None:
        return "—"
    try:
        return f"{v:,.0f}{suffix}"
    except (TypeError, ValueError):
        return str(v)


def _fmt_pct(v):
    return f"{v*100:.1f}%" if isinstance(v, (int, float)) else "—"


def _num(v, nd=2):
    """Làm tròn số về nd chữ số thập phân; '—' nếu None."""
    if v is None:
        return "—"
    try:
        return f"{float(v):.{nd}f}"
    except (TypeError, ValueError):
        return str(v)


def _fmt_marketcap(v):
    """Vốn hóa thân thiện: vnstock trả về VND nguyên."""
    if not isinstance(v, (int, float)) or not v:
        return "—"
    if v >= 1e12:
        return f"{v/1e12:.1f} nghìn tỷ VND"
    if v >= 1e9:
        return f"{v/1e9:.0f} tỷ VND"
    return f"{v:,.0f} VND"


def scorecard_table(sc: Scorecard) -> str:
    """Bảng checklist PASS/WARN/FAIL cho một scorecard."""
    if sc is None:
        return "_(không có dữ liệu)_"
    rows = ["| # | Tiêu chí | Kết quả | Chi tiết | Ngưỡng |",
            "|---|----------|:-------:|----------|--------|"]
    badge = {"PASS": "✅ PASS", "WARN": "🟡 WARN", "FAIL": "❌ FAIL", "NA": "➖ NA"}
    for i, c in enumerate(sc.checks, 1):
        rows.append(f"| {i} | {c.label} | {badge.get(c.status, c.status)} | {c.detail} | {c.threshold} |")
    rows.append(f"\n**Điểm: {sc.score:.1f}/100 — {sc.grade}**")
    return "\n".join(rows)


def technical_table(t: dict) -> str:
    if not t or not t.get("indicators"):
        return "_(không có dữ liệu kỹ thuật)_"
    ind = t["indicators"]
    rows = [
        "| Chỉ báo | Giá trị |",
        "|---------|---------|",
        f"| Giá đóng | {_fmt_vnd(ind.get('price'))} VND |",
        f"| MA20 / MA50 / MA200 | {_fmt_vnd(ind.get('ma20'))} / {_fmt_vnd(ind.get('ma50'))} / {_fmt_vnd(ind.get('ma200'))} |",
        f"| RSI(14) | {ind.get('rsi14')} |",
        f"| MACD histogram | {ind.get('macd_hist')} |",
        f"| ATR(14) | {ind.get('atr_pct')}% |",
        f"| Bias tổng hợp | **{t.get('bias','').upper()}** |",
    ]
    return "\n".join(rows)


def signals_block(t: dict) -> str:
    sigs = t.get("signals") or []
    if not sigs:
        return "_(không có tín hiệu cụ thể)_"
    icon = {"bull": "🟢", "bear": "🔴", "neutral": "⚪"}
    lines = [f"{icon.get(s['bias'],'')} **[{s['bias'].upper()}]** {s['category']} — {s['name']}: {s['detail']}"
             for s in sigs]
    return "\n".join(lines)


def risk_table(risk) -> str:
    if risk is None:
        return "_(không có kế hoạch rủi ro — cần giá vào)_"
    d = risk.to_dict() if hasattr(risk, "to_dict") else risk
    rows = [
        "| Thông số | Giá trị |",
        "|----------|---------|",
        f"| Giá vào / Cắt lỗ / Mục tiêu | {_fmt_vnd(d.get('entry'))} / {_fmt_vnd(d.get('stop'))} / {_fmt_vnd(d.get('target'))} VND |",
        f"| Rủi ro/lệnh | {d.get('risk_pct')*100:.1f}% vốn = {_fmt_vnd(d.get('risk_money'))} VND |",
        f"| Cắt lỗ / Mục tiêu | {d.get('stop_pct')}% / {d.get('target_pct')}% |",
        f"| R:R (Reward:Risk) | {d.get('rr_ratio')} : 1 |",
        f"| Số cổ phiếu | {_fmt_vnd(d.get('shares'))} |",
        f"| Vốn giải ngân | {_fmt_vnd(d.get('deployable'))} VND ({d.get('deployable_pct')}% vốn) |",
        f"| Đánh giá | **{d.get('verdict')}** |",
    ]
    out = "\n".join(rows)
    if d.get("warnings"):
        out += "\n\n" + "\n".join(f"- ⚠️ {w}" for w in d["warnings"])
    return out


# --------------------------------------------------------------------------- #
# Verdict tổng hợp
# --------------------------------------------------------------------------- #
def composite(scores: dict[str, float], tech_bias: str) -> tuple[float, str, str]:
    """Trả (điểm tổng hợp 0–100, nhãn KHUYẾN NGHỊ, diễn giải)."""
    parts: list[tuple[float, float, str]] = []  # (score, weight, label)
    if scores.get("value") is not None:
        parts.append((scores["value"], 1.0, "Giá trị"))
    if scores.get("growth") is not None:
        parts.append((scores["growth"], 1.0, "CANSLIM"))
    if tech_bias:
        tb = {"bull": 75.0, "neutral": 50.0, "bear": 25.0}.get(tech_bias, 50.0)
        parts.append((tb, 0.8, "Kỹ thuật"))
    if not parts:
        return 0.0, "THIẾU DỮ LIỆU", "Không đủ dữ liệu để chấm tổng hợp."
    total_w = sum(w for _, w, _ in parts)
    score = sum(s * w for s, w, _ in parts) / total_w
    if score >= 65:
        label = "MUA / GIỮ (MẠNH)"
    elif score >= 45:
        label = "THEO DÕI"
    else:
        label = "TRÁNH / CHỜ"
    diag = " + ".join(f"{lab}: {s:.0f}" for s, _, lab in parts)
    return score, label, f"{diag} → {score:.0f}/100"


def build_report(r: dict) -> str:
    """Lắp báo cáo Markdown từ dict kết quả (evaluate.run)."""
    sym = r.get("symbol", "?")
    price = r.get("price")
    f = r.get("fundamentals") or {}
    style = r.get("style", "auto")
    today = r.get("date", "")

    lines: list[str] = []
    lines.append(f"# Đánh giá cổ phiếu **{sym}**")
    if f.get("company_name"):
        lines.append(f"_{f['company_name']}" + (f" — {f['sector']}" if f.get("sector") else "") + "_")
    lines.append(f"\n> Ngày: {today} · Giá: **{_fmt_vnd(price)} VND** · Phân tích theo: **{style}**\n")

    # 1. Snapshot cơ bản
    lines.append("## 1. Thông tin & định giá")
    snap = [
        (f"- Giá / P/E / P/B: **{_fmt_vnd(price)}** / {_num(f.get('pe'),1)} / {_num(f.get('pb'),2)}"
         if price else f"- P/E / P/B: {_num(f.get('pe'),1)} / {_num(f.get('pb'),2)}"),
        f"- Vốn hóa: {_fmt_marketcap(f.get('market_cap'))}",
        f"- ROE / ROA: {_fmt_pct(f.get('roe'))} / {_fmt_pct(f.get('roa'))}",
        f"- Biên ròng / Biên gộp: {_fmt_pct(f.get('net_margin'))} / {_fmt_pct(f.get('gross_margin'))}",
        f"- D/E / Current ratio: {_num(f.get('de_ratio'),2)} / {_num(f.get('current_ratio'),2)}",
        f"- EPS: {_num(f.get('eps_latest'),0)} | Tăng trưởng EPS 3 năm: {_fmt_pct(f.get('eps_growth_3y'))}",
        f"- Biên an toàn (Graham): {_fmt_pct(f.get('margin_of_safety'))} | Graham number: {_fmt_vnd(f.get('graham_number'))} VND",
    ]
    lines.append("\n".join(snap))

    # 2. Scorecards
    if r.get("value_score"):
        lines.append("\n## 2. Đánh giá Giá trị (Buffett — bài 02)")
        lines.append(scorecard_table(r["value_score"]))
    if r.get("canslim_score"):
        lines.append("\n## 3. Đánh giá Tăng trưởng (CANSLIM — bài 03)")
        lines.append(scorecard_table(r["canslim_score"]))
        for n in (r["canslim_score"].notes or []):
            lines.append(f"\n_{n}_")

    # 3. Kỹ thuật
    tech = r.get("technical")
    if tech:
        lines.append("\n## 4. Phân tích Kỹ thuật (bài 01, 04, 05)")
        lines.append(technical_table(tech))
        lines.append("\n**Tín hiệu:**\n")
        lines.append(signals_block(tech))
        lv = tech.get("levels") or {}
        if lv.get("support") or lv.get("resistance"):
            lines.append(f"\n**Hỗ trợ:** {lv.get('support')} · **Kháng cự:** {lv.get('resistance')}")
        fib = lv.get("fib")
        if fib:
            lines.append(f"\n**Fibonacci** (nhịp {fib.get('direction')}, "
                         f"{fib.get('from')}→{fib.get('to')}): thoái lui 38.2%={fib['retracement'][0.382]}, "
                         f"50%={fib['retracement'][0.5]}, 61.8%={fib['retracement'][0.618]} · "
                         f"mở rộng 161.8%={fib.get('ext_1618')}")

    # 4. Rủi ro
    if r.get("risk"):
        lines.append("\n## 5. Kế hoạch rủi ro (bài 06)")
        lines.append(risk_table(r["risk"]))

    # 5. Verdict
    lines.append("\n## 6. Khuyến nghị tổng hợp")
    score, label, diag = composite(r.get("scores", {}), (tech or {}).get("bias", ""))
    lines.append(f"### **{label}** — {score:.0f}/100")
    lines.append(f"_{diag}_")
    if r.get("caveats"):
        lines.append("\n**Lưu ý dữ liệu:**")
        lines.extend(f"- ⚠️ {c}" for c in r["caveats"])

    lines.append("\n---")
    lines.append("> ⚠️ **Miễn trừ trách nhiệm**: Báo cáo do công cụ tự động tổng hợp từ dữ liệu "
                 "vnstock/Yahoo và **không phải khuyến nghị đầu tư**. Mọi quyết định giao dịch "
                 "thuộc về bạn. Đầu tư chứng khoán có rủi ro mất vốn.")
    return "\n".join(lines)
