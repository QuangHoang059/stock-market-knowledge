"""Knowledge base resources cho MCP server.

Mỗi file markdown kiến thức (bài 01–06 trong `lessons/`) + file strategy (01–10) + skill file
(2 skills) được expose dưới dạng MCP resource với URI scheme `kb://`. Thêm
`kb://index` để liệt kê tất cả resource, và resource template
`kb://reports/{filename}` để đọc report đã sinh trong `market_reports/`.

Tổng cộng: 1 index + 6 knowledge + 10 strategy + 2 skill = 19 resource tĩnh
+ 1 template `kb://reports/{filename}`.
"""

from __future__ import annotations

import logging
import re
from pathlib import Path

# Repo root = parent của `mcp_server/` package.
REPO_ROOT: Path = Path(__file__).resolve().parent.parent

logger = logging.getLogger(__name__)

# Tên bài + slug tương ứng trên URI.
# Thứ tự slug (01-basics → 06-risk) khớp với thứ tự học trong README.
KNOWLEDGE_FILES: dict[str, tuple[str, str]] = {
    "01-basics": (
        "lessons/01_Nhan_Thuc_&_Khai_Niem_Co_Ban.md",
        "Nhận thức & khái niệm cơ bản — chỉ báo kỹ thuật, nến Nhật, xu hướng, lệnh giao dịch.",
    ),
    "02-buffett": (
        "lessons/02_Triet_Ly_Dau_Tu_Gia_Tri_Buffett.md",
        "Triết lý đầu tư giá trị (Buffett) — moat, ROE, nợ, biên an toàn, định giá.",
    ),
    "03-canslim": (
        "lessons/03_He_Thong_Tang_Truong_CANSLIM.md",
        "Hệ thống tăng trưởng CANSLIM (O'Neil) — 7 tiêu chí C/A/N/S/L/I/M, cúp tay cầm, FTD.",
    ),
    "04-wyckoff": (
        "lessons/04_Ly_Thuyet_Wyckoff_&_VSA.md",
        "Wyckoff & VSA — dấu chân dòng tiền, tích lũy/phân phối, Spring/UTAD.",
    ),
    "05-elliott": (
        "lessons/05_Nguyen_Ly_Song_Elliott.md",
        "Sóng Elliott & Fibonacci — cấu trúc 5-3, 3 quy tắc, mục tiêu Fib.",
    ),
    "06-risk": (
        "lessons/06_Quan_Tri_Rui_Ro_&_Ky_Luat.md",
        "Quản trị rủi ro & kỷ luật — R:R, position sizing, cắt lỗ 7–8%, chốt lời 20–25%.",
    ),
}

# 10 chiến lược Pine Script v6 — merge từ repo cũ `strategy-trade/`.
# Slug đánh số `strategy-NN-...` để agent nhận biết thứ tự.
STRATEGY_FILES: dict[str, tuple[str, str]] = {
    "strategy-01-ema-crossover": (
        "strategies/01-ema-20-50-crossover.md",
        "EMA 20/50 Crossover — trend following cổ điển. TF: 1H/4H. Entry khi EMA cross, SL swing, TP 2R.",
    ),
    "strategy-02-breakout-volume": (
        "strategies/02-breakout-plus-volume.md",
        "Breakout + Volume — phá level với volume xác nhận >1.5× trung bình 20. TF: 15m/1H. TP 2R.",
    ),
    "strategy-03-breakout-retest": (
        "strategies/03-breakout-retest.md",
        "Breakout + Retest — vào lệnh khi giá retest thành công vùng phá. TF: 15m/1H. TP 2R.",
    ),
    "strategy-04-ema-pullback": (
        "strategies/04-ema20-pullback.md",
        "EMA20 Pullback — pullback về EMA20 theo trend + đóng nến xác nhận. TF: 15m/1H. TP 2R.",
    ),
    "strategy-05-rsi-bollinger-mr": (
        "strategies/05-rsi-bollinger-mean-reversion.md",
        "RSI + Bollinger Mean Reversion — giá chạm band ngoài + RSI quá bán/quá mua. TF: 15m/1H. TP 1.5R.",
    ),
    "strategy-06-bb-squeeze": (
        "strategies/06-bollinger-squeeze-breakout.md",
        "Bollinger Squeeze Breakout — bắt biến động bùng nổ sau nén band. TF: 15m/1H. TP 2R.",
    ),
    "strategy-07-vwap-pullback": (
        "strategies/07-vwap-pullback.md",
        "VWAP Pullback — intraday pullback về VWAP + volume xác nhận. TF: 5m/15m. TP 1.5R.",
    ),
    "strategy-08-macd-ema200": (
        "strategies/08-macd-ema200-trend-filter.md",
        "MACD + EMA200 — momentum cross theo trend filter EMA200. TF: 1H/4H. TP 2R.",
    ),
    "strategy-09-orb": (
        "strategies/09-opening-range-breakout.md",
        "Opening Range Breakout — phá opening range 5/15/30 phút đầu phiên. TF: 5m/15m. TP 2R.",
    ),
    "strategy-10-donchian-bo": (
        "strategies/10-donchian-channel-breakout.md",
        "Donchian Channel Breakout — 20-bar breakout, SL 2×ATR(14), TP 3×ATR(14). TF: 1H/4H/D.",
    ),
}

