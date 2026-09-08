"""MCP server for stock-market-knowledge.

Host the Vietnamese stock-market knowledge base (bài 01–06) and the Python
evaluation tools (`tools/`) as MCP resources + tools, so any Claude client
can access them remotely without git cloning the repo.

Usage:
    python -m mcp_server                    # stdio (local dev, no auth)
    python -m mcp_server --http             # streamable-http on 127.0.0.1:8001
"""

__version__ = "0.1.0"
