"""Bearer token authentication cho HTTP transport.

Khi chạy HTTP, server bắt buộc phải có `MCP_AUTH_TOKEN` (không cho phép
chạy unauthenticated trên internet). Middleware này check token trên mọi
request trừ `/health` và `/healthz` (cho Docker healthcheck / uptime monitor).

Token comparison dùng `hmac.compare_digest` để chống timing attack.
"""

from __future__ import annotations

import hmac
import json
import logging
import os
from typing import Any

logger = logging.getLogger(__name__)

# Path bypass auth — health checks chỉ cần TCP probe là đủ.
HEALTH_PATHS: frozenset[str] = frozenset({"/health", "/healthz"})


def get_expected_token() -> str | None:
    """Đọc MCP_AUTH_TOKEN từ env. Trả None nếu chưa set."""
    return os.environ.get("MCP_AUTH_TOKEN") or None


def verify_bearer_token(token: str) -> bool:
    """Constant-time comparison với MCP_AUTH_TOKEN.

    Trả False nếu token rỗng, None, hoặc không khớp.
    """
    expected = get_expected_token()
    if not expected or not token:
        return False
    return hmac.compare_digest(token, expected)


def extract_bearer(authorization_header: str | None) -> str | None:
    """Parse `Authorization: Bearer <token>` → token.

    Trả None nếu header rỗng, không có scheme `Bearer`, hoặc token rỗng.
    """
    if not authorization_header:
        return None
    parts = authorization_header.strip().split(None, 1)
    if len(parts) != 2 or parts[0].lower() != "bearer":
        return None
    token = parts[1].strip()
    return token or None


class BearerAuthMiddleware:
    """ASGI middleware: chặn mọi request không có bearer token hợp lệ.

    Bypass cho HEALTH_PATHS (chỉ cần TCP probe cho Docker healthcheck).

    Trả 401 JSON nếu thiếu / sai token. Đây là defense in depth — bên ngoài
    còn có nginx reverse proxy với TLS, có thể thêm IP allowlist nếu cần.
    """

    def __init__(self, app: Any, expected_token: str | None = None) -> None:
        self.app = app
        # Nếu không truyền explicit, đọc từ env mỗi request (cho phép reload
        # token mà không restart server trong trường hợp dev).
        self._expected_override = expected_token

    def _expected(self) -> str | None:
        return self._expected_override if self._expected_override is not None else get_expected_token()

    async def __call__(self, scope: dict, receive: Any, send: Any) -> None:
        if scope["type"] != "http":
            # WebSocket, lifespan, etc. → pass through
            await self.app(scope, receive, send)
            return

        path = scope.get("path", "")
        if path in HEALTH_PATHS:
            await self.app(scope, receive, send)
            return

        expected = self._expected()
        if not expected:
            # Server được start mà thiếu token là lỗi cấu hình. Từ chối mọi
            # request để tránh lộ knowledge base không auth.
            logger.error("MCP_AUTH_TOKEN chưa set nhưng HTTP transport đang chạy. Từ chối request.")
            await self._reject(send, status=503, error="server_misconfigured", message="MCP_AUTH_TOKEN chưa được cấu hình")
            return

        # Đọc Authorization header (case-insensitive theo HTTP spec)
        headers = dict(scope.get("headers") or [])
        auth_value = None
        for k, v in headers.items():
            if k.lower() == b"authorization":
                auth_value = v.decode("latin-1", errors="replace")
                break

        token = extract_bearer(auth_value)
        if not token or not verify_bearer_token(token):
            await self._reject(send, status=401, error="unauthorized", message="Bearer token không hợp lệ hoặc thiếu")
            return

        await self.app(scope, receive, send)

    @staticmethod
    async def _reject(send: Any, *, status: int, error: str, message: str) -> None:
        body = json.dumps({"error": error, "message": message}, ensure_ascii=False).encode("utf-8")
        await send(
            {
                "type": "http.response.start",
                "status": status,
                "headers": [
                    (b"content-type", b"application/json; charset=utf-8"),
                    (b"content-length", str(len(body)).encode("ascii")),
                    (b"www-authenticate", b'Bearer realm="mcp-server"'),
                ],
            }
        )
        await send({"type": "http.response.body", "body": body, "more_body": False})


__all__ = [
    "BearerAuthMiddleware",
    "HEALTH_PATHS",
    "extract_bearer",
    "get_expected_token",
    "verify_bearer_token",
]
