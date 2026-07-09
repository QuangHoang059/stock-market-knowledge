"""
Lớp dữ liệu cho bộ đánh giá cổ phiếu.

Nguồn:
  - Cổ phiếu Việt Nam: vnstock 4.x (Quote.history cho OHLCV; Finance.income_statement /
    balance_sheet cho cơ bản; Company.overview cho thông tin/vốn hóa).
  - Chỉ số quốc tế / mã nước ngoài: Yahoo Finance v8 chart (OHLCV). Không có cơ bản.

Thiết kế:
  - Mọi lệnh gọi vnstock được bọc để tắt banner/quảng cáo (hush).
  - Phân tích cơ bản tự TÍNH từ báo cáo tài chính (ROE, ROA, biên, D/E, current ratio,
    EPS) thay vì dùng Finance.ratio() (cột kỳ hạn bị lỗi trong vnstock 4.0.4).
  - Nếu thiếu dữ liệu → trả giá trị None và báo cáo sẽ ghi chú, không ném lỗi.
"""

from __future__ import annotations

import contextlib
import io
import logging
import time
from typing import Optional

import httpx
import pandas as pd

logger = logging.getLogger(__name__)

HTTP_HEADERS = {
    "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                   "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")
}

# --------------------------------------------------------------------------- #
# vnstock availability + phiên bản
# --------------------------------------------------------------------------- #
_VNSTOCK_OK = False
try:
    import vnstock as _vns  # noqa: F401
    _VNSTOCK_OK = True
except Exception as _e:  # noqa: BLE001
    logger.info("vnstock chưa cài (%s) — cổ phiếu VN sẽ không có dữ liệu.", _e)

# Source mặc định (VCI ổn định cho cả Quote/Finance/Company).
_VN_SOURCE = "VCI"


def _hush(fn, *args, **kwargs):
    """Chạy fn mà chặn stdout/stderr (vnstock in nhiều banner/quảng cáo)."""
    buf_out, buf_err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(buf_out), contextlib.redirect_stderr(buf_err):
        return fn(*args, **kwargs)


def is_yahoo_symbol(symbol: str) -> bool:
    """True với chỉ số (^xxx) hoặc mã đã có hậu tố (000001.SS, AAPL, DIG.VN)."""
    return symbol.startswith("^") or "." in symbol


def looks_like_vn(symbol: str) -> bool:
    """Heuristic: mã trần (không ^, không .) → khả năng là cổ phiếu VN."""
    return (not is_yahoo_symbol(symbol)) and symbol.strip() != ""


# --------------------------------------------------------------------------- #
# Yahoo Finance — OHLCV cho chỉ số / mã nước ngoài
# --------------------------------------------------------------------------- #
_YAHOO_CRUMB: Optional[str] = None


def _yahoo_history_sync(symbol: str, years: int) -> pd.DataFrame:
    """Lấy OHLCV qua v8 chart (đồng bộ). Trả DataFrame index=date, cột OHLCV.
    Trả DataFrame rỗng nếu mã không tồn tại (404) hoặc lỗi mạng — không raise."""
    end = int(time.time())
    start = end - years * 365 * 24 * 3600
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
    params = {"period1": start, "period2": end, "interval": "1d", "events": "div,split"}
    try:
        with httpx.Client(headers=HTTP_HEADERS, timeout=20, follow_redirects=True) as client:
            for _ in range(2):
                r = client.get(url, params=params)
                if r.status_code in (401, 429):
                    try:
                        params["crumb"] = client.get(
                            "https://query1.finance.yahoo.com/v1/test/getcrumb").text.strip()
                        continue
                    except Exception:
                        break
                if r.status_code >= 400:
                    return pd.DataFrame()
                break
            data = r.json().get("chart", {}).get("result")
            if not data:
                return pd.DataFrame()
            data = data[0]
            ts = data.get("timestamp") or []
            q = data["indicators"]["quote"][0]
            df = pd.DataFrame({
                "open": q.get("open"), "high": q.get("high"), "low": q.get("low"),
                "close": q.get("close"), "volume": q.get("volume"),
            }, index=pd.to_datetime(ts, unit="s", utc=True).tz_convert(None))
            df = df.dropna(subset=["close"])
            df.index.name = "date"
            return df
    except Exception as e:  # noqa: BLE001
        logger.warning("Yahoo chart %s lỗi: %s", symbol, e)
        return pd.DataFrame()


