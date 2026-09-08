FROM python:3.11-slim

# Đặt locale UTF-8 để in tiếng Việt không lỗi
ENV LANG=C.UTF-8 \
    LC_ALL=C.UTF-8 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    MCP_TRANSPORT=http \
    MCP_HOST=0.0.0.0 \
    MCP_PORT=8001

WORKDIR /app

# Cài deps trước để cache layer khi chỉ sửa code.
# vnstock + pandas cần build wheels — slim + apt cơ bản.
RUN apt-get update \
    && apt-get install -y --no-install-recommends gcc \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt mcp>=1.0

# ML deps riêng (CPU-only torch) — optional layer, ~200MB. Có thể comment
# nếu không cần TimesFM ở production (tool timesfm_* sẽ trả error JSON).
COPY requirements-ml.txt ./
RUN pip install --no-cache-dir -r requirements-ml.txt || echo "[WARN] ML deps install failed — timesfm_* tools sẽ không hoạt động"

# Copy source. .dockerignore loại .git, .venv, market_reports, .claude, v.v.
COPY . .

# Healthcheck TCP probe (không cần endpoint /health riêng).
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD python -c "import socket; s=socket.socket(); s.settimeout(3); s.connect(('localhost', 8001)); s.close()" || exit 1

EXPOSE 8001

# MCP_AUTH_TOKEN phải được set qua env_file (.env) hoặc docker-compose env.
# Server sẽ từ chối start nếu thiếu — xem mcp_server/server.py.
CMD ["python", "-m", "mcp_server", "--http"]
