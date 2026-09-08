"""Tool wrappers cho MCP server — 12 tools gom thành 5 nhóm.

Mỗi tool đều:
- Wrap một hàm trong `tools/` (không re-implement logic).
- Bắt exception, trả `{"error": ..., "tool": ...}` thay vì raise để agent
  remote không bị crash khi 1 symbol fail.
- Trả dict JSON-safe (Scorecard/RiskPlan đã có `.to_dict()`, DataFrame
  convert qua `_df_to_records`).

Khi `python -m mcp_server` chạy từ bất kỳ CWD nào, package `tools/` (cùng
repo root) phải import được → tự thêm REPO_ROOT vào sys.path.
"""

from __future__ import annotations

import logging
import re
import sys
from pathlib import Path

# Đảm bảo `from tools import ...` chạy được bất kể CWD.
_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

import pandas as pd  # noqa: E402  (sau sys.path hack)

from tools import canslim_score as CS  # noqa: E402
from tools import data as D  # noqa: E402
from tools import evaluate as EV  # noqa: E402
from tools import indicators as I  # noqa: E402
from tools import risk as R  # noqa: E402
from tools import technical as T  # noqa: E402
from tools import value_score as VS  # noqa: E402

logger = logging.getLogger(__name__)

MARKET_REPORTS_DIR: Path = _REPO_ROOT / "market_reports"
SAFE_FILENAME_RE = re.compile(r"^[A-Za-z0-9._-]+\.md$")


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _df_to_records(df: pd.DataFrame) -> list[dict]:
    """Convert OHLCV DataFrame sang list-of-dicts với date ISO string.

    Input df có index tên 'date' (datetime64) hoặc DatetimeIndex.
    Output: `[{"date": "2024-01-02", "open": 100.0, "high": ..., ...}, ...]`
    """
    if df is None or df.empty:
        return []
    out = df.reset_index()
    # Đổi tên cột index → "date" (nếu có)
    if "index" in out.columns and "date" not in out.columns:
        out = out.rename(columns={"index": "date"})
    if "Date" in out.columns and "date" not in out.columns:
        out = out.rename(columns={"Date": "date"})
    # Cột date → ISO string
    if "date" in out.columns:
        out["date"] = pd.to_datetime(out["date"]).dt.strftime("%Y-%m-%d")
    return out.to_dict(orient="records")


def _safe_call(tool_name: str, fn, /, *args, **kwargs) -> dict:
    """Wrap exception thành dict JSON thay vì raise."""
    try:
        return {"ok": True, "data": fn(*args, **kwargs)}
    except Exception as e:  # noqa: BLE001 — wrap tất cả để tool không crash
        logger.exception("Tool %s lỗi: %s", tool_name, e)
        return {
            "ok": False,
            "tool": tool_name,
            "error": f"{type(e).__name__}: {e}",
            "args": {"positional": list(args), "kwargs": kwargs},
        }


def _validate_filename(filename: str) -> None:
    """Validate filename report — raise ValueError nếu không hợp lệ."""
    if not SAFE_FILENAME_RE.match(filename or ""):
        raise ValueError(
            f"Filename không hợp lệ: '{filename}'. "
            f"Chỉ chấp nhận [A-Za-z0-9._-]+ với đuôi .md."
        )
    target = (MARKET_REPORTS_DIR / filename).resolve()
    if MARKET_REPORTS_DIR.resolve() not in target.parents and target != MARKET_REPORTS_DIR:
        raise ValueError(f"Filename vượt ngoài thư mục market_reports/: '{filename}'.")


def _check_timesfm_available() -> dict | None:
    """Trả None nếu torch + timesfm3 sẵn sàng; dict error JSON nếu thiếu.

    MCP server KHÔNG được crash khi user chưa cài torch/timesfm3 — chỉ trả
    error JSON để agent remote hiển thị thân thiện.
    """
    try:
        # Lazy import — KHÔNG thêm top-level import để tránh crash server.
        from tools.timesfm import is_available
        from tools.timesfm.model import get_availability_status

        if not is_available():
            return {
                "ok": False,
                "tool": "timesfm_*",
                "error": (
                    "torch + timesfm3 chưa sẵn sàng. "
                    "Chạy `pip install -r requirements-ml.txt` rồi copy thư mục "
                    "timesfm3/ từ Google upstream (google-research/timesfm) vào "
                    "stock-market-knowledge/timesfm3/."
                ),
                "availability": get_availability_status(),
            }
        return None
    except ImportError as e:
        return {
            "ok": False,
            "tool": "timesfm_*",
            "error": f"Không import được tools.timesfm: {e}",
        }