# Skill files cho agent Claude.
SKILL_FILES: dict[str, tuple[str, str]] = {
    "skill-danh-gia-co-phieu": (
        ".claude/skills/danh-gia-co-phieu/SKILL.md",
        "Skill 6-section cho agent đánh giá cổ phiếu (Buffett/CANSLIM/Wyckoff/Elliott + rủi ro).",
    ),
    "skill-chien-luoc-giao-dich": (
        ".claude/skills/chien-luoc-giao-dich/SKILL.md",
        "Skill chọn + backtest 10 chiến lược trading + tích hợp TimesFM 3.0 forecast.",
    ),
}

MARKET_REPORTS_DIR: Path = REPO_ROOT / "market_reports"

# Whitelist regex cho filename report — chống path traversal.
SAFE_FILENAME_RE = re.compile(r"^[A-Za-z0-9._-]+\.md$")

# MIME type cho tất cả resource trong knowledge base.
MIME = "text/markdown; charset=utf-8"


def register_resources(mcp) -> None:
    """Đăng ký tất cả resource lên FastMCP instance.

    Hàm này phải được gọi 1 lần khi server khởi động. Tất cả decorator
    `@mcp.resource(...)` chạy trong hàm này nên việc đăng ký xảy ra ngay.
    """

    @mcp.resource(
        "kb://index",
        name="kb_index",
        title="Knowledge base index",
        description="Danh sách tất cả knowledge resource + URI có sẵn trong server này.",
        mime_type=MIME,
    )
    def kb_index() -> str:  # pyright: ignore[reportUnusedFunction]
        lines = ["# 📚 Knowledge base — `stock-market-knowledge`\n"]
        lines.append(
            "Server này expose **19 resource tĩnh** (6 bài học + 10 chiến lược + 2 skill + index) "
            "+ 1 resource template cho reports.\n"
        )
        lines.append("## Bài học nền tảng (bài 01–06)\n")
        for slug, (filename, desc) in KNOWLEDGE_FILES.items():
            lines.append(f"- **`kb://{slug}`** → `{filename}` — {desc}")
        lines.append("")
        lines.append("## 10 Chiến lược Pine Script (Pine v6)\n")
        for slug, (filename, desc) in STRATEGY_FILES.items():
            lines.append(f"- **`kb://{slug}`** → `{filename}` — {desc}")
        lines.append("")
        lines.append("## Skill Claude (hướng dẫn cho agent)\n")
        for slug, (filename, desc) in SKILL_FILES.items():
            lines.append(f"- **`kb://{slug}`** → `{filename}` — {desc}")
        lines.append("")
        lines.append("## Meta\n")
        lines.append("- **`kb://index`** → File này.")
        lines.append("")
        lines.append("## Reports đã sinh (`market_reports/`)\n")
        lines.append("Dùng tool `list_market_reports` để liệt kê, sau đó đọc qua URI template:")
        lines.append(
            "- **`kb://reports/{filename}`** → file `.md` trong `market_reports/` "
            "(vd `kb://reports/20.07.2026.md`)."
        )
        lines.append("")
        lines.append("## Gợi ý workflow cho agent\n")
        lines.append("1. Đọc `kb://skill-danh-gia-co-phieu` để hiểu format đầu ra 6-section cho cổ phiếu.")
        lines.append("2. Đọc `kb://skill-chien-luoc-giao-dich` để hiểu workflow cho chiến lược + TimesFM.")
        lines.append("3. Đọc `kb://01-basics` và `kb://06-risk` (nền tảng + rủi ro).")
        lines.append("4. Tuỳ phong cách user: `kb://02-buffett` (giá trị) **hoặc** `kb://03-canslim` (tăng trưởng).")
        lines.append("5. Điểm vào/ra: `kb://04-wyckoff` + `kb://05-elliott`.")
        lines.append("6. Chọn chiến lược: `kb://strategy-NN-...`.")
        lines.append(
            "7. Khi cần số liệu thực → gọi tool `evaluate_stock`, `score_value`, `position_size`, "
            "hoặc `timesfm_forecast`."
        )
        return "\n".join(lines)

    # Đăng ký từng bài 01–06.
    for slug, (filename, desc) in KNOWLEDGE_FILES.items():
        path = REPO_ROOT / filename
        if not path.exists():
            logger.warning(
                "Knowledge file không tồn tại: %s — resource kb://%s sẽ fail khi đọc",
                path,
                slug,
            )
        _register_static_kb(mcp, slug=slug, path=path, desc=desc)

    # 10 file strategy — same pattern.
    for slug, (filename, desc) in STRATEGY_FILES.items():
        path = REPO_ROOT / filename
        if not path.exists():
            logger.warning(
                "Strategy file không tồn tại: %s — resource kb://%s sẽ fail khi đọc",
                path,
                slug,
            )
        _register_static_kb(mcp, slug=slug, path=path, desc=desc)

    # Skill files (loop thay vì hard-code).
    for slug, (filename, desc) in SKILL_FILES.items():
        path = REPO_ROOT / filename
        if not path.exists():
            logger.warning(
                "Skill file không tồn tại: %s — resource kb://%s sẽ fail khi đọc",
                path,
                slug,
            )
        _register_static_kb(mcp, slug=slug, path=path, desc=desc)

    # Resource template cho reports.
    _register_reports_template(mcp)