# --------------------------------------------------------------------------- #
# OHLCV công khai
# --------------------------------------------------------------------------- #
def _fetch_vn(symbol: str, years: int) -> pd.DataFrame:
    """Lấy OHLCV cổ phiếu/chỉ số VN qua vnstock Quote.history (đã chuẩn hoá VND)."""
    if not _VNSTOCK_OK:
        return pd.DataFrame()
    try:
        from vnstock.api.quote import Quote
        raw = _hush(Quote(source=_VN_SOURCE, symbol=symbol, show_log=False).history,
                    start=_years_ago_str(years), end=_today_str(), interval="1D")
        return _normalize_vn_history(raw)
    except Exception as e:  # noqa: BLE001
        logger.warning("vnstock history lỗi cho %s: %s", symbol, e)
        return pd.DataFrame()


def get_history(symbol: str, years: int = 3) -> pd.DataFrame:
    """Lấy lịch sử OHLCV (index=date; cột open/high/low/close/volume).

    Tuyến: mã trần VN → vnstock; chỉ số/mã có hậu tố → Yahoo.
    Đặc biệt: VN-Index (^VNINDEX/VNINDEX) không có trên Yahoo → ưu tiên vnstock.
    Nếu mã VN không có trên vnstock, thử Yahoo (đuôi .VN rồi nguyên dạng)."""
    sym = symbol.strip()
    norm = sym.upper().lstrip("^")
    # VN-Index: Yahoo không mang chỉ số Việt Nam → luôn ưu tiên vnstock.
    if norm == "VNINDEX" and _VNSTOCK_OK:
        df = _fetch_vn("VNINDEX", years)
        if not df.empty:
            return df

    if is_yahoo_symbol(sym):
        return _yahoo_history_sync(sym, years)

    df = _fetch_vn(sym, years)

    if df.empty:  # fallback Yahoo
        for cand_sym in (sym + ".VN", sym):
            try:
                cand = _yahoo_history_sync(cand_sym, years)
            except Exception as e:  # noqa: BLE001
                logger.warning("Yahoo fallback lỗi (%s): %s", cand_sym, e)
                continue
            if not cand.empty:
                df = cand
                break
    return df


def _normalize_vn_history(raw) -> pd.DataFrame:
    if raw is None or not isinstance(raw, pd.DataFrame) or raw.empty:
        return pd.DataFrame()
    df = raw.copy()
    colmap = {c: c.lower().strip() for c in df.columns}
    df = df.rename(columns=colmap)
    tcol = "time" if "time" in df.columns else df.columns[0]
    df["date"] = pd.to_datetime(df[tcol], errors="coerce")
    df = df.dropna(subset=["date"]).set_index("date").sort_index()
    keep = [c for c in ("open", "high", "low", "close", "volume") if c in df.columns]
    df = df[keep].apply(pd.to_numeric, errors="coerce")
    # vnstock Quote.history trả giá theo NGHÌN (72.3); chuẩn hoá về VND (72_300)
    # để đồng bộ với EPS/overview và module rủi ro.
    for col in ("open", "high", "low", "close"):
        if col in df.columns:
            df[col] = df[col] * 1000.0
    return df.dropna(subset=["close"])


# --------------------------------------------------------------------------- #
# Cơ bản (chỉ cổ phiếu VN)
# --------------------------------------------------------------------------- #
# Ánh xạ nhãn item_en (theo dữ liệu thật của vnstock 4.0.4) -> khoá nội bộ.
# Dùng danh sách để khớp linh hoạt khi nhãn hơi khác giữa các ngành.
_LABEL_MAP = {
    "revenue": ["Net sales", "Sales", "Total revenue"],
    "gross_profit": ["Gross Profit", "Gross profit"],
    "operating_income": ["Operating profit/(loss)", "Operating profit", "Operating income"],
    "net_income": ["Net profit/(loss) after tax", "Net profit after tax",
                   "Net income", "Profit after tax"],
    "eps": ["EPS basic (VND)", "Basic EPS", "EPS"],
    "current_assets": ["CURRENT ASSETS", "Total current assets"],
    "total_assets": ["Total Assets", "TOTAL ASSETS"],
    "total_liabilities": ["Liabilities", "Total liabilities"],
    "current_liabilities": ["Current liabilities", "Total current liabilities"],
    "short_term_debt": ["Short-term borrowings", "Short-term debt", "Short-term loans"],
    "long_term_debt": ["Long-term borrowings", "Long-term debt", "Long-term loans"],
    "equity": ["Owner's Equity", "Owners equity", "Total equity"],
}


