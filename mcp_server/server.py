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
"""

from __future__ import annotations

import sys

# Force UTF-8 cho stdout/stderr khi chạy trên Windows console (cp1252) để in
# được emoji và tiếng Việt. Trên POSIX (VPS Linux) đã là UTF-8 mặc định.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]

import argparse
import logging
import os
import sys

from mcp.server.fastmcp import FastMCP

# Pyright không tự resolve package local — suppress cho 3 import này.
from mcp_server.auth import BearerAuthMiddleware, get_expected_token  # pyright: ignore[reportMissingImports]
from mcp_server.resources import register_resources  # pyright: ignore[reportMissingImports]
from mcp_server.tools import register_tools  # pyright: ignore[reportMissingImports]

logger = logging.getLogger(__name__)


def build_mcp(host: str = "127.0.0.1", port: int = 8001) -> FastMCP:
    """Tạo FastMCP instance + đăng ký resources + tools."""
    mcp = FastMCP(
        name="stock-market-knowledge",
        instructions=(
            "Knowledge base + tools cho đánh giá cổ phiếu Việt Nam. "
            "Đọc `kb://skill` trước để hiểu format trả lời 6-section. "
            "Liệt kê resource qua `kb://index`."
        ),
        host=host,
        port=port,
        # streamable_http_path='/mcp' là default — khớp với nginx snippet
        # (proxy_pass http://127.0.0.1:8001/mcp/ nếu dùng path prefix).
    )
    register_resources(mcp)
    register_tools(mcp)
    return mcp


async def _health_handler(request):  # pyright: ignore[reportUnusedParameter, reportMissingTypeStubs]
    """Handler cho GET /health — trả JSON status, bypass auth."""
    # `request` chỉ dùng để Starlette route matching — không cần đọc body.
    _ = request
    from starlette.responses import JSONResponse

    return JSONResponse(
        {
            "status": "ok",
            "service": "stock-market-knowledge-mcp",
            "version": "0.1.0",
        },
        headers={"Cache-Control": "no-store"},
    )


def build_http_app(mcp: FastMCP):
    """Build Starlette app cho HTTP mode: MCP endpoints + /health + auth.

    Luồng:
      request → BearerAuthMiddleware → (health? skip) → FastMCP streamable-http app
    """
    from starlette.applications import Starlette
    from starlette.routing import Mount, Route

    mcp_app = mcp.streamable_http_app()

    app = Starlette(
        routes=[
            Route("/health", _health_handler, methods=["GET"]),
            Route("/healthz", _health_handler, methods=["GET"]),
            Mount("/", app=mcp_app),
        ],
    )

    # Auth middleware wrap ngoài cùng. `/health` & `/healthz` được bypass
    # bên trong BearerAuthMiddleware.
    expected = get_expected_token()
    if not expected:
        logger.warning(
            "MCP_AUTH_TOKEN chưa set — server sẽ từ chối mọi request "
            "MCP (chỉ /health hoạt động). Set token trong .env hoặc "
            "env var trước khi deploy."
        )
    app.add_middleware(BearerAuthMiddleware, expected_token=expected)

    return app


def run_http(host: str, port: int) -> None:
    """Khởi động server ở HTTP mode (streamable-http transport)."""
    import uvicorn

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
    app = build_http_app(mcp)

    print(
        f"🚀 MCP server (streamable-http) trên http://{host}:{port}\n"
        f"   Health: http://{host}:{port}/health\n"
        f"   MCP endpoint: http://{host}:{port}/mcp\n"
        f"   Auth: Bearer token (đã cấu hình)",
        flush=True,
    )

    uvicorn.run(
        app,
        host=host,
        port=port,
        log_level=os.environ.get("MCP_LOG_LEVEL", "info"),
        # Streamable-HTTP cần HTTP/1.1 với keep-alive
        http="h11",
        access_log=True,
    )


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
