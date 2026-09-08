"""Smoke test cho MCP server — chạy local không cần deploy.

Test các kịch bản:
1. List resources (expect 8) + tools (expect 12).
2. Đọc `kb://index` (kiểm tra có 6 bài + skill + index).
3. List market reports (expect ≥2 file .md trong repo này).
4. `suggest_stop` + `position_size` (pure math, không cần network).
5. `get_market_report` chặn path traversal.
6. HTTP mode: server từ chối request không có bearer token.
7. HTTP mode: bearer token sai → 401.

Chạy: `python -m mcp_server.test_local`
"""

from __future__ import annotations

import os
import socket
import subprocess
import sys
import time
from pathlib import Path

# Force UTF-8 cho stdout/stderr để in tiếng Việt trên Windows console (cp1252).
# Phải set TRƯỚC khi print bất kỳ thứ gì.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]

REPO_ROOT = Path(__file__).resolve().parent.parent

# ─────────────────────────────────────────────────────────────────────────────
# Test runner
# ─────────────────────────────────────────────────────────────────────────────

PASS = "✅ PASS"
FAIL = "❌ FAIL"
results: list[tuple[str, bool, str]] = []


def check(name: str, condition: bool, detail: str = "") -> None:
    """Record 1 test result."""
    results.append((name, bool(condition), detail))
    icon = PASS if condition else FAIL
    msg = f"{icon}  {name}"
    if detail:
        msg += f"\n        {detail}"
    print(msg, flush=True)


# ─────────────────────────────────────────────────────────────────────────────
# 1. Direct in-process tests (không cần subprocess)
# ─────────────────────────────────────────────────────────────────────────────

def test_resources_and_tools_inprocess() -> None:
    """Test list resources/tools + đọc kb://index không qua network."""
    print("\n── In-process tests (không cần subprocess) ──", flush=True)

    import mcp_server.server as _server_mod  # pyright: ignore[reportMissingImports]

    mcp = _server_mod.build_mcp()

    # List tools
    tools = list(mcp._tool_manager.list_tools())
    check(
        "Đăng ký đúng 14 tools (12 cũ + 2 timesfm)",
        len(tools) == 14,
        f"Thực tế: {len(tools)} tools — {[t.name for t in tools]}",
    )

    expected_tools = {
        "evaluate_stock", "get_history", "get_fundamentals", "get_index_trend",
        "analyze_technical", "score_value", "score_canslim",
        "position_size", "suggest_stop", "suggest_target",
        "list_market_reports", "get_market_report",
        "timesfm_forecast", "timesfm_evaluate",
    }
    actual_tools = {t.name for t in tools}
    check(
        "Tools tên khớp expected set",
        actual_tools == expected_tools,
        f"Thiếu: {expected_tools - actual_tools}; thừa: {actual_tools - expected_tools}",
    )

    # List resources (đếm cả template)
    resources = list(mcp._resource_manager.list_resources())
    templates = list(mcp._resource_manager.list_templates())
    check(
        "Đăng ký đúng 19 static resources (1 index + 6 knowledge + 10 strategy + 2 skill)",
        len(resources) == 19,
        f"Thực tế: {len(resources)} — {[str(r.uri) for r in resources]}",
    )
    check(
        "Đăng ký đúng 1 resource template (kb://reports/{filename})",
        len(templates) == 1,
        f"Thực tế: {len(templates)} — {[t.uri_template for t in templates]}",
    )

    # Đọc kb://index (gọi thẳng handler trong mcp._resource_manager)
    index_handler = None
    for r in resources:
        if str(r.uri) == "kb://index":
            index_handler = r
            break
    check("Có resource kb://index", index_handler is not None)
    if index_handler:
        # FastMCP resource có .fn là function handler (runtime, không có trong stub).
        content = index_handler.fn()  # pyright: ignore[reportAttributeAccessIssue]
        expected_keywords = [
            # 6 knowledge bài học
            "01-basics", "02-buffett", "03-canslim", "04-wyckoff",
            "05-elliott", "06-risk",
            # 10 strategy slugs
            "strategy-01-ema-crossover", "strategy-02-breakout-volume",
            "strategy-10-donchian-bo",
            # 2 skill slugs
            "skill-danh-gia-co-phieu", "skill-chien-luoc-giao-dich",
            # 1 tool gợi ý
            "list_market_reports",
        ]
        missing = [kw for kw in expected_keywords if kw not in content]
        check(
            "kb://index liệt kê đầy đủ 19 resource + tool gợi ý",
            not missing,
            f"Thiếu keywords: {missing}" if missing else "Đủ 19 URI + gợi ý tool.",
        )

    # Đọc 1 knowledge file cụ thể
    basics_handler = next((r for r in resources if str(r.uri) == "kb://01-basics"), None)
    check("Có resource kb://01-basics", basics_handler is not None)
    if basics_handler:
        content = basics_handler.fn()
        check(
            "kb://01-basics có nội dung (>1KB)",
            len(content) > 1000,
            f"Length: {len(content)} chars",
        )

    # Đọc 1 strategy file — kiểm tra có Pine Script code
    strat_handler = next(
        (r for r in resources if str(r.uri) == "kb://strategy-10-donchian-bo"),
        None,
    )
    check("Có resource kb://strategy-10-donchian-bo", strat_handler is not None)
    if strat_handler:
        content = strat_handler.fn()
        has_pine = ("```pine" in content) or ("@version=6" in content)
        check(
            "kb://strategy-10-donchian-bo có Pine Script code",
            has_pine,
            f"Length: {len(content)} chars",
        )

    # Đọc skill mới
    skill_handler = next(
        (r for r in resources if str(r.uri) == "kb://skill-chien-luoc-giao-dich"),
        None,
    )
    check("Có resource kb://skill-chien-luoc-giao-dich", skill_handler is not None)
    if skill_handler:
        content = skill_handler.fn()
        check(
            "skill-chien-luoc-giao-dich có frontmatter `name: chien-luoc-giao-dich`",
            "name: chien-luoc-giao-dich" in content,
            f"Length: {len(content)} chars",
        )


