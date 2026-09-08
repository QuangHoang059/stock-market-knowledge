"""Entry point cho `python -m mcp_server`.

Cho phép chạy trực tiếp mà không cần `python -m mcp_server.server`.
"""

from mcp_server.server import main  # pyright: ignore[reportMissingImports]

if __name__ == "__main__":
    raise SystemExit(main())