def _register_static_kb(mcp, *, slug: str, path: Path, desc: str) -> None:
    """Đăng ký 1 resource tĩnh (file markdown cố định)."""

    @mcp.resource(
        f"kb://{slug}",
        name=f"kb_{slug.replace('-', '_')}",
        title=f"kb://{slug}",
        description=desc,
        mime_type=MIME,
    )
    def _handler() -> str:  # pyright: ignore[reportUnusedFunction]
        if not path.exists():
            raise FileNotFoundError(f"Knowledge file không tồn tại: {path}")
        # Đọc UTF-8, thay lỗi encoding thay vì crash (markdown thường có emoji).
        return path.read_text(encoding="utf-8", errors="replace")


def _register_reports_template(mcp) -> None:
    """Đăng ký resource template `kb://reports/{filename}`.

    Handler validate `filename` qua whitelist regex để chặn path traversal
    (vd `../../etc/passwd`). Nếu filename không khớp pattern → trả 404 với
    message rõ ràng thay vì raise exception.
    """

    @mcp.resource(
        "kb://reports/{filename}",
        name="kb_reports_template",
        title="Market reports (template)",
        description=(
            "Đọc 1 file `.md` trong `market_reports/`. Dùng tool `list_market_reports` "
            "để biết tên file hợp lệ. URI: `kb://reports/{filename}`."
        ),
        mime_type=MIME,
    )
    def _reports_handler(filename: str) -> str:  # pyright: ignore[reportUnusedFunction]
        if not SAFE_FILENAME_RE.match(filename):
            raise ValueError(
                f"Filename không hợp lệ: '{filename}'. "
                f"Chỉ chấp nhận [A-Za-z0-9._-]+ với đuôi .md."
            )
        target = (MARKET_REPORTS_DIR / filename).resolve()
        # Defense in depth: đảm bảo file nằm trong MARKET_REPORTS_DIR (chống
        # symlink attack dù regex đã chặn `..`).
        if (
            MARKET_REPORTS_DIR.resolve() not in target.parents
            and target != MARKET_REPORTS_DIR
        ):
            raise ValueError(
                f"Filename vượt ngoài thư mục market_reports/: '{filename}'."
            )
        if not target.exists():
            raise FileNotFoundError(
                f"Report không tồn tại: {filename}. Gọi `list_market_reports` để xem danh sách."
            )
        return target.read_text(encoding="utf-8", errors="replace")


__all__ = ["register_resources"]
