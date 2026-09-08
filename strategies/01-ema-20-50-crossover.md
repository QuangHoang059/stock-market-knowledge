# 01. EMA 20/50 Crossover — Trend Following

> Pine Script v6 · Trend following · Đa khung thời gian.

---

## 1. Mục đích

Bắt **xu hướng trung hạn** bằng cách đợi một EMA ngắn hạn (20) **cắt lên/xuống** một EMA dài hạn (50) — dấu hiệu momentum đang đổi chiều. Khi tín hiệu đi kèm điều kiện giá đóng cửa đứng đúng phía xu hướng, xác suất trend tiếp diễn cao hơn so với chỉ nhìn giá trần/thuỷ.

---

## 2. Khi nào hoạt động tốt / xấu

### Phù hợp

- Thị trường có **xu hướng rõ** (crypto/forex trending, cổ phiếu mid-cap theo tin tức lớn).
- Khung thời gian **1H / 4H** cho swing trade; có thể lên daily cho position trade.
- Có **volume nền** ổn định, ít gap.

### Không phù hợp

- **Sideway / range** hẹp → EMA bị nhiễu, hai đường **quấn vào nhau**, ra vào lệnh liên tục → whipsaw.
- Phiên **low volume** (vd: cuối tuần crypto, sau giờ giao dịch cổ phiếu Mỹ).
- Khi tin kinh tế lớn sắp ra → tín hiệu dễ bị "fakeout" bởi spike đầu phiên.

---

## 3. Cơ chế toán học / chỉ báo

**EMA (Exponential Moving Average)** là trung bình cộng có trọng số hàm mũ — phản ứng nhanh hơn SMA vì đặt nhiều trọng số hơn lên các nến gần nhất:

```text
k    = 2 / (n + 1)
EMAₙ = Close × k + EMAₙ₋₁ × (1 − k)
```

Với `n = 20` → `k ≈ 0.0952`. Với `n = 50` → `k ≈ 0.0392`. EMA20 "mượt" hơn SMA20 không đáng kể ở vùng giá gần, nhưng **nhanh hơn SMA50 khá nhiều** khi giá đột biến.

**Crossover** xảy ra khi:

- **Golden cross (Long)**: `EMA20[bar trước] ≤ EMA50[bar trước]` **và** `EMA20[hiện tại] > EMA50[hiện tại]`.
- **Death cross (Short)**: ngược lại.

Pine cung cấp sẵn `ta.crossover()` / `ta.crossunder()` nên không cần tự kiểm tra hai điều kiện.

---

## 4. Tại sao chọn tham số mặc định

|Input|Mặc định|Ý nghĩa|
|---|---|---|
|`fastLen`|20|Đại diện **1 phiên giao dịch Mỹ** (20 × 5m = 100 phút ≈ 1 phiên), hoặc **1 tuần trading** trên khung 1H.|
|`slowLen`|50|Trung bình 2.5 phiên / 2.5 tuần — đủ dài để lọc noise nhưng không quá trễ.|
|`rr`|2.0|TP gấp **2 lần** rủi ro — đảm bảo expectancy dương ngay cả khi win rate chỉ ~40%.|
|`swing`|5|Swing low/high **5 nến** gần nhất — khoảng đệm vừa đủ để SL không quá sát.|

**Khi tăng `fastLen`/`slowLen`** → EMA phản ứng chậm hơn → **ít tín hiệu nhưng chất lượng cao hơn**, dễ bỏ lỡ đầu trend.

**Khi giảm** → nhiều tín hiệu hơn nhưng nhiều tín hiệu giả, đặc biệt trong range.

---

## 5. Luật

### Long

1. `EMA20` cắt lên `EMA50` (`ta.crossover`).
2. Giá đóng cửa > `EMA50` (lọc nhiễu, xác nhận đã đứng đúng phía).
3. Entry ở giá đóng cửa nến tín hiệu.

### Short

1. `EMA20` cắt xuống `EMA50` (`ta.crossunder`).
2. Giá đóng cửa < `EMA50`.
3. Entry ở giá đóng cửa nến tín hiệu.

### Stop Loss

- Long: dưới **swing low** của N nến gần nhất (`ta.lowest(low, swing)`).
- Short: trên **swing high** của N nến gần nhất (`ta.highest(high, swing)`).

### Take Profit

