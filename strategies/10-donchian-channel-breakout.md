# 10. Donchian Channel Breakout

> Pine Script v6 · Breakout đa năng · Multi-timeframe.

---

## 1. Mục đích

**Donchian Channel** = high / low của N nến gần nhất. Chiến lược kinh điển của **huyền thoại Richard Dennis** ("Turtle Trading") — vào lệnh khi giá phá high/low 20 nến trước.

Đây là chiến lược **đơn giản nhất** trong bộ 10: chỉ cần 1 chỉ báo, 1 quy tắc — nhưng rất hiệu quả trên **khung lớn** (Daily, 4H) và thị trường trending.

---

## 2. Khi nào hoạt động tốt / xấu

### Phù hợp

- **Trending dài hạn** rõ ràng (commodity, FX majors, index futures).
- **Khung lớn** (Daily, 4H) — Turtle Trading gốc dùng Daily.
- Thị trường có **xu hướng mạnh**, ít whipsaw.

### Không phù hợp

- **Sideway kéo dài** → Donchian breakout liên tục nhưng giá quay lại ngay → thua.
- **Tin bất ngờ** (black swan): breakout có thể là spike 1 nến rồi đảo chiều.
- **Khung quá nhỏ** (1m–5m) — Donchian bị nhiễu bởi spread.

---

## 3. Cơ chế toán học / chỉ báo

**Donchian Channel** xác định bằng high / low của N nến trước:

```text
upper = max(high[1], n)         // high của N nến trước, không bao gồm nến hiện tại
lower = min(low[1], n)          // low của N nến trước
```

`[1]` nghĩa là **không bao gồm nến hiện tại** — nếu dùng `high` nến hiện tại sẽ luôn breakout.

**Tín hiệu**:

```text
long  = close > upper    // giá đóng cửa phá high N nến trước
short = close < lower    // giá đóng cửa xuyên low N nến trước
```

**ATR (Average True Range)** dùng để đặt SL/TP theo **biến động hiện tại**, không theo R cố định:

```text
SL = entry − ATR × slATR     // Long
TP = entry + ATR × tpATR     // Long
```

Cách này thích nghi với biến động thị trường: khi ATR lớn (volatile), SL/TP rộng; khi ATR nhỏ (sideway), SL/TP hẹp.

---

## 4. Tại sao chọn tham số mặc định

|Input|Mặc định|Ý nghĩa|
|---|---|---|
|`donchianLen`|20|Chuẩn Turtle Trading.|
|`atrLen`|14|Chuẩn phổ biến.|
|`slATR`|2.0|SL = 2 ATR.|
|`tpATR`|3.0|TP = 3 ATR — R:R = 1:1.5 (thấp hơn 2R của strategies khác).|

**Tại sao RR = 1:1.5 thay vì 1:2?** Turtle Trading dùng R:R thấp (~1:1.5) nhưng win rate cao (~40–50%) nhờ SL/TP adaptive. Khi ATR tăng, TP cũng tăng → bắt được các trend lớn.

**Khi tăng `donchianLen`** → breakout hiếm hơn nhưng đáng tin hơn.
**Khi giảm** → nhiều tín hiệu, dễ whipsaw.

---

## 5. Luật

### Long

1. `close > highest(high[1], 20)` (giá phá high 20 nến trước).
2. Entry ở giá đóng cửa nến tín hiệu.

### Short

1. `close < lowest(low[1], 20)`.
2. Entry.

### Stop Loss

- Long: `entry − ATR(14) × 2`.
- Short: `entry + ATR(14) × 2`.

### Take Profit

- Long: `entry + ATR(14) × 3`.
- Short: `entry − ATR(14) × 3`.

---

## 6. Pine Script v6

```pine
//@version=6
strategy("10 - Donchian Breakout", overlay=true, pyramiding=0)

donchianLen = input.int(20, "Donchian Length")
atrLen = input.int(14, "ATR Length")
slATR = input.float(2.0, "SL ATR")
tpATR = input.float(3.0, "TP ATR")

upper = ta.highest(high[1], donchianLen)
lower = ta.lowest(low[1], donchianLen)
atr = ta.atr(atrLen)

longCond = close > upper
shortCond = close < lower

if longCond
    sl = close - atr * slATR
    tp = close + atr * tpATR
    strategy.entry("Long", strategy.long)
    strategy.exit("Long Exit", "Long", stop=sl, limit=tp)

if shortCond
    sl = close + atr * slATR
    tp = close - atr * tpATR
    strategy.entry("Short", strategy.short)
    strategy.exit("Short Exit", "Short", stop=sl, limit=tp)

plot(upper, "Donchian Upper")
plot(lower, "Donchian Lower")
```

---

## 7. Ví dụ số (minh hoạ)

BTCUSDT Daily:

|Bar|High|Low|Close|Donchian High(20)|ATR(14)|
|---|---|---|---|---|---|
|Bar #1–20|dao động 60k–68k|||68,000|2,500|
|Bar #21|70,000|67,500|69,500|68,000|2,500|

Bar #21 close = 69,500 > 68,000 → **Long breakout**.

- Entry = 69,500
- SL = 69,500 − 2,500 × 2 = **64,500**
- TP = 69,500 + 2,500 × 3 = **77,000**

R:R thực tế = (77,000 − 69,500) : (69,500 − 64,500) = 7,500 : 5,000 = 1:1.5.

---

## 8. Rủi ro chính & lưu ý chỉnh tham số

### Rủi ro

- **Whipsaw trong range**: Donchian breakout liên tục → SL hit liên tục. Cách hạn chế: chỉ trade khi ATR tăng (volatility expansion).
- **Spike đảo chiều**: tin bất ngờ tạo breakout giả → SL hit, sau đó giá đi đúng hướng.
- **R:R thấp (1:1.5)** → cần win rate > 40% để expectancy dương.
- **Ngược trend lớn**: Donchian breakout ngắn hạn có thể đi **ngược** trend daily.

### Lưu ý khi tối ưu

- Có thể thêm **filter trend** (vd: chỉ Long khi close > SMA200) để giảm tín hiệu ngược trend.
- **Donchian 55-bar** (Turtle Trading "System 2") — ít tín hiệu hơn, chỉ bắt trend rất lớn.
- **Trailing stop** thay vì SL cố định có thể tăng lợi nhuận trong trend dài.

---

## 9. Timeframe gợi ý & Inputs chính

|Input|Mặc định|Khoảng hợp lý|Ghi chú|
|---|---|---|---|
|`donchianLen`|20|10–55|20 = Turtle System 1 ; 55 = System 2|
|`atrLen`|14|10–20||
|`slATR`|2.0|1.5–3.0|SL rộng hơn — ít whipsaw, R lớn hơn|
|`tpATR`|3.0|2.0–5.0||
|Timeframe|1H/4H/D|4H → Daily|Intraday: nhiều nhiễu, Daily: chuẩn Turtle|