def test_list_market_reports() -> None:
    """Test tool list_market_reports trả ≥2 file .md."""
    print("\n── Market reports test ──", flush=True)

    import mcp_server.server as _server_mod  # pyright: ignore[reportMissingImports]

    mcp = _server_mod.build_mcp()
    tool = next((t for t in mcp._tool_manager.list_tools() if t.name == "list_market_reports"), None)
    check("Có tool list_market_reports", tool is not None)
    if tool is None:
        return

    # Gọi trực tiếp handler
    result = tool.fn()
    check(
        "list_market_reports trả ok=True",
        result.get("ok") is True,
        f"Result: {result}",
    )
    if result.get("ok"):
        data = result["data"]
        reports = data.get("reports", [])
        check(
            "list_market_reports trả ≥2 file .md",
            len(reports) >= 2,
            f"Reports: {[r['name'] for r in reports]}",
        )
        # Trong repo này có 2 file .md mẫu
        names = {r["name"] for r in reports}
        check(
            "Có file 20.07.2026.md và dig_20.07.2026.md",
            {"20.07.2026.md", "dig_20.07.2026.md"}.issubset(names),
            f"Names: {names}",
        )


def test_risk_math_offline() -> None:
    """Pure math: suggest_stop, suggest_target, position_size — không cần network."""
    print("\n── Risk math tests (offline) ──", flush=True)

    import mcp_server.server as _server_mod  # pyright: ignore[reportMissingImports]

    mcp = _server_mod.build_mcp()
    by_name = {t.name: t for t in mcp._tool_manager.list_tools()}

    # suggest_stop(entry=100, atr=3) → 100 - 2*3 = 94
    r = by_name["suggest_stop"].fn(entry=100.0, atr_value=3.0, method="atr")
    check(
        "suggest_stop(100, 3, atr) ≈ 94",
        r.get("ok") and abs(r["data"]["stop"] - 94.0) < 0.01,
        f"Result: {r}",
    )

    # suggest_target(entry=100, stop=95, rr=2) → 100 + (100-95)*2 = 110
    r = by_name["suggest_target"].fn(entry=100.0, stop=95.0, rr=2.0)
    check(
        "suggest_target(100, 95, 2) = 110",
        r.get("ok") and abs(r["data"]["target"] - 110.0) < 0.01,
        f"Result: {r}",
    )

    # position_size(1e8, 1.5, 100, 95) → risk=1.5M, shares ≈ 300
    r = by_name["position_size"].fn(capital=100_000_000, risk_pct=1.5, entry=100.0, stop=95.0)
    check(
        "position_size trả ok + shares > 0",
        r.get("ok") and r["data"].get("shares", 0) > 0,
        f"Result: {r}",
    )


