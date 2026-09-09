# MCP Server — `stock-market-knowledge`

Host bộ knowledge base (6 bài markdown) + Python pipeline (`tools/`) dưới dạng **MCP resources + tools**, để bất kỳ Claude client (Claude Code, Claude Desktop) nào cũng dùng được từ xa — không cần `git clone` repo.

## Tổng quan

| Thành phần | Số lượng | URI / Tên |
|------------|----------|-----------|
| Knowledge resources (markdown tĩnh) | 8 | `kb://01-basics`, `kb://02-buffett`, `kb://03-canslim`, `kb://04-wyckoff`, `kb://05-elliott`, `kb://06-risk`, `kb://skill`, `kb://index` |
| Resource template (reports động) | 1 | `kb://reports/{filename}` |
| Tools (chấm điểm + dữ liệu + rủi ro) | 12 | `evaluate_stock`, `get_history`, `get_fundamentals`, `get_index_trend`, `analyze_technical`, `score_value`, `score_canslim`, `position_size`, `suggest_stop`, `suggest_target`, `list_market_reports`, `get_market_report` |

## Kiến trúc

```
Client (Claude Code / Claude Desktop)
        │
        ▼  HTTPS + Authorization: Bearer <token>
nginx (reverse proxy có sẵn trên VPS)
        │
        ▼  HTTP localhost:8001
mcp_server (Docker container)
   ├─ FastMCP 1.x BearerAuthBackend (built-in, lifecycle-safe)
   │     └─ token_verifier=StaticBearerTokenVerifier() so sánh với MCP_AUTH_TOKEN
   ├─ /health    ← custom route, bypass auth (Docker healthcheck)
   └─ /mcp       ← streamable-http MCP transport (enforce Bearer token)
        │
        ▼
tools/ (evaluate, data, value_score, canslim_score, technical, risk)
   ├─ vnstock (cổ phiếu VN)
   └─ yahoo finance (chỉ số / mã quốc tế)
```

## Deploy lên VPS

### 1. Clone + setup env

```bash
git clone <repo-url> stock-market-knowledge
cd stock-market-knowledge/mcp_server

# Generate bearer token (chỉ chạy 1 lần, lưu vào password manager)
python -c "import secrets; print(secrets.token_urlsafe(32))"
# → ví dụ: aBcD3fG... (43 ký tự)

cp .env.example .env
nano .env   # dán token vào MCP_AUTH_TOKEN=...
```

### 2. Build + chạy Docker

```bash
docker compose up -d --build

# Check logs
docker compose logs -f stock-mcp

# Verify health
docker compose ps
# → STATUS: Up (healthy) trong vài giây
```

### 3. Cấu hình nginx

Tạo subdomain `mcp.your-domain.com` trỏ về VPS IP, sau đó:

```bash
# Xin cert Let's Encrypt
sudo certbot --nginx -d mcp.your-domain.com

# Paste nội dung `nginx.conf.snippet` vào server block certbot vừa tạo
sudo nano /etc/nginx/sites-available/mcp.your-domain.com
# (hoặc include file nếu thích)

# Test + reload
sudo nginx -t && sudo systemctl reload nginx
```

### 4. Test end-to-end

Từ máy bất kỳ (không phải VPS):

```bash
# Health check (bypass auth)
curl -i https://mcp.your-domain.com/health

# Auth check (phải có Bearer token)
curl -i -H "Authorization: Bearer $TOKEN" https://mcp.your-domain.com/mcp
```

## Cấu hình client

### Claude Code

Sửa `~/.claude/mcp.json` (hoặc `%USERPROFILE%\.claude\mcp.json` trên Windows):

```json
{
  "mcpServers": {
    "stock-knowledge": {
      "url": "https://mcp.your-domain.com/mcp",
      "headers": {
        "Authorization": "Bearer aBcD3fG..."
      }
    }
  }
}
```

### Claude Desktop

Sửa `claude_desktop_config.json`:

- macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`
- Windows: `%APPDATA%\Claude\claude_desktop_config.json`

```json
{
  "mcpServers": {
    "stock-knowledge": {
      "url": "https://mcp.your-domain.com/mcp",
      "headers": {
        "Authorization": "Bearer aBcD3fG..."
      }
    }
  }
}
```

Restart Claude → server xuất hiện trong danh sách MCP với 12 tools + 8 resources.

## Dùng local (không cần deploy)

Chạy stdio mode để dev/test trên máy cá nhân (không cần auth):

```bash
# Từ repo root
python -m mcp_server

# Hoặc chạy HTTP mode local (cần set MCP_AUTH_TOKEN)
export MCP_AUTH_TOKEN=dev-token
python -m mcp_server --http --port 8001
```

Test tự động:

```bash
python -m mcp_server.test_local
```

## Cập nhật knowledge / tools

### Knowledge (sửa file `.md`)

```bash
# Trên máy local — sửa xong commit
git add 0*.md && git commit -m "update bài 03" && git push

# Trên VPS
cd stock-market-knowledge && git pull
docker compose build stock-mcp && docker compose up -d
```

### Reports (`market_reports/`)

Reports mount qua volume, không cần rebuild:

```bash
# Trên máy local — generate report mới
python -m tools.evaluate FPT > market_reports/fpt_$(date +%F).md
git add market_reports/ && git commit -m "new FPT report" && git push

# Trên VPS — chỉ pull, KHÔNG cần restart container
cd stock-market-knowledge && git pull
# File mới tự xuất hiện trong `list_market_reports` ngay
```

### Tools (`tools/`)

Sửa code Python → rebuild:

```bash
git pull && docker compose build stock-mcp && docker compose up -d
```

## Troubleshooting

| Triệu chứng | Nguyên nhân | Cách fix |
|-------------|-------------|----------|
| Server exit ngay khi `docker compose up` | Thiếu `MCP_AUTH_TOKEN` trong `.env` | Set token rồi restart |
| Client không thấy server | Sai URL hoặc DNS chưa trỏ | `dig mcp.your-domain.com` kiểm tra |
| 401 Unauthorized từ client | Token sai/không match | Verify token trong `~/.claude/mcp.json` đúng y hệt `MCP_AUTH_TOKEN` trong `.env` |
| `evaluate_stock` trả `error: vnstock...` | VPS ở xa VN, network vnstock timeout | Tăng timeout hoặc dùng VPS gần VN (Singapore/Hong Kong) |
| Knowledge file không đọc được | File `.md` chưa có trong image | Rebuild: `docker compose build && up -d` |
| Container restart liên tục | HEALTHCHECK fail → kiểm tra log | `docker logs stock-mcp` |
| `RuntimeError: Task group is not initialized` khi gọi `/mcp` | Wrap ASGI middleware custom quanh `FastMCP.streamable_http_app()` vô hiệu hoá task group lifecycle | Dùng `token_verifier=` built-in của FastMCP (xem `mcp_server/auth.py` — `StaticBearerTokenVerifier`); KHÔNG wrap middleware thủ công |

Xem thêm log:

```bash
docker compose logs -f --tail 100 stock-mcp
```

## Security notes

- Bearer token enforce **ở cả nginx** (qua IP allowlist nếu muốn) **và MCP server** (defense in depth).
- Token KHÔNG BAO GIỜ commit vào git — file `.env` đã có trong `.gitignore` của repo.
- Health endpoint (`/health`) bypass auth — chỉ trả JSON status, không lộ nội dung knowledge.
- Mọi tool đều wrap exception → không crash process khi 1 mã cổ phiếu fail.