# ─────────────────────────────────────────────────────────────────────────────
# Tool registration
# ─────────────────────────────────────────────────────────────────────────────

def register_tools(mcp) -> None:
    """Đăng ký 12 tools lên FastMCP instance."""

    # ── Nhóm 1: Pipeline tổng hợp ──────────────────────────────────────────

    @mcp.tool(
        name="evaluate_stock",
        title="Đánh giá cổ phiếu tổng hợp",
        description=(
            "Chạy toàn bộ pipeline đánh giá một mã cổ phiếu (hoặc chỉ số) theo "
            "các trường phái: giá trị (Buffett), tăng trưởng (CANSLIM), kỹ thuật "
            "(MA/RSI/MACD/Wyckoff/Elliott), kèm kế hoạch quản trị rủi ro "
            "(position sizing, R:R). Dùng cho mọi yêu cầu 'đánh giá/phân tích "
            "mã X'."
        ),
    )
    def evaluate_stock(  # pyright: ignore[reportUnusedFunction]
        symbol: str,
        style: str = "auto",
        capital: float = 100_000_000,
        risk_pct: float = 1.5,
        years: int = 3,
    ) -> dict:
        """Đánh giá cổ phiếu tổng hợp (value/growth/technical/all).

        Args:
            symbol: Mã cổ phiếu (FPT, DIG, ...) hoặc chỉ số (^VNINDEX, AAPL).
            style: 'value' | 'growth' | 'technical' | 'auto' (mặc định).
            capital: Vốn (VND). Mặc định 100 triệu.
            risk_pct: Rủi ro mỗi lệnh (% vốn). Mặc định 1.5.
            years: Số năm dữ liệu lịch sử. Mặc định 3.

        Returns:
            Dict JSON gồm value_score, canslim_score, technical, risk, scores,
            composite verdict, caveats. Shape giống `python -m tools.evaluate X --json`.
        """
        def _do():
            r = EV.run(
                symbol=symbol,
                style=style,
                index_symbol="VNINDEX",
                capital=capital,
                risk_pct=risk_pct,
                years=years,
            )
            return EV._to_jsonable(r)

        return _safe_call("evaluate_stock", _do)

    # ── Nhóm 2: Dữ liệu thô ───────────────────────────────────────────────

    @mcp.tool(
        name="get_history",
        title="Lấy lịch sử giá OHLCV",
        description="Lấy dữ liệu OHLCV (open/high/low/close/volume) theo ngày cho một mã cổ phiếu hoặc chỉ số. Cổ phiếu VN dùng vnstock, chỉ số/mã nước ngoài dùng Yahoo Finance.",
    )
    def get_history(symbol: str, years: int = 3) -> dict:  # pyright: ignore[reportUnusedFunction]
        """Lấy lịch sử giá OHLCV.

        Args:
            symbol: Mã cổ phiếu hoặc chỉ số (FPT, ^VNINDEX, AAPL...).
            years: Số năm dữ liệu. Mặc định 3.

        Returns:
            Dict gồm `symbol`, `rows` (list OHLCV theo ngày, date ISO).
        """
        def _do():
            df = D.get_history(symbol, years=years)
            if df is None or df.empty:
                return {"symbol": symbol.upper(), "rows": [], "caveats": [f"Không lấy được dữ liệu cho {symbol}"]}
            return {"symbol": symbol.upper(), "rows": _df_to_records(df), "count": len(df)}

        return _safe_call("get_history", _do)

    @mcp.tool(
        name="get_fundamentals",
        title="Lấy dữ liệu cơ bản (fundamentals)",
        description="Lấy dữ liệu tài chính cơ bản của một cổ phiếu VN: ROE, ROA, biên lợi nhuận, nợ, EPS, P/E, P/B, ROIC, doanh thu, EPS YoY. Cổ phiếu quốc tế / chỉ số sẽ trả dict rỗng (vnstock không cover).",
    )
    def get_fundamentals(symbol: str) -> dict:  # pyright: ignore[reportUnusedFunction]
        """Lấy dữ liệu cơ bản.

        Args:
            symbol: Mã cổ phiếu VN (FPT, DIG...). Mã quốc tế sẽ trả `fundamentals: {}`.

        Returns:
            Dict raw từ `tools.data.get_fundamentals` — các field chính: roe,
            roa, net_margin, debt_to_equity, current_ratio, eps, eps_yoy_growth,
            revenue_yoy, pe, pb, ...
        """
        def _do():
            f = D.get_fundamentals(symbol)
            return {"symbol": symbol.upper(), "fundamentals": f or {}}

        return _safe_call("get_fundamentals", _do)

    @mcp.tool(
        name="get_index_trend",
        title="Xu hướng chỉ số thị trường",
        description="Lấy xu hướng hiện tại của một chỉ số thị trường (VNINDEX mặc định) cho CANSLIM 'M' (Market direction). Trả giá, MA50/MA200, và verdict (UPTREND/DOWNTREND/SIDEWAYS).",
    )
    def get_index_trend(index_symbol: str = "VNINDEX") -> dict:  # pyright: ignore[reportUnusedFunction]
        """Xu hướng chỉ số.

        Args:
            index_symbol: Mã chỉ số (VNINDEX, ^GSPC...). Mặc định VNINDEX.

        Returns:
            Dict trend — `price`, `ma50`, `ma200`, `verdict`.
        """
        def _do():
            return {"index": index_symbol, "trend": D.get_index_trend(index_symbol)}

        return _safe_call("get_index_trend", _do)

    @mcp.tool(
        name="analyze_technical",
        title="Phân tích kỹ thuật đầy đủ",
        description="Phân tích kỹ thuật tổng hợp cho một mã: xu hướng (MA stack), S/R, nến Nhật, RSI/MACD/Bollinger, Wyckoff/VSA, Fibonacci. Trả về bias (bull/bear/neutral), danh sách tín hiệu, và mức hỗ trợ/kháng cự.",
    )
    def analyze_technical(symbol: str, years: int = 3) -> dict:  # pyright: ignore[reportUnusedFunction]
        """Phân tích kỹ thuật đầy đủ.

        Args:
            symbol: Mã cổ phiếu hoặc chỉ số.
            years: Số năm dữ liệu. Mặc định 3.

        Returns:
            Dict `T.analyze(hist)` — `bias`, `signals[]`, `levels{}`, `indicators{}`, `summary`.
        """
        def _do():
            hist = D.get_history(symbol, years=years)
            if hist is None or hist.empty:
                return {"symbol": symbol.upper(), "bias": "unknown", "signals": [], "caveats": [f"Không có dữ liệu giá cho {symbol}"]}
            return {"symbol": symbol.upper(), **T.analyze(hist)}

        return _safe_call("analyze_technical", _do)

    # ── Nhóm 3: Chấm điểm ─────────────────────────────────────────────────

    @mcp.tool(
        name="score_value",
        title="Chấm điểm giá trị (Buffett)",
        description="Chấm điểm phong cách Buffett với 8 tiêu chí có trọng số: ROE, ROA, biên lợi nhuận, Debt/Equity, Current Ratio, PEG, EPS growth, biên an toàn (Graham). Trả về Scorecard (score 0–100, grade MẠNH/KHẢ QUAN/TRÁNH, danh sách checks chi tiết).",
    )
    def score_value(symbol: str) -> dict:  # pyright: ignore[reportUnusedFunction]
        """Chấm điểm giá trị (Buffett).

        Args:
            symbol: Mã cổ phiếu VN.

        Returns:
            `Scorecard.to_dict()` — `style`, `score`, `grade`, `checks[]`, `notes[]`.
        """
        def _do():
            f = D.get_fundamentals(symbol)
            if not f:
                return {"symbol": symbol.upper(), "score": None, "grade": "THIẾU DỮ LIỆU", "checks": [], "notes": [f"Không có fundamentals cho {symbol}"]}
            sc = VS.score_value(f)
            return {"symbol": symbol.upper(), **sc.to_dict()}

        return _safe_call("score_value", _do)

    @mcp.tool(
        name="score_canslim",
        title="Chấm điểm tăng trưởng (CANSLIM)",
        description="Chấm điểm phong cách CANSLIM (O'Neil) với 7 tiêu chí: C (EPS quý YoY), A (EPS năm YoY), N (gần đỉnh 52 tuần), S (supply/demand), L (leader - RS rank), I (institutional), M (market direction). Trả về Scorecard.",
    )
    def score_canslim(symbol: str, index_symbol: str = "VNINDEX", years: int = 3) -> dict:  # pyright: ignore[reportUnusedFunction]
        """Chấm điểm tăng trưởng (CANSLIM).

        Args:
            symbol: Mã cổ phiếu VN.
            index_symbol: Chỉ số so sánh (mặc định VNINDEX).
            years: Số năm dữ liệu (mặc định 3).

        Returns:
            `Scorecard.to_dict()`.
        """
        def _do():
            f = D.get_fundamentals(symbol)
            hist = D.get_history(symbol, years=years)
            if hist is None or hist.empty:
                return {"symbol": symbol.upper(), "score": None, "grade": "THIẾU DỮ LIỆU", "checks": [], "notes": [f"Không có dữ liệu giá cho {symbol}"]}
            bench, _ = EV._benchmark_history(index_symbol, years=min(years, 2))
            rs_rank = None
            if bench is not None and not bench.empty:
                try:
                    rs_rank = I.rs_rank(hist["close"], bench["close"])
                except Exception:  # noqa: BLE001
                    rs_rank = None
            idx_trend = D.get_index_trend(index_symbol)
            if not f:
                return {"symbol": symbol.upper(), "score": None, "grade": "THIẾU DỮ LIỆU", "checks": [], "notes": [f"Không có fundamentals cho {symbol}"]}
            sc = CS.score_canslim(f, hist, rs_rank, idx_trend)
            return {"symbol": symbol.upper(), "rs_rank": rs_rank, "index_trend": idx_trend, **sc.to_dict()}

        return _safe_call("score_canslim", _do)

    # ── Nhóm 4: Quản trị rủi ro ────────────────────────────────────────────

    @mcp.tool(
        name="position_size",
        title="Tính position sizing",
        description="Tính số cổ phiếu nên mua dựa trên vốn, rủi ro mỗi lệnh, entry, stop. Tự động tính target nếu không cung cấp (mặc định R:R = 2:1). Trả RiskPlan: shares, deployable, R:R ratio, verdict (ĐẠT/CẢNH BÁO).",
    )
    def position_size(  # pyright: ignore[reportUnusedFunction]
        capital: float,
        risk_pct: float,
        entry: float,
        stop: float,
        target: float | None = None,
    ) -> dict:
        """Tính position sizing.

        Args:
            capital: Vốn (VND).
            risk_pct: Rủi ro mỗi lệnh (% vốn, vd 1.5 = 1.5%).
            entry: Giá vào.
            stop: Giá cắt lỗ.
            target: Giá chốt lời (None = auto theo R:R=2:1).

        Returns:
            `RiskPlan.to_dict()` — `entry, stop, target, shares, deployable,
            deployable_pct, rr_ratio, verdict, warnings[]`.
        """
        def _do():
            plan = R.position_size(capital, risk_pct, entry, stop, target)
            return plan.to_dict()

        return _safe_call("position_size", _do)

    @mcp.tool(
        name="suggest_stop",
        title="Gợi ý giá cắt lỗ",
        description="Gợi ý giá stop-loss dựa trên ATR (Average True Range) hoặc phần trăm O'Neil (mặc định 7-8%). Method 'atr': entry - 2×ATR; method 'oneil': entry × (1 - pct).",
    )
    def suggest_stop(entry: float, atr_value: float | None = None, method: str = "atr", pct: float = 0.08) -> dict:  # pyright: ignore[reportUnusedFunction]
        """Gợi ý giá cắt lỗ.

        Args:
            entry: Giá vào.
            atr_value: ATR (None nếu dùng method 'oneil').
            method: 'atr' (mặc định) hoặc 'oneil'.
            pct: Phần trăm cắt lỗ cho method 'oneil' (mặc định 0.08 = 8%).

        Returns:
            Dict gồm `stop`, `method`, `pct_below_entry`, `atr_value`.
        """
        def _do():
            stop = R.suggest_stop(entry, atr_value, method=method, pct=pct)
            return {
                "entry": entry,
                "atr_value": atr_value,
                "method": method,
                "stop": stop,
                "pct_below_entry": round((entry - stop) / entry * 100, 2) if entry else None,
            }

        return _safe_call("suggest_stop", _do)

    @mcp.tool(
        name="suggest_target",
        title="Gợi ý giá chốt lời",
        description="Tính giá target dựa trên entry, stop và reward:risk ratio mong muốn (mặc định 2:1). Trả về target và R:R thực tế.",
    )
    def suggest_target(entry: float, stop: float, rr: float = 2.0) -> dict:  # pyright: ignore[reportUnusedFunction]
        """Gợi ý giá chốt lời.

        Args:
            entry: Giá vào.
            stop: Giá cắt lỗ.
            rr: Reward:Risk ratio mong muốn (mặc định 2.0).

        Returns:
            Dict gồm `target`, `rr_actual` (R:R tính ngược từ entry/stop/target).
        """
        def _do():
            target = R.suggest_target(entry, stop, rr=rr)
            risk = entry - stop
            reward = target - entry
            rr_actual = round(reward / risk, 2) if risk > 0 else None
            return {
                "entry": entry,
                "stop": stop,
                "target": target,
                "rr_requested": rr,
                "rr_actual": rr_actual,
            }

        return _safe_call("suggest_target", _do)

    # ── Nhóm 5: Báo cáo lưu trữ ───────────────────────────────────────────

    @mcp.tool(
        name="list_market_reports",
        title="Liệt kê reports đã sinh",
        description="Liệt kê tất cả file `.md` trong `market_reports/`. Trả về tên, kích thước, ngày sửa. Dùng trước khi đọc report qua `kb://reports/{filename}` hoặc gọi `get_market_report`.",
    )
    def list_market_reports() -> dict:  # pyright: ignore[reportUnusedFunction]
        """Liệt kê market reports."""
        def _do():
            if not MARKET_REPORTS_DIR.exists():
                return {"reports": [], "count": 0, "caveats": ["Thư mục market_reports/ chưa tồn tại"]}
            reports = []
            for p in sorted(MARKET_REPORTS_DIR.glob("*.md")):
                stat = p.stat()
                reports.append({
                    "name": p.name,
                    "size": stat.st_size,
                    "modified": stat.st_mtime,
                    "uri": f"kb://reports/{p.name}",
                })
            return {"reports": reports, "count": len(reports)}

        return _safe_call("list_market_reports", _do)

    @mcp.tool(
        name="get_market_report",
        title="Đọc 1 market report",
        description="Đọc nội dung 1 file `.md` trong `market_reports/`. Validate filename chống path traversal. Gọi `list_market_reports` trước để biết tên file hợp lệ.",
    )
    def get_market_report(filename: str) -> dict:  # pyright: ignore[reportUnusedFunction]
        r"""Đọc 1 market report.

        Args:
            filename: Tên file `.md` (vd '20.07.2026.md'). Validate regex
                chỉ chấp nhận `[A-Za-z0-9._-]+` kết thúc bằng `.md`.

        Returns:
            Dict gồm `name`, `content` (text markdown), `size`, `modified`.
        """
        def _do():
            _validate_filename(filename)
            target = MARKET_REPORTS_DIR / filename
            if not target.exists():
                raise FileNotFoundError(f"Report không tồn tại: {filename}")
            stat = target.stat()
            return {
                "name": filename,
                "content": target.read_text(encoding="utf-8", errors="replace"),
                "size": stat.st_size,
                "modified": stat.st_mtime,
            }

        return _safe_call("get_market_report", _do)

    # ── Nhóm 6: TimesFM 3.0 forecast + evaluation ──────────────────────

    @mcp.tool(
        name="timesfm_forecast",
        title="Forecast TimesFM 3.0",
        description=(
            "Dùng TimesFM 3.0 (google/timesfm-3.0-pytorch) dự báo giá N bước "
            "tới cho 1 symbol Yahoo Finance. Mặc định XAUUSD (GC=F) trên khung "
            "15m, horizon 12 (≈3 giờ). Trả current_price, forecast_prices, "
            "expected_returns_pct, signal BUY/HOLD/SELL. Yêu cầu torch + "
            "timesfm3 đã cài — nếu thiếu sẽ trả error JSON với hướng dẫn."
        ),
    )
    def timesfm_forecast(  # pyright: ignore[reportUnusedFunction]
        symbol: str = "GC=F",
        interval: str = "15m",
        period: str = "60d",
        context_length: int = 256,
        horizon: int = 12,
        buy_threshold: float = 0.002,
        sell_threshold: float = -0.002,
        device: str = "auto",
    ) -> dict:
        """Forecast N bước giá + tín hiệu BUY/HOLD/SELL.

        Args:
            symbol: Yahoo Finance symbol. Mặc định `GC=F` (XAUUSD).
            interval: 1m | 5m | 15m | 30m | 60m | 1h | 1d. Mặc định 15m.
            period: 7d | 30d | 60d | 1mo | 3mo | 6mo | 1y | 2y. Mặc định 60d.
            context_length: Số candles làm context cho TimesFM. Mặc định 256.
            horizon: Số candles forecast. Mặc định 12 (≈3 giờ ở 15m).
            buy_threshold: Ngưỡng expected_return → BUY. Mặc định +0.2%.
            sell_threshold: Ngưỡng expected_return → SELL. Mặc định -0.2%.
            device: 'auto' | 'cuda' | 'cpu'. Mặc định auto-detect GPU.

        Returns:
            `ForecastResult.to_dict()` — current_price, forecast_prices[12],
            expected_returns_pct[12], signal, device, elapsed_seconds, caveats.
        """
        def _do():
            err = _check_timesfm_available()
            if err is not None:
                return err

            from tools.timesfm import run_forecast

            dev: str | None = None if device == "auto" else device
            result = run_forecast(
                symbol=symbol,
                interval=interval,
                period=period,
                context_length=context_length,
                horizon=horizon,
                buy_threshold=buy_threshold,
                sell_threshold=sell_threshold,
                device=dev,
            )
            return result.to_dict()

        return _safe_call("timesfm_forecast", _do)

    @mcp.tool(
        name="timesfm_evaluate",
        title="Walk-forward evaluate TimesFM 3.0",
        description=(
            "Walk-forward evaluation TimesFM 3.0 trên lịch sử. Tính MAE, RMSE, "
            "MAPE, Direction Accuracy theo từng horizon [1, 3, 6, 12] so với "
            "baseline naive (= current price). Yêu cầu torch + timesfm3 đã cài."
        ),
    )
    def timesfm_evaluate(  # pyright: ignore[reportUnusedFunction]
        symbol: str = "GC=F",
        interval: str = "15m",
        period: str = "60d",
        context_length: int = 256,
        horizons: list[int] | None = None,
        step: int = 12,
        max_samples: int = 100,
        device: str = "auto",
    ) -> dict:
        """Walk-forward evaluation.

        Args:
            symbol: Yahoo Finance symbol. Mặc định `GC=F`.
            interval: Khung nến. Mặc định 15m.
            period: Khoảng thời gian download. Mặc định 60d.
            context_length: Số candles context. Mặc định 256.
            horizons: Danh sách horizon cần đánh giá. Mặc định [1, 3, 6, 12].
            step: Bước trượt (candles) giữa 2 window. Mặc định 12.
            max_samples: Giới hạn windows lấy từ cuối. Mặc định 100.
            device: 'auto' | 'cuda' | 'cpu'. Mặc định auto-detect.

        Returns:
            `EvaluationResult.to_dict()` — metrics[] theo từng horizon với
            TimesFM + naive direction accuracy + improvement.
        """
        def _do():
            err = _check_timesfm_available()
            if err is not None:
                return err

            from tools.timesfm import run_evaluate

            hs = horizons if horizons is not None else [1, 3, 6, 12]
            dev: str | None = None if device == "auto" else device
            result = run_evaluate(
                symbol=symbol,
                interval=interval,
                period=period,
                context_length=context_length,
                horizons=hs,
                step=step,
                max_samples=max_samples,
                device=dev,
            )
            return result.to_dict()

        return _safe_call("timesfm_evaluate", _do)


__all__ = ["register_tools"]