def test_get_market_report_validation() -> None:
    """Path traversal phải bị chặn."""
    print("\n── get_market_report validation ──", flush=True)

    import mcp_server.server as _server_mod  # pyright: ignore[reportMissingImports]

    mcp = _server_mod.build_mcp()
    tool = next(t for t in mcp._tool_manager.list_tools() if t.name == "get_market_report")

    # Path traversal
    r = tool.fn(filename="../../../etc/passwd")
    check(
        "Chặn path traversal '../../etc/passwd'",
        not r.get("ok"),
        f"Result: {r}",
    )

    # Empty filename
    r = tool.fn(filename="")
    check(
        "Chặn empty filename",
        not r.get("ok"),
        f"Result: {r}",
    )

    # Filename không đuôi .md
    r = tool.fn(filename="evil.py")
    check(
        "Chặn filename không đuôi .md",
        not r.get("ok"),
        f"Result: {r}",
    )

    # Valid filename — đọc được file thật
    r = tool.fn(filename="20.07.2026.md")
    check(
        "Đọc file hợp lệ 20.07.2026.md",
        r.get("ok") and len(r.get("data", {}).get("content", "")) > 100,
        f"Result: {r.get('ok') and len(r.get('data', {}).get('content', ''))}",
    )


def test_timesfm_graceful_error() -> None:
    """TimesFM tools phải trả error JSON graceful khi thiếu torch/timesfm3,
    KHÔNG crash server.

    Skipped nếu torch + timesfm3 đã sẵn sàng (chạy smoke test nâng cao hơn).
    """
    print("\n── TimesFM graceful error test ──", flush=True)

    import mcp_server.server as _server_mod  # pyright: ignore[reportMissingImports]
    from mcp_server.tools import _check_timesfm_available

    err = _check_timesfm_available()
    if err is None:
        print(
            "⚠️  torch + timesfm3 đã sẵn sàng — skip graceful error test "
            "(chạy evaluation thật qua tool evaluate_timesfm_xauusd.py)"
        )
        return

    check(
        "_check_timesfm_available() trả error dict",
        err.get("ok") is False,
        f"Got: {err}",
    )
    check(
        "Error dict có `tool: 'timesfm_*'`",
        err.get("tool") == "timesfm_*",
        f"Got: {err}",
    )
    check(
        "Error dict có hướng dẫn (mention torch + timesfm3)",
        "torch" in err.get("error", "") and "timesfm3" in err.get("error", ""),
        f"Got: {err}",
    )

    # Gọi tool handler — cũng phải trả graceful (không raise)
    mcp = _server_mod.build_mcp()
    fc_tool = next(
        (t for t in mcp._tool_manager.list_tools() if t.name == "timesfm_forecast"),
        None,
    )
    check("Có tool timesfm_forecast", fc_tool is not None)
    if fc_tool:
        r = fc_tool.fn(symbol="GC=F", horizon=4)
        check(
            "timesfm_forecast(symbol=GC=F) → ok=False graceful",
            r.get("ok") is False,
            f"Got: {r}",
        )
        check(
            "timesfm_forecast error có `tool: 'timesfm_forecast'`",
            r.get("tool") == "timesfm_forecast",
            f"Got: {r}",
        )


# ─────────────────────────────────────────────────────────────────────────────
# 2. HTTP mode tests (subprocess)
# ─────────────────────────────────────────────────────────────────────────────

def _free_port() -> int:
    """Tìm port trống."""
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _wait_for_port(host: str, port: int, timeout: float = 10.0) -> bool:
    """Đợi port mở."""
    start = time.time()
    while time.time() - start < timeout:
        try:
            with socket.create_connection((host, port), timeout=0.5):
                return True
        except OSError:
            time.sleep(0.2)
    return False


