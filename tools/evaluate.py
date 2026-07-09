"""
CLI duy nhất để đánh giá cổ phiếu.

Cách dùng:
    python -m tools.evaluate <MÃ> [--style value|growth|technical|auto]
                               [--index VNINDEX] [--capital 100000000] [--risk 1.5]
                               [--years 3] [--json]

Ví dụ:
    python -m tools.evaluate FPT
    python -m tools.evaluate FPT --style value
    python -m tools.evaluate FPT --capital 200000000 --risk 1.5
    python -m tools.evaluate ^VNINDEX --style technical
    python -m tools.evaluate DIG
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import logging
import sys

from . import data as D
from . import indicators as I
from . import technical as T
from . import risk as R
from . import value_score as VS
from . import canslim_score as CS
from . import report as REP

logger = logging.getLogger("tools.evaluate")


def _benchmark_history(index_symbol: str, years: int):
    """Lấy lịch sử chỉ số với fallback (^VNINDEX → VNINDEX)."""
    for sym in (index_symbol, "VNINDEX"):
        if not sym:
            continue
        df = D.get_history(sym, years=years)
        if df is not None and not df.empty:
            return df, sym
    return None, index_symbol


def run(symbol: str, style: str = "auto", index_symbol: str = "VNINDEX",
        capital: float = 1e8, risk_pct: float = 1.5, years: int = 3) -> dict:
    """Chạy toàn bộ pipeline, trả dict kết quả đầy đủ (dùng cho cả report & JSON)."""
    symbol = symbol.strip().upper()
    caveats: list[str] = []

    hist = D.get_history(symbol, years=years)
    if hist is None or hist.empty:
        caveats.append(f"Không lấy được dữ liệu giá cho {symbol}.")
    price = float(hist["close"].iloc[-1]) if hist is not None and not hist.empty else None

    # Cơ bản (chỉ cổ phiếu VN)
    f = D.get_fundamentals(symbol)
    if not f:
        if D.is_yahoo_symbol(symbol):
            caveats.append(f"{symbol} là chỉ số/mã nước ngoài — không có dữ liệu cơ bản VN.")
        else:
            caveats.append(f"Không lấy được dữ liệu cơ bản cho {symbol} (vnstock?).")

    # Chỉ số + RS rank
    index_trend = D.get_index_trend(index_symbol)
    bench, bench_sym = _benchmark_history(index_symbol, years=2)
    rs_rank = None
    if hist is not None and not hist.empty and bench is not None and not bench.empty:
        try:
            rs_rank = I.rs_rank(hist["close"], bench["close"])
        except Exception as e:  # noqa: BLE001
            logger.warning("rs_rank lỗi: %s", e)
    if rs_rank is None:
        caveats.append("Không tính được RS rank (thiếu dữ liệu chỉ số so sánh).")

    # CANSLIM cần EPS quý YoY; cảnh báo nếu thiếu
    if f and f.get("eps_q_yoy_growth") is None:
        caveats.append("CANSLIM 'C': vnstock chỉ có 4 quý gần nhất → dùng tăng trưởng EPS năm thay cho EPS quý YoY.")

    # Chạy scorecard theo style
    value_sc = VS.score_value(f) if f else None
    canslim_sc = CS.score_canslim(f, hist, rs_rank, index_trend) if f else None
    tech = T.analyze(hist) if hist is not None else None

    if style == "value":
        value_sc = value_sc
        canslim_sc = None
    elif style == "growth":
        canslim_sc = canslim_sc
        value_sc = None
    elif style == "technical":
        value_sc = None
        canslim_sc = None

    # Kế hoạch rủi ro (cần giá)
    risk_plan = None
    if price:
        atrp = R.atr_pct(hist) if hist is not None else None
        atr_abs = price * atrp / 100 if atrp else None
        stop = R.suggest_stop(price, atr_abs, method="atr") if atr_abs else R.suggest_stop(price, None, method="oneil")
        target = R.suggest_target(price, stop, rr=2.0)
        try:
            risk_plan = R.position_size(capital, risk_pct / 100.0, price, stop, target)
        except ValueError as e:
            caveats.append(f"Không lập được kế hoạch rủi ro: {e}")

    scores: dict[str, float] = {}
    if value_sc and value_sc.grade != "THIẾU DỮ LIỆU":
        scores["value"] = value_sc.score
    if canslim_sc and canslim_sc.grade != "THIẾU DỮ LIỆU":
        scores["growth"] = canslim_sc.score

    return {
        "symbol": symbol, "style": style, "date": dt.date.today().isoformat(),
        "price": price, "fundamentals": f,
        "value_score": value_sc, "canslim_score": canslim_sc,
        "technical": tech, "risk": risk_plan, "index_trend": index_trend,
        "rs_rank": rs_rank, "benchmark": bench_sym,
        "scores": scores, "caveats": caveats,
    }


def _to_jsonable(r: dict) -> dict:
    out = {
        "symbol": r["symbol"], "style": r["style"], "date": r["date"],
        "price": r["price"], "rs_rank": r["rs_rank"], "benchmark": r["benchmark"],
        "value_score": r["value_score"].to_dict() if r.get("value_score") else None,
        "canslim_score": r["canslim_score"].to_dict() if r.get("canslim_score") else None,
        "technical": r.get("technical"),
        "risk": r["risk"].to_dict() if r.get("risk") else None,
        "scores": r["scores"], "caveats": r["caveats"],
        "composite": REP.composite(r["scores"], (r.get("technical") or {}).get("bias", "")),
    }
    return out


def main(argv=None) -> int:
    p = argparse.ArgumentParser(
        prog="tools.evaluate", description="Đánh giá cổ phiếu theo giá trị/tăng trưởng/kỹ thuật.")
    p.add_argument("symbol", help="Mã cổ phiếu (FPT, DIG) hoặc chỉ số (^VNINDEX, AAPL).")
    p.add_argument("--style", choices=["value", "growth", "technical", "auto"], default="auto")
    p.add_argument("--index", default="VNINDEX", help="Chỉ số so sánh (mặc định VNINDEX).")
    p.add_argument("--capital", type=float, default=1e8, help="Vốn (VND), mặc định 100 triệu.")
    p.add_argument("--risk", type=float, default=1.5, help="Rủi ro %/lệnh (mặc định 1.5).")
    p.add_argument("--years", type=int, default=3, help="Số năm dữ liệu lịch sử.")
    p.add_argument("--json", action="store_true", help="Xuất JSON thay vì Markdown.")
    args = p.parse_args(argv)

    logging.basicConfig(level=logging.WARNING, format="%(message)s")
    r = run(args.symbol, style=args.style, index_symbol=args.index,
            capital=args.capital, risk_pct=args.risk, years=args.years)

    if args.json:
        json.dump(_to_jsonable(r), sys.stdout, ensure_ascii=False, indent=2, default=str)
        sys.stdout.write("\n")
    else:
        sys.stdout.write(REP.build_report(r) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