**2R** = entry + `2 × |entry − SL|`.

---

## 6. Pine Script v6

```pine
//@version=6
strategy("01 - EMA 20/50 Crossover", overlay=true, pyramiding=0)

fastLen = input.int(20, "EMA Fast")
slowLen = input.int(50, "EMA Slow")
rr      = input.float(2.0, "Risk/Reward", minval=0.1)
swing   = input.int(5, "Swing Lookback", minval=1)

emaFast = ta.ema(close, fastLen)
emaSlow = ta.ema(close, slowLen)

longCond  = ta.crossover(emaFast, emaSlow) and close > emaSlow
shortCond = ta.crossunder(emaFast, emaSlow) and close < emaSlow

longSL  = ta.lowest(low, swing)
shortSL = ta.highest(high, swing)

if longCond and longSL < close
    risk = close - longSL
    strategy.entry("Long", strategy.long)
    strategy.exit("Long Exit", "Long", stop=longSL, limit=close + risk * rr)

if shortCond and shortSL > close
    risk = shortSL - close
    strategy.entry("Short", strategy.short)
    strategy.exit("Short Exit", "Short", stop=shortSL, limit=close - risk * rr)

plot(emaFast, "EMA 20")
plot(emaSlow, "EMA 50")
```

---

## 7. Ví dụ số (minh hoạ)

Giả sử giá đóng cửa các nến (5 nến gần nhất) đều loanh quanh $100, EMA20 = $100, EMA50 = $99.

|Nến|Close|EMA20|EMA50|Sự kiện|
|---|---|---|---|---|
|#1|100.0|100.0|99.0|EMA20 > EMA50 (giữ)|
|#2|100.5|100.1|99.0|Có thể cắt — tuỳ nến trước|
|#3|101.0|100.3|99.0|Golden cross xác nhận, Close > EMA50|
|#4|100.6|100.4|99.1|—|
|#5|99.5|100.2|99.1|Low = 99.2 — SL = 99.2|

- Entry = 100.6 (nến #4) nếu tín hiệu xuất hiện ở đây (crossover + Close > EMA50).
- SL = swing low gần nhất = 99.2 → **R = 100.6 − 99.2 = 1.4**.
- TP = 100.6 + 2 × 1.4 = **103.4**.

Rủi ro thực = 1.4 USD / 1 đơn vị. Nếu chạm TP, lời 2R = 2.8 USD.

---

## 8. Rủi ro chính & lưu ý chỉnh tham số

### Rủi ro

- **Whipsaw trong range**: hai EMA quấn vào nhau → hàng loạt tín hiệu thua. Cách hạn chế: chỉ trade khi `ATR` đang tăng, hoặc thêm filter ADX > 25.
- **Lag**: EMA phản ứng chậm — bạn sẽ vào lệnh **sau khi trend đã đi được một đoạn**, dẫn tới R:R thực tế thấp hơn 2R.
- **Slippage trên breakout gap**: nến tín hiệu có thể mở cửa xa giá kỳ vọng → fill không đúng entry lý thuyết.
- **Phí giao dịch**: nếu trade khung 1m–5m với spread lớn, 2R có thể không đủ bù phí.

### Lưu ý khi tối ưu

- Đừng điều chỉnh `fastLen`/`slowLen` cho từng mã — sẽ overfit. Giữ một bộ tham số, test trên nhiều symbol.
- Nếu muốn nhanh hơn, dùng **EMA 9/21** (chuẩn "turtles modified") nhưng kỳ vọng whipsaw cao hơn.
- Nếu muốn chậm hơn, dùng **EMA 50/200** (chuẩn "Golden Cross / Death Cross") — rất ít tín hiệu, chỉ phù hợp position trade.

---

## 9. Timeframe gợi ý & Inputs chính

|Input|Mặc định|Khoảng hợp lý|Ghi chú|
|---|---|---|---|
|`fastLen`|20|10–30|10 cho intraday, 30 cho swing dài|
|`slowLen`|50|40–100|Đừng để `slowLen < 2 × fastLen`|
|`rr`|2.0|1.5–3.0|TP > 2R cần win rate thấp hơn để vẫn dương|
|`swing`|5|3–10|Tăng lên nếu SL hay bị quét do noise|
|Timeframe|1H/4H|15m → Daily|Khung càng lớn — SL càng rộng — R càng lớn|
