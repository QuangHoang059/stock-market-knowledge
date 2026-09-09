"""MCP server entry point cho `stock-market-knowledge`.

Hai chế độ:
- `python -m mcp_server`              → stdio (Claude Desktop local, không auth)
- `python -m mcp_server --http`       → streamable-http trên 0.0.0.0:8001
                                         yêu cầu MCP_AUTH_TOKEN (bắt buộc)

Cấu hình qua env:
- MCP_TRANSPORT    = 'stdio' | 'http' (mặc định 'stdio')
- MCP_HOST         = hostname để bind (mặc định '127.0.0.1' cho dev)
- MCP_PORT         = port (mặc định 8001)
- MCP_AUTH_TOKEN   = bearer token bắt buộc khi MCP_TRANSPORT=http
- MCP_RESOURCE_URL = public URL của server (dùng cho AuthSettings.resource_server_url,
                     mặc định http://{host}:{port})
"""

from __future__ import annotations

import sys

# Force UTF-8 cho stdout/stderr khi chạy trên Windows console (cp1252) để in
# được emoji và tiếng Việt. Trên POSIX (VPS Linux) đã là UTF-8 mặc định.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-define]
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-define]

import argparse
import logging
import os
import sys

from mcp.server.auth.settings import AuthSettings
from mcp.server.fastmcp import FastMCP

# Pyright không tự resolve package local — suppress cho 3 import này.
from mcp_server.auth import StaticBearerTokenVerifier, get_expected_token  # pyright: ignore[reportMissingImports]
from mcp_server.resources import register_resources  # pyright: ignore[reportMissingImports]
from mcp_server.tools import register_tools  # pyright: ignore[reportMissingImports]

logger = logging.getLogger(__name__)


def build_mcp(host: str = "127.0.0.1", port: int = 8001) -> FastMCP:
    """Tạo FastMCP instance + đăng ký resources + tools + health route.

    Khi HTTP mode được dùng, attach `AuthSettings` + `StaticBearerTokenVerifier`
    để FastMCP tự enforce bearer token (wrap bằng BearerAuthBackend nội bộ,
    dùng đúng lifecycle → fix được lỗi "Task group is not initialized" khi
    wrap Starlette middleware thủ công).
    """
    expected_token = get_expected_token()
    resource_url = os.environ.get(
        "MCP_RESOURCE_URL", f"http://{host}:{port}"
    )

    auth_kwargs: dict = {}
    if expected_token:
        # AuthSettings bắt buộc issuer_url + resource_server_url.
        # Vì ta dùng static bearer (không OAuth) nên issuer_url trỏ về
        # chính server — chỉ là metadata, không ảnh hưởng verify.
        auth_kwargs = {
            "auth": AuthSettings(
                issuer_url=resource_url,
                resource_server_url=resource_url,
            ),
            "token_verifier": StaticBearerTokenVerifier(),
        }

    mcp = FastMCP(
        name="stock-market-knowledge",
        instructions=(
            "Knowledge base + tools cho đánh giá cổ phiếu Việt Nam. "
            "Đọc `kb://index` để liệt kê resource, sau đó đọc `kb://01-basics` "
            "và `kb://06-risk` làm nền tảng."
        ),
        host=host,
        port=port,
        **auth_kwargs,
    )

    register_resources(mcp)
    register_tools(mcp)

    # Custom route `/health` — FastMCP đảm bảo custom_route bypass auth
    # (xem `custom_route` docstring: "will not require authorization").
    # Dùng cho Docker healthcheck + uptime monitor.
    @mcp.custom_route("/health", methods=["GET"])
    async def _health_handler(_request) -> object:  # pyright: ignore[reportUnusedFunction, reportMissingTypeStubs]
        from starlette.responses import JSONResponse

        return JSONResponse(
            {
                "status": "ok",
                "service": "stock-market-knowledge-mcp",
                "version": "0.1.0",
            },
            headers={"Cache-Control": "no-store"},
        )

    # Alias /healthz cho tương thích Kubernetes-style probe.
    @mcp.custom_route("/healthz", methods=["GET"])
    async def _healthz_handler(_request) -> object:  # pyright: ignore[reportUnusedFunction, reportMissingTypeStubs]
        from starlette.responses import JSONResponse

        return JSONResponse({"status": "ok"})

    return mcp


def run_http(host: str, port: int) -> None:
    """Khởi động server ở HTTP mode (streamable-http transport)."""
    expected = get_expected_token()
    if not expected:
        # Refuse to start — better fail loud than expose knowledge unauthenticated.
        print(
            "ERROR: MCP_AUTH_TOKEN chưa được set. HTTP mode yêu cầu token "
            "để bảo vệ knowledge base.\n"
            "Generate: python -c \"import secrets; print(secrets.token_urlsafe(32))\"\n"
            "Sau đó set trong .env hoặc: export MCP_AUTH_TOKEN=<token>",
            file=sys.stderr,
        )
        sys.exit(1)

    mcp = build_mcp(host=host, port=port)

    print(
        f"🚀 MCP server (streamable-http) trên http://{host}:{port}\n"
        f"   Health: http://{host}:{port}/health (không cần auth)\n"
        f"   MCP endpoint: http://{host}:{port}/mcp (cần Bearer token)\n"
        f"   Auth: bearer token (đã cấu hình)",
        flush=True,
    )

    # `mcp.run(transport="streamable-http")` tự quản uvicorn + task group
    # lifecycle → tránh được lỗi "Task group is not initialized" khi wrap
    # Starlette middleware thủ công như trước.
    mcp.run(transport="streamable-http")


def run_stdio() -> None:
    """Khởi động server ở stdio mode (cho Claude Desktop local)."""
    mcp = build_mcp()
    # mcp.run() sẽ block until stdin closes
    mcp.run(transport="stdio")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m mcp_server",
        description="MCP server cho stock-market-knowledge.",
    )
    parser.add_argument(
        "--http",
        action="store_true",
        help="Chạy streamable-http transport (mặc định: stdio). "
             "Đọc host/port từ MCP_HOST/MCP_PORT env.",
    )
    parser.add_argument(
        "--host",
        default=os.environ.get("MCP_HOST", "127.0.0.1"),
        help="Bind host (mặc định 127.0.0.1; dùng 0.0.0.0 khi chạy trong Docker).",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=int(os.environ.get("MCP_PORT", "8001")),
        help="Bind port (mặc định 8001).",
    )
    parser.add_argument(
        "--log-level",
        default=os.environ.get("MCP_LOG_LEVEL", "INFO"),
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
    )

    args = parser.parse_args(argv)

    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    transport = "http" if args.http or os.environ.get("MCP_TRANSPORT") == "http" else "stdio"

    if transport == "http":
        run_http(host=args.host, port=args.port)
    else:
        run_stdio()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())