def _extract_rows(df: pd.DataFrame) -> dict[str, dict[str, float]]:
    """Chuyển statement dạng 'dài' (hàng = item_en, cột = năm) -> {key: {year: value}}."""
    if df is None or not isinstance(df, pd.DataFrame) or "item_en" not in df.columns:
        return {}
    year_cols = [c for c in df.columns if str(c)[:4].isdigit()]
    out: dict[str, dict[str, float]] = {}
    label_lower = {str(x).strip().lower(): str(x).strip() for x in df["item_en"]}
    for key, candidates in _LABEL_MAP.items():
        chosen_col = None
        for cand in candidates:
            if cand.strip().lower() in label_lower:
                chosen_col = label_lower[cand.strip().lower()]
                break
        if chosen_col is None:
            continue
        row = df[df["item_en"] == chosen_col].iloc[0]
        series = {}
        for c in year_cols:
            v = row[c]
            try:
                v = float(v)
                if pd.notna(v):
                    series[str(c)] = v
            except (TypeError, ValueError):
                continue
        out[key] = series
    return out


def _ratio(num, den, years):
    return {y: (num.get(y) / den.get(y)) for y in years
            if num.get(y) not in (None, 0) and den.get(y) not in (None, 0)
            and den.get(y)}


def _growth(series: dict[str, float], n: int) -> Optional[float]:
    """Tăng trưởng kép (CAGR) qua n năm gần nhất có dữ liệu, hoặc None."""
    yrs = sorted(series.keys())
    if len(yrs) < 2:
        return None
    end = yrs[-1]
    start_idx = max(0, len(yrs) - 1 - n)
    start = yrs[start_idx]
    a, b = series[start], series[end]
    if not a or not b or a <= 0:
        # fallback: tăng trưởng giản đơn năm cuối
        prev = yrs[-2]
        if series.get(prev):
            return (series[end] - series[prev]) / abs(series[prev])
        return None
    span = max(1, len(yrs) - 1 - start_idx)
    return (b / a) ** (1 / span) - 1


