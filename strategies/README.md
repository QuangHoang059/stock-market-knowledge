# 📊 10 Chiến lược Trading (Pine Script v6)

Bộ tài liệu tham khảo **10 chiến lược trading** kèm code Pine Script v6 cho TradingView. Tách thành từng file riêng để tiện backtest / paper trade trên nhiều mã và nhiều khung thời gian.

> ⚠️ **Disclaimer**: tài liệu chỉ phục vụ mục đích học tập. Các chiến lược **không đảm bảo lợi nhuận**. Hãy kiểm thử trên từng mã, từng khung thời gian và từng thị trường trước khi giao dịch tiền thật.

---

## 1. Quy ước chung

- `R = |Entry - SL|` — đơn vị rủi ro cố định cho mỗi lệnh.
- **TP theo R nghĩa** = khoảng cách chốt lời bằng một bội số của rủi ro (vd: 2R = TP cách entry 2 lần khoảng cách tới SL).
- Tất cả chiến lược chạy được cả **Long** lẫn **Short** trong TradingView Strategy Tester.
- Code minh hoạ dùng **Pine Script v6**.
- Với cổ phiếu, một số strategy (vd: ORB) cần chỉnh `session` theo giờ mở cửa của thị trường.
- **Phí giao dịch** và **slippage** nên cấu hình lại trong Strategy Properties.

---

## 2. Bảng tổng hợp 10 chiến lược

|#|Strategy|Loại|Timeframe|Entry|SL|TP|Tài liệu|
|---|---|---|---|---|---|---|---|
|1|EMA 20/50 Crossover|Trend following|1H / 4H|EMA crossover|Swing low/high|2R|[01](./01-ema-20-50-crossover.md)|
|2|Breakout + Volume|Breakout|15m / 1H|Phá level + volume|Nến breakout|2R|[02](./02-breakout-plus-volume.md)|
|3|Breakout + Retest|Breakout nâng cao|15m / 1H|Retest thành công|Retest swing|2R|[03](./03-breakout-retest.md)|
|4|EMA20 Pullback|Trend pullback|15m / 1H|Pullback về EMA|Swing|2R|[04](./04-ema20-pullback.md)|
|5|RSI + Bollinger MR|Mean reversion|15m / 1H|Giá về trong band|Swing|1.5R|[05](./05-rsi-bollinger-mean-reversion.md)|
|6|BB Squeeze Breakout|Volatility breakout|15m / 1H|Squeeze + phá band|Vùng tích lũy|2R|[06](./06-bollinger-squeeze-breakout.md)|
|7|VWAP Pullback|Intraday trend|5m / 15m|Pullback về VWAP|Swing|1.5R|[07](./07-vwap-pullback.md)|
|8|MACD + EMA200|Trend + momentum|1H / 4H|MACD cross theo EMA200|Swing|2R|[08](./08-macd-ema200-trend-filter.md)|
|9|Opening Range Breakout|Intraday breakout|5m / 15m|Phá opening range|Range ngược|2R|[09](./09-opening-range-breakout.md)|
|10|Donchian Channel Breakout|Breakout đa năng|1H / 4H / D|20-bar breakout|2×ATR(14)|3×ATR(14)|[10](./10-donchian-channel-breakout.md)|

---

## 3. Thứ tự nên backtest (từ dễ → khó)

1. **Donchian Breakout** — ít tham số, làm quen Strategy Tester.
2. **EMA20 Pullback** — học khái niệm trend + pullback.
3. **Breakout + Retest** — học market structure (HH/HL, LH/LL).
4. **VWAP Pullback** — day trading với volume profile.
5. **EMA20/50 Crossover** — trend following cổ điển.
6. **ORB** — intraday, làm quen session time.
7. **MACD + EMA200** — momentum + trend filter.
8. **Breakout + Volume** — xác nhận volume.
9. **BB Squeeze Breakout** — bắt biến động bùng nổ sau nén.
10. **RSI + Bollinger** — mean reversion.

Sau đó đánh giá theo **cùng một bộ tiêu chí**:
- Net Profit, Max Drawdown, Profit Factor
- Số lượng trade, Expectancy (E = win_rate × avg_win − loss_rate × avg_loss)
- Độ ổn định qua các giai đoạn thị trường

---

## 4. Tích hợp với stock-market-knowledge

Khi backtest xong, kết hợp với các công cụ trong [`../tools/`](../tools/) để đánh giá xem chiến lược có phù hợp với mã cổ phiếu cụ thể không:

- `python -m tools.evaluate <MÃ>` — chấm điểm giá trị (Buffett) + tăng trưởng (CANSLIM) + kỹ thuật
- `python -m tools.risk.suggest_stop <entry> <atr>` — tính stop-loss theo ATR
- `python -m tools.risk.position_size <capital> <risk_pct> <entry> <stop>` — tính position size

---

## 5. Expectancy — đừng chỉ nhìn Win Rate

**Ví dụ A** — win rate thấp, R:R tốt:
- Win rate 40% · Avg Win +2R · Avg Loss −1R
- `E = 0.40 × 2R − 0.60 × 1R = +0.20R / trade` → lợi nhuận đến từ lệnh thắng lớn.

**Ví dụ B** — win rate cao, R:R xấu:
- Win rate 70% · Avg Win +0.5R · Avg Loss −1R
- `E = 0.70 × 0.5R − 0.30 × 1R = +0.05R / trade` → dương nhưng mỏng, dễ âm khi phí tăng.

Cả hai đều có thể tốt, nhưng **cấu trúc lợi nhuận khác hẳn**. Đánh giá dựa trên expectancy + max drawdown + độ ổn định — không chỉ win rate.

---

## 6. Xem thêm

- Skill Claude: `.claude/skills/chien-luoc-giao-dich/SKILL.md` — hướng dẫn agent đọc + chọn strategy + backtest.
- MCP resources: `kb://strategy-01-..10-..` + `kb://skill-chien-luoc-giao-dich` (khi host lên VPS).
- TimesFM forecast: `tools/timesfm/` — dự báo giá tự động bằng TimesFM 3.0.
