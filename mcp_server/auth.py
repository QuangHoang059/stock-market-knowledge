"""Bearer token authentication cho HTTP transport.

Khi chạy HTTP, server bắt buộc phải có `MCP_AUTH_TOKEN` (không cho phép
chạy unauthenticated trên internet).

Triển khai `TokenVerifier` protocol của FastMCP 1.x → FastMCP tự wrap
`BearerAuthBackend` ASGI middleware nội bộ (với task group được init qua
`mcp.run()`). Trước đây code wrap `BearerAuthMiddleware` thủ công quanh
Starlette app riêng — wrap như vậy vô hiệu hoá lifecycle của FastMCP và
gây `RuntimeError: Task group is not initialized` khi request đến.

Token comparison dùng `hmac.compare_digest` để chống timing attack.
"""

from __future__ import annotations

import hmac
import logging
import os

from mcp.server.auth.provider import AccessToken, TokenVerifier

logger = logging.getLogger(__name__)


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
    return parts[1].strip() or None


class StaticBearerTokenVerifier(TokenVerifier):
    """TokenVerifier cho static bearer token (không OAuth).

    So sánh token với MCP_AUTH_TOKEN qua `hmac.compare_digest`. Trả
    `AccessToken` hợp lệ nếu khớp, `None` nếu không. FastMCP sẽ trả
    401 cho client khi `verify_token` trả `None`.
    """

    async def verify_token(self, token: str) -> AccessToken | None:
        if not verify_bearer_token(token):
            return None
        return AccessToken(
            token=token,
            client_id="bearer-token-client",
            scopes=["read", "write"],
        )


__all__ = [
    "StaticBearerTokenVerifier",
    "extract_bearer",
    "get_expected_token",
    "verify_bearer_token",
]