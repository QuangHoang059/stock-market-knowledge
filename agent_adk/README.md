# agent_adk — Google ADK Strategy Evaluator

Folder mới trong `stock-market-knowledge/` chạy trên **Google ADK Python** với **LiteLLM** provider switcher (Claude / Gemini / DeepSeek) để evaluate và iterate các chiến lược trading từ `../strategies/*.md`.

## Cấu trúc

```
agent_adk/
├── core/                          # Pure Python — không phụ thuộc ADK
│   ├── data_loader.py             # yfinance → CSV (XAUUSD, BTCUSD)
│   ├── strategies/                # 10 chiến lược port từ Pine Script v6
│   ├── engine/
│   │   ├── backtest.py            # Vectorized bar-by-bar backtest
│   │   ├── metrics.py             # Sharpe, max DD, win rate, profit factor
│   │   └── evaluator.py           # Rank + markdown output
│   └── tools_adk.py               # ADK FunctionTool wrappers
├── agents/                        # ADK LlmAgent definitions
│   ├── data_refresh.py            # refresh 6 ngày CSV
│   ├── strategist.py              # đề xuất/sửa strategy (Claude)
│   ├── backtest_runner.py         # chạy backtest engine (Gemini)
│   ├── critic.py                  # chấm điểm (DeepSeek)
│   └── reporter.py                # viết báo cáo (Claude)
├── pipeline.py                    # SequentialAgent + LoopAgent wiring
├── runner.py                      # InMemoryRunner + CLI
├── scripts/                       # CLI không cần LLM
│   ├── download_data.py           # tải 2 năm XAUUSD + BTCUSD
│   ├── refresh_data.py            # append 6 ngày
│   └── evaluate_only.py           # backtest 10 strategies (no LLM)
├── reports/                       # Markdown output
│   ├── latest_XAUUSD_1d.md
│   └── history/
└── providers.env.example          # Template cho API keys
```

## Quy trình sử dụng

### Bước 1 — Tải dataset lần đầu

```bash
python -m agent_adk.scripts.download_data
# → 6 file CSV trong agent_adk/core/data/ (XAUUSD/BTCUSD × 1d/4h/1h)
```

### Bước 2 — Sanity check (không cần LLM)

```bash
python -m agent_adk.scripts.evaluate_only --symbol XAUUSD --timeframe 1d --save-md
# → in bảng ranking 10 strategies, lưu reports/latest_XAUUSD_1d.md
```

### Bước 3 — Refresh 6 ngày gần nhất

```bash
python -m agent_adk.scripts.refresh_data --symbol XAUUSD --all-timeframes
# (ưu tiên XAUUSD)
```

### Bước 4 — Full ADK pipeline (cần API key)

```bash
# Cấu hình provider (mặc định claude)
cp providers.env.example providers.env
# Điền GEMINI_API_KEY / ANTHROPIC_API_KEY / DEEPSEEK_API_KEY

# Chạy loop agent: refresh → strategist ↔ backtest ↔ critic (≤5 vòng) → reporter
python -m agent_adk.runner --symbol XAUUSD --timeframe 1d --goal "max DD < 15%"
```

Đổi provider qua env var:
```bash
$env:AGENT_ADK_PROVIDER = "gemini"
python -m agent_adk.runner --symbol XAUUSD
```

### Bước 5 — Đọc báo cáo

```bash
cat agent_adk/reports/latest_XAUUSD_1d.md
# hoặc xem các snapshot cũ:
ls agent_adk/reports/history/
```

## Quy trình lặp (test → sửa / tạo mới → đánh giá)

1. Sửa 1 file `core/strategies/sNN_xxx.py` (vd: đổi `fast_len=20 → 15`).
2. Chạy `python -m agent_adk.scripts.refresh_data --symbol XAUUSD --all-timeframes`.
3. Chạy `python -m agent_adk.scripts.evaluate_only --symbol XAUUSD --timeframe 1d --save-md`.
4. So sánh `reports/latest_XAUUSD_1d.md` với snapshot cũ.
5. Nếu metrics cải thiện → giữ, nếu xấu → revert.
6. Strategy hoàn toàn mới → tạo `core/strategies/s11_xxx.py` + thêm vào `core/strategies/registry.py`, lặp lại.

## Tuỳ chỉnh ngưỡng Critic

Sửa trong `agent_adk/config.py`:
```python
MIN_SHARPE = 0.5
MAX_DRAWDOWN_PCT = 20.0
MIN_WIN_RATE = 0.40
MIN_PROFIT_FACTOR = 1.2
```

## Provider mapping (LiteLLM)

| `AGENT_ADK_PROVIDER` | LiteLLM model |
|---|---|
| `claude` (mặc định) | `anthropic/claude-sonnet-4-5` |
| `gemini` | `gemini/gemini-2.5-pro` |
| `deepseek` | `deepseek/deepseek-chat` |

Xem `agent_adk/llm.py` để thêm provider khác.