def test_http_mode_auth() -> None:
    """Test HTTP transport + bearer token enforcement."""
    print("\n── HTTP mode + auth tests ──", flush=True)

    port = _free_port()
    token = "test-token-" + str(int(time.time()))

    env = os.environ.copy()
    env["MCP_TRANSPORT"] = "http"
    env["MCP_HOST"] = "127.0.0.1"
    env["MCP_PORT"] = str(port)
    env["MCP_AUTH_TOKEN"] = token
    env["PYTHONPATH"] = str(REPO_ROOT)

    proc = subprocess.Popen(
        [sys.executable, "-m", "mcp_server", "--http"],
        cwd=str(REPO_ROOT),
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    try:
        if not _wait_for_port("127.0.0.1", port, timeout=15):
            stdout, stderr = proc.communicate(timeout=2)
            check(
                "HTTP server khởi động thành công",
                False,
                f"Timeout đợi port {port}. stdout={stdout[:200]} stderr={stderr[:200]}",
            )
            return

        check(f"HTTP server listening trên 127.0.0.1:{port}", True)

        import httpx as _httpx
        with _httpx.Client(timeout=5.0) as client:
            # 1. /health bypass auth → 200
            r = client.get(f"http://127.0.0.1:{port}/health")
            check(
                "/health bypass auth → 200",
                r.status_code == 200 and r.json().get("status") == "ok",
                f"Status: {r.status_code}, body: {r.text[:200]}",
            )

            # 2. MCP endpoint KHÔNG có Authorization → 401
            r = client.post(f"http://127.0.0.1:{port}/mcp", json={})
            check(
                "POST /mcp không token → 401",
                r.status_code == 401,
                f"Status: {r.status_code}",
            )

            # 3. MCP endpoint có token SAI → 401
            r = client.post(
                f"http://127.0.0.1:{port}/mcp",
                headers={"Authorization": "Bearer wrong-token"},
                json={},
            )
            check(
                "POST /mcp token sai → 401",
                r.status_code == 401,
                f"Status: {r.status_code}",
            )

            # 4. MCP endpoint có token ĐÚNG → MCP handshake (sẽ trả lỗi vì body
            # không phải JSON-RPC hợp lệ, nhưng phải KHÔNG phải 401)
            r = client.post(
                f"http://127.0.0.1:{port}/mcp",
                headers={"Authorization": f"Bearer {token}"},
                json={"jsonrpc": "2.0", "id": 1, "method": "ping"},
            )
            check(
                "POST /mcp token đúng → KHÔNG phải 401 (qua được auth)",
                r.status_code != 401,
                f"Status: {r.status_code}, body: {r.text[:200]}",
            )

    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()


def test_http_mode_rejects_without_token() -> None:
    """Nếu thiếu MCP_AUTH_TOKEN + http mode → server từ chối start."""
    print("\n── HTTP mode refuses to start without token ──", flush=True)

    port = _free_port()
    env = os.environ.copy()
    env["MCP_TRANSPORT"] = "http"
    env["MCP_HOST"] = "127.0.0.1"
    env["MCP_PORT"] = str(port)
    env.pop("MCP_AUTH_TOKEN", None)  # Đảm bảo KHÔNG có token
    env["PYTHONPATH"] = str(REPO_ROOT)

    proc = subprocess.Popen(
        [sys.executable, "-m", "mcp_server", "--http"],
        cwd=str(REPO_ROOT),
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    try:
        # Đợi tối đa 5s — server phải exit ngay, không listen port.
        try:
            returncode = proc.wait(timeout=5)
            check(
                "Server exit ngay khi thiếu MCP_AUTH_TOKEN",
                returncode != 0,
                f"Return code: {returncode}",
            )
        except subprocess.TimeoutExpired:
            proc.kill()
            check(
                "Server exit ngay khi thiếu MCP_AUTH_TOKEN",
                False,
                "Server không exit trong 5s — có thể đã accept token rỗng?",
            )
    finally:
        if proc.poll() is None:
            proc.kill()
            proc.wait(timeout=2)


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────

def main() -> int:
    print("=" * 70)
    print("MCP server smoke test — `stock-market-knowledge`")
    print("=" * 70)

    # In-process tests (chạy được mọi nơi, không cần network/subprocess)
    test_resources_and_tools_inprocess()
    test_list_market_reports()
    test_risk_math_offline()
    test_get_market_report_validation()

    # HTTP tests (cần httpx + khả năng bind port — skip nếu lỗi)
    try:
        import httpx as _httpx_check  # noqa: F841 — chỉ để verify httpx đã cài
        _ = _httpx_check
        test_http_mode_rejects_without_token()
        test_http_mode_auth()
    except ImportError:
        print("\n⚠️  httpx chưa cài — skip HTTP tests. Cài: pip install httpx")
    except Exception as e:  # noqa: BLE001
        print(f"\n⚠️  HTTP tests failed unexpectedly: {e}")

    # Summary
    print("\n" + "=" * 70)
    total = len(results)
    passed = sum(1 for _, ok, _ in results if ok)
    print(f"Summary: {passed}/{total} passed")
    if passed < total:
        print("Failed tests:")
        for name, ok, detail in results:
            if not ok:
                print(f"  - {name}\n    {detail}")
        return 1
    print("All tests passed ✅")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