def get_fundamentals(symbol: str) -> dict:
    """Trả dict cơ bản cho cổ phiếu VN. Rỗng {} nếu không phải VN / không có dữ liệu."""
    if not _VNSTOCK_OK or not looks_like_vn(symbol):
        return {}
    from vnstock.api import financial
    try:
        fin = financial.Finance(source=_VN_SOURCE, symbol=symbol,
                                period="year", get_all=False, show_log=False)
        inc = _hush(fin.income_statement)
        bs = _hush(fin.balance_sheet)
    except Exception as e:  # noqa: BLE001
        logger.warning("Lấy báo cáo tài chính %s lỗi: %s", symbol, e)
        return {}

    inc_rows = _extract_rows(inc)
    bs_rows = _extract_rows(bs)
    if not inc_rows:
        return {}

    years = sorted({y for d in (inc_rows, bs_rows) for s in d.values() for y in s})
    f = {
        "symbol": symbol, "years": years,
        "source": "vnstock",
        "revenue": inc_rows.get("revenue", {}),
        "gross_profit": inc_rows.get("gross_profit", {}),
        "operating_income": inc_rows.get("operating_income", {}),
        "net_income": inc_rows.get("net_income", {}),
        "eps": inc_rows.get("eps", {}),
        "current_assets": bs_rows.get("current_assets", {}),
        "total_assets": bs_rows.get("total_assets", {}),
        "total_liabilities": bs_rows.get("total_liabilities", {}),
        "current_liabilities": bs_rows.get("current_liabilities", {}),
        "short_term_debt": bs_rows.get("short_term_debt", {}),
        "long_term_debt": bs_rows.get("long_term_debt", {}),
        "equity": bs_rows.get("equity", {}),
    }

    # Tỷ số theo năm (cho xu hướng)
    f["roe_series"] = _ratio(f["net_income"], f["equity"], years)
    f["gross_margin_series"] = _ratio(f["gross_profit"], f["revenue"], years)
    f["net_margin_series"] = _ratio(f["net_income"], f["revenue"], years)
    f["de_series"] = _ratio(f["total_liabilities"], f["equity"], years)

    def latest(s):
        return s[list(s)[-1]] if s else None

    f["latest_year"] = years[-1] if years else None
    f["roe"] = latest(f["roe_series"])
    f["roa"] = (latest(f["net_income"]) / latest(f["total_assets"])) if latest(f["total_assets"]) else None
    f["gross_margin"] = latest(f["gross_margin_series"])
    f["net_margin"] = latest(f["net_margin_series"])
    f["de_ratio"] = latest(f["de_series"])
    f["current_ratio"] = (latest(f["current_assets"]) / latest(f["current_liabilities"])) if latest(f["current_liabilities"]) else None
    f["equity_ratio"] = (latest(f["equity"]) / latest(f["total_assets"])) if latest(f["total_assets"]) else None
    f["eps_latest"] = latest(f["eps"])
    f["eps_growth_3y"] = _growth(f["eps"], 3)
    f["revenue_growth_3y"] = _growth(f["revenue"], 3)
    f["net_income_growth_3y"] = _growth(f["net_income"], 3)

    # Xu hướng biên (so 3 năm gần nhất)
    f["net_margin_trend"] = _trend(f["net_margin_series"])
    f["roe_stable"] = _is_stable_high(f["roe_series"], 0.15)

    # Định giá + thông tin công ty + EPS quý (CANSLIM C)
    ov = company_overview(symbol)
    f["price"] = ov.get("current_price") or latest_price(symbol)
    f["company_name"] = ov.get("organ_short_name") or ov.get("organ_name")
    f["sector"] = ov.get("sector")
    f["rating"] = ov.get("rating")
    f["target_price"] = ov.get("target_price")
    f["high52"] = ov.get("highest_price1_year")
    f["low52"] = ov.get("lowest_price1_year")
    f["dividend_yield"] = ov.get("dividend_yield")
    f["is_bank"] = bool(ov.get("is_bank"))
    f.update(_valuation(f, f["price"]))
    f["eps_q_yoy_growth"] = _quarterly_eps_yoy(symbol)
    return f


def _trend(series: dict) -> str:
    vals = [v for _, v in sorted(series.items())][-3:]
    if len(vals) < 2:
        return "n/a"
    if vals[-1] > vals[0] * 1.05:
        return "up"
    if vals[-1] < vals[0] * 0.95:
        return "down"
    return "flat"


def _is_stable_high(series: dict, threshold: float) -> bool:
    vals = [v for _, v in sorted(series.items())][-5:]
    return len(vals) >= 3 and all(v >= threshold for v in vals)


def _valuation(f: dict, price: Optional[float]) -> dict:
    """Định giá dùng giá & shares từ Company.overview (VND), tránh lệch đơn vị với EPS (VND)."""
    out = {"pe": None, "pb": None, "market_cap": None, "shares": None,
           "graham_number": None, "margin_of_safety": None}
    ov = company_overview(f["symbol"])
    # Ưu tiên giá/market cap trực tiếp từ overview (VND); fallback price truyền vào.
    vnd_price = ov.get("current_price") or price
    out["market_cap"] = ov.get("market_cap")
    out["shares"] = _shares_outstanding(f["symbol"])
    eps = f["eps_latest"]
    eq = f["equity"].get(f["latest_year"]) if f.get("equity") and f.get("latest_year") else None
    if vnd_price and eps and eps > 0:
        out["pe"] = vnd_price / eps
        if eq and out["shares"]:
            bvps = eq / out["shares"]
            if bvps > 0:
                out["pb"] = vnd_price / bvps
                out["graham_number"] = (22.5 * eps * bvps) ** 0.5
                out["margin_of_safety"] = (out["graham_number"] - vnd_price) / out["graham_number"]
    return out


_OVERVIEW_CACHE: dict[str, dict] = {}


