---
name: chien-luoc-giao-dich
description: Chọn, giải thích và backtest 10 chiến lược trading (EMA crossover, breakout, VWAP pullback, v.v.) đi kèm code Pine Script v6 cho TradingView. Tích hợp TimesFM 3.0 để forecast giá. Dùng khi người dùng hỏi "nên dùng chiến lược nào cho BTC/cổ phiếu X", "backtest chiến lược EMA trên khung 1H", "forecast giá vàng bằng TimesFM", "đánh giá tín hiệu BUY/HOLD/SELL cho XAUUSD".
---

# Skill: Chiến lược giao dịch

Skill này điều phối 10 chiến lược trading trong thư mục `strategies/` (cùng repo `stock-market-knowledge/`),
kết hợp với bộ công cụ `tools/timesfm/` (TimesFM 3.0 forecast) và `tools/risk.py` (position sizing),
rồi **diễn giải kết quả theo đúng kiến thức** trong từng file strategy markdown.

## Khi nào dùng

Khi người dùng yêu cầu (bằng tiếng Việt hoặc tiếng Anh) một trong các dạng:

- "nên dùng chiến lược nào cho breakout BTC?"
- "backtest EMA crossover trên FPT khung 1H"
- "forecast giá vàng 12 bước tới"
- "đánh giá TimesFM so với baseline cho XAUUSD"
- "so sánh 3 chiến lược: Donchian, EMA pullback, MACD"
- "Tín hiệu BUY/SELL hiện tại cho XAUUSD là gì?"

## Quy trình (luôn làm theo thứ tự)

### 1. Xác định strategy phù hợp

Đọc [`strategies/README.md`](../../../strategies/README.md) bảng tổng hợp → chọn strategy theo:
- **Loại tín hiệu**: trend following (1, 4, 8) / breakout (2, 3, 6, 9, 10) / pullback (4, 7) / mean reversion (5)
- **Timeframe**: intraday (5m–15m) → 7, 9 ; swing (15m–1H) → 2, 3, 4, 5, 6 ; daily (1H–4H+) → 1, 8, 10
- **Độ khó backtest**: nếu user mới bắt đầu → gợi ý 1 (Donchian) trước.

Sau đó **đọc file markdown tương ứng** để biết:
- Cơ chế toán học (công thức entry/SL/TP)
- Tại sao chọn tham số mặc định (input + khoảng hợp lý)
- Ví dụ số minh hoạ
- Rủi ro chính

### 2. Chạy TimesFM forecast (tuỳ chọn, cần torch + timesfm3)

Nếu user muốn **dự báo giá thay vì backtest chiến lược cụ thể**:

```bash
# Từ stock-market-knowledge/
python -m tools.timesfm.cli forecast --symbol GC=F --horizon 12 --period 60d
# Output: current_price, forecast_prices[12], expected_returns_pct[12], signal BUY/HOLD/SELL
```

Nếu muốn **đánh giá độ chính xác của model** trước khi dùng:

```bash
python -m tools.timesfm.cli evaluate --symbol GC=F --max-samples 50 --period 60d
# Output: MAE/RMSE/MAPE/Direction Accuracy theo từng horizon [1, 3, 6, 12]
```

Nếu thiếu torch/timesfm3, CLI sẽ in lỗi rõ ràng — KHÔNG tự ý bỏ qua.

### 3. Tính position sizing (nếu user hỏi về quản trị vốn)

Kết hợp `tools/risk.py`:

```bash
# Tính stop-loss theo ATR (O'Neil):
python -c "from tools.risk import suggest_stop; print(suggest_stop(entry=72100, atr_value=1450, method='atr'))"
# → stop = 72100 - 2*1450 = 69200

# Tính position size với vốn 200tr, rủi ro 1.5%:
python -c "from tools.risk import position_size; print(position_size(capital=200_000_000, risk_pct=1.5, entry=72100, stop=69200, target=77800).to_dict())"
```

Công thức: `Số CP = (Vốn × Rủi ro %) / (Entry − SL)`.

### 4. Trình bày kết quả (tiếng Việt, cấu trúc cố định)

Luôn theo 5 mục này:

1. **Strategy đã chọn** — tên + lý do phù hợp (loại / timeframe / độ khó).
2. **Cơ chế chính** — entry/SL/TP theo file markdown (đừng bịa, phải copy từ tài liệu).
3. **TimesFM forecast** (nếu chạy) — current price + 12 forecast prices + tín hiệu BUY/HOLD/SELL.
4. **Đánh giá rủi ro** — position size, R:R ratio, verdict từ `position_size()`.
5. **Disclaimer + caveat** — LUÔN nêu: "không phải khuyến nghị đầu tư", "backtest trên sample chưa đủ lớn có thể overfit", "kiểm tra phí + slippage".

## Ví dụ flow

**User hỏi**: "BTC đang breakout, nên dùng chiến lược nào? Forecast giá 6 giờ tới?"

**Agent trả lời**:
> ### Chiến lược gợi ý: Breakout + Volume (`strategies/02-breakout-plus-volume.md`)
> Phù hợp vì: BTC đang có range consolidation + volume tăng dần trên 1H.
>
> **Cơ chế**: Entry khi giá phá resistance với volume > 1.5× trung bình 20 nến.
> SL = low của nến breakout. TP = 2R.
>
> **TimesFM forecast** (BTC-USD 1H, horizon=6):
> - Current: 67,500
> - T+1: 67,820 (+0.47%)
> - T+3: 68,140 (+0.95%)
> - T+6: 68,560 (+1.57%)
> - Signal: **BUY** (expected return +1.57% > threshold +0.2%)
>
> **Position sizing** (vốn 200tr, rủi ro 1.5%):
> - Entry 67,500 / SL 65,800 (2R = 1,700) / TP 70,900
> - Shares ≈ 1,764 CP × 67,500 = 119 triệu (60% vốn)
> - R:R = 1:2, verdict OK.
>
> **⚠️ Disclaimer**: TimesFM model có direction accuracy ~52–55% ở horizon 1–6 — tốt hơn
> baseline naive ~50% nhưng KHÔNG đảm bảo lợi nhuận. Backtest strategy trên dữ liệu BTC
> 2 năm trước khi vào lệnh thật. Cắt lỗ 7–8% (O'Neil) nếu giá không đi đúng hướng.

## Bảng 10 chiến lược (quick reference)

| # | Strategy | Loại | TF | Entry | SL | TP |
|---|----------|------|-----|-------|-----|-----|
| 1 | EMA 20/50 Crossover | Trend | 1H/4H | EMA cross | Swing | 2R |
| 2 | Breakout + Volume | Breakout | 15m/1H | Phá level + volume | Nến BO | 2R |
| 3 | Breakout + Retest | Breakout | 15m/1H | Retest OK | Retest swing | 2R |
| 4 | EMA20 Pullback | Pullback | 15m/1H | Pullback về EMA | Swing | 2R |
| 5 | RSI + BB MR | Mean rev | 15m/1H | Giá về band | Swing | 1.5R |
| 6 | BB Squeeze BO | Volatility | 15m/1H | Squeeze + phá band | Tích lũy | 2R |
| 7 | VWAP Pullback | Intraday | 5m/15m | Pullback VWAP | Swing | 1.5R |
| 8 | MACD + EMA200 | Trend | 1H/4H | MACD cross EMA200 | Swing | 2R |
| 9 | ORB | Intraday | 5m/15m | Phá opening range | Range ngược | 2R |
| 10 | Donchian BO | Breakout | 1H/4H/D | 20-bar breakout | 2×ATR | 3×ATR |

## Lưu ý

- **KHÔNG tự ý chạy TimesFM với dữ liệu giả**. Model cần download checkpoint lần đầu (~500MB từ HuggingFace).
- **Nếu TimesFM chưa cài** (thiếu torch/timesfm3): chỉ phân tích strategy theo markdown, KHÔNG dùng forecast.
- **Với cổ phiếu VN**: cần chỉnh `session` cho ORB theo giờ mở cửa HOSE/HNX/UPCoM. Backtest trên 3–5 năm để có đủ sample size.
- **Walk-forward eval** của TimesFM chỉ là lower bound — model có thể overfit nếu max_samples < 50.
- Khi user hỏi "so sánh N chiến lược" → đọc từng file markdown, lập bảng so sánh expected return / max drawdown.
- Luôn đính kèm **disclaimer** trong mọi câu trả lời có khuyến nghị giao dịch.