def company_overview(symbol: str) -> dict:
    """Trả bản ghi Company.overview() (current_price VND, market_cap, issue_share, rating...).
    Có cache theo symbol. Trả {} nếu không phải VN / lỗi."""
    if symbol in _OVERVIEW_CACHE:
        return _OVERVIEW_CACHE[symbol]
    if not _VNSTOCK_OK or not looks_like_vn(symbol):
        _OVERVIEW_CACHE[symbol] = {}
        return _OVERVIEW_CACHE[symbol]
    try:
        from vnstock.api.company import Company
        ov = _hush(Company(source=_VN_SOURCE, symbol=symbol, show_log=False).overview)
        if ov is None or not isinstance(ov, pd.DataFrame) or ov.empty:
            _OVERVIEW_CACHE[symbol] = {}
            return _OVERVIEW_CACHE[symbol]
        rec = {k: (None if pd.isna(v) else v) for k, v in ov.iloc[0].items()}
    except Exception as e:  # noqa: BLE001
        logger.warning("Company.overview %s lỗi: %s", symbol, e)
        rec = {}
    _OVERVIEW_CACHE[symbol] = rec
    return rec


def _shares_outstanding(symbol: str) -> Optional[float]:
    for k in ("issue_share", "outstanding_share", "share_outstanding", "listed_share"):
        v = company_overview(symbol).get(k)
        if v not in (None, "", 0):
            try:
                return float(v)
            except (TypeError, ValueError):
                continue
    return None


def _quarterly_eps_yoy(symbol: str) -> Optional[float]:
    """Tăng trưởng EPS quý gần nhất so cùng quý năm trước (CANSLIM 'C')."""
    if not _VNSTOCK_OK:
        return None
    try:
        from vnstock.api import financial
        fin = financial.Finance(source=_VN_SOURCE, symbol=symbol,
                                period="quarter", get_all=False, show_log=False)
        inc = _hush(fin.income_statement)
        rows = _extract_rows(inc)
        eps = rows.get("eps")
        if not eps or len(eps) < 5:
            return None
        # Cột dạng '2024-Q3'; lấy quý mới nhất và cùng quý năm trước
        keys = sorted(eps.keys())
        last = keys[-1]
        yr, q = last.split("-Q")
        prev = f"{int(yr) - 1}-Q{q}"
        if prev in eps and eps[prev]:
            return (eps[last] - eps[prev]) / abs(eps[prev])
    except Exception as e:  # noqa: BLE001
        logger.warning("EPS quý %s lỗi: %s", symbol, e)
    return None


# --------------------------------------------------------------------------- #
# Giá hiện tại & xu hướng chỉ số
# --------------------------------------------------------------------------- #
def latest_price(symbol: str) -> Optional[float]:
    df = get_history(symbol, years=1)
    if df.empty:
        return None
    return float(df["close"].iloc[-1])


def get_index_trend(index_symbol: str = "VNINDEX") -> dict:
    """Tóm tắt xu hướng chỉ số cho CANSLIM 'M'.

    VN-Index lấy qua vnstock (symbol 'VNINDEX'); các chỉ số quốc tế qua Yahoo.
    Chịu lỗi: nếu không lấy được → available=False (báo cáo sẽ ghi chú)."""
    out = {"index": index_symbol, "available": False}
    df = pd.DataFrame()
    for sym in (index_symbol, "VNINDEX" if index_symbol == "^VNINDEX" else index_symbol):
        try:
            cand = get_history(sym, years=2)
        except Exception as e:  # noqa: BLE001
            logger.warning("Lấy chỉ số %s lỗi: %s", sym, e)
            continue
        if cand is not None and not cand.empty:
            df = cand
            out["index"] = sym
            break
    if df.empty or len(df) < 50:
        return out
    close = df["close"]
    out.update({
        "available": True,
        "price": float(close.iloc[-1]),
        "ma50": float(close.rolling(50).mean().iloc[-1]),
        "ma200": float(close.rolling(200).mean().iloc[-1]) if len(df) >= 200 else None,
        "pct_off_high52": float(close.iloc[-1] / close.tail(252).max() - 1),
        "uptrend": None,
    })
    p, m50, m200 = out["price"], out["ma50"], out["ma200"]
    out["uptrend"] = bool(p > m50 > m200) if m200 else bool(p > m50)
    return out


# --------------------------------------------------------------------------- #
# Tiện ích ngày tháng
# --------------------------------------------------------------------------- #
def _today_str() -> str:
    import datetime as dt
    return dt.date.today().strftime("%Y-%m-%d")


def _years_ago_str(years: int) -> str:
    import datetime as dt
    return (dt.date.today() - dt.timedelta(days=years * 365)).strftime("%Y-%m-%d")
