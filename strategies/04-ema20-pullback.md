# 04. EMA20 Pullback

> Pine Script v6 · Trend pullback · Khung 15m/1H.

---

## 1. Mục đích

Một chiến lược kinh điển của **trend following**: đợi xu hướng đã rõ (EMA20 > EMA50) rồi **mua pullback** — tức đợi giá tạm thời chạm EMA20 (dynamic support) rồi bật lên.

Ưu điểm so với **strategy #1 (EMA crossover)**: vào lệnh với **giá tốt hơn** (pullback sâu hơn), R:R cao hơn, nhưng đòi hỏi trend đã rõ ràng.

---

## 2. Khi nào hoạt động tốt / xấu

### Phù hợp

- **Uptrend / downtrend** rõ ràng, EMA20 và EMA50 cách xa nhau.
- Sau khi breakout khỏi range → pullback về EMA20 = cơ hội tốt.
- Khung 15m / 1H cho swing intraday, 4H cho swing dài hơn.

### Không phù hợp

- **Range / choppy**: EMA20 và EMA50 đan xen → điều kiện `EMA20 > EMA50` thoả mãn lúc, fail lúc khác → tín hiệu rác.
- **Trend đảo chiều mạnh**: EMA20 có thể trở thành **resistance** thay vì support — pullback không bật lên mà xuyên thủng.
- Khi tin quan trọng sắp ra.

---

## 3. Cơ chế toán học / chỉ báo

Tương tự strategy #1, EMA20 đóng vai trò **dynamic support** trong uptrend và **dynamic resistance** trong downtrend. Công thức EMA xem lại ở [strategy #1](./01-ema-20-50-crossover.md).

**Điều kiện Long (pullback trong uptrend)**:

```text
EMA20 > EMA50       // uptrend
close > EMA50       // giá đang ở "đúng phía" xu hướng
low   ≤ EMA20       // nến chạm EMA20 (pullback)
close > EMA20       // nhưng đóng cửa lại trên EMA20 (bật lên)
```

Ý nghĩa: "trend đang lên, giá tạm thời rơi về EMA20 rồi bật lên — phe mua vẫn kiểm soát".

**Điều kiện Short** là phép đối ngẫu (downtrend + pullback lên EMA20 + đóng cửa dưới).

---

## 4. Tại sao chọn tham số mặc định

|Input|Mặc định|Ý nghĩa|
|---|---|---|
|EMA20|20|Đường "gần giá nhất", phản ứng nhanh — phù hợp cho pullback intraday/swing.|
|EMA50|50|Filter trend trung hạn. Khoảng cách EMA20 – EMA50 phải đủ lớn để uptrend/downtrend rõ ràng.|
|`swingLen`|5|SL đặt ở swing low/high 5 nến — gần EMA20 nhưng đủ buffer tránh bị quét.|
|`rr`|2.0|TP 2R.|

**Phân biệt với strategy #1**: #1 **chờ crossover** (EMA20 cắt EMA50) — tín hiệu đến trễ, khi trend đã đi được 1 đoạn. #4 **chờ pullback** — vào sớm hơn trong trend với giá tốt hơn.

---

## 5. Luật

### Long

1. `EMA20 > EMA50` (uptrend).
2. `close > EMA50` (giá đứng đúng phía).
3. `low ≤ EMA20` (pullback chạm EMA20).
4. `close > EMA20` (bật lên, xác nhận EMA20 giữ).
5. Entry ở giá đóng cửa nến tín hiệu.

### Short

Đối ngẫu với `EMA20 < EMA50`, `close < EMA50`, `high ≥ EMA20`, `close < EMA20`.

### Stop Loss

- Long: swing low 5 nến (`ta.lowest(low, swingLen)`).
- Short: swing high 5 nến (`ta.highest(high, swingLen)`).

### Take Profit

**2R**.

---

## 6. Pine Script v6

```pine
//@version=6
strategy("04 - EMA20 Pullback", overlay=true, pyramiding=0)

ema20 = ta.ema(close, 20)
ema50 = ta.ema(close, 50)

swingLen = input.int(5, "Swing Length")
rr = input.float(2.0, "Risk/Reward")

longCond = ema20 > ema50 and close > ema50 and low <= ema20 and close > ema20
shortCond = ema20 < ema50 and close < ema50 and high >= ema20 and close < ema20

if longCond
    sl = ta.lowest(low, swingLen)
    risk = close - sl
    if risk > 0
        strategy.entry("Long", strategy.long)
        strategy.exit("Long Exit", "Long", stop=sl, limit=close + risk * rr)

if shortCond
    sl = ta.highest(high, swingLen)
    risk = sl - close
    if risk > 0
        strategy.entry("Short", strategy.short)
        strategy.exit("Short Exit", "Short", stop=sl, limit=close - risk * rr)

plot(ema20, "EMA20")
plot(ema50, "EMA50")
```

---

## 7. Ví dụ số (minh hoạ)

AAPL 1H, giá đang trong uptrend:

|Nến|Close|EMA20|EMA50|Quan sát|
|---|---|---|---|---|
|#1|195.0|194.8|192.0|EMA20 > EMA50|
|#2|194.0|194.5|192.1|Giá rơi về gần EMA20|
|#3|192.5|194.0|192.2|low = 192.3 ≤ EMA20 = 194.0|
|#4|194.5|194.2|192.3|close = 194.5 > EMA20 = 194.2|

Tín hiệu Long ở nến #4 (cần đủ 4 điều kiện **trong cùng nến** hoặc vừa thoả ở nến này).

- Entry = 194.5
- SL = swing low 5 nến = 192.0 → **R = 2.5**
- TP = 194.5 + 2 × 2.5 = **199.5**

---

## 8. Rủi ro chính & lưu ý chỉnh tham số

### Rủi ro

- **EMA20 bị xuyên thủng** (EMA flip): trend đảo chiều nhưng EMA20 chưa phản ứng kịp → pullback này không phải pullback mà là **breakdown**.
- **Pullback sâu quá mức**: giá có thể xuyên EMA20 rồi EMA50 — đó không còn là pullback mà là đảo chiều. SL theo swing sẽ bảo vệ phần nào, nhưng R sẽ rất lớn.
- **Whipsaw khi EMA quấn nhau**: chỉ trade khi `|EMA20 − EMA50|` đủ lớn (vd: > 1% giá).
- **Phí trên khung nhỏ**: ở khung 1m–5m, EMA20 pullback xảy ra rất thường xuyên, phí sẽ ăn lợi nhuận.

### Lưu ý khi tối ưu

- Thêm filter: chỉ vào lệnh khi `close > EMA20` (lúc đầu pullback) **hoặc** `low ≤ EMA20 * 1.001` (chạm rất gần EMA20) để tránh tín hiệu pullback sâu đã thành breakdown.
- Với cổ phiếu, EMA20 / EMA50 có thể thay bằng SMA20 / SMA50 (chậm hơn, ít tín hiệu hơn nhưng ổn định hơn).
- Kết hợp với **volume** tăng lúc bật lên (rejection candle) để tăng xác suất thắng.

---

## 9. Timeframe gợi ý & Inputs chính

|Input|Mặc định|Khoảng hợp lý|Ghi chú|
|---|---|---|---|
|EMA20|20|10–30|Intraday: 10–20 ; swing: 20–30|
|EMA50|50|40–100|Đừng < 2× EMA20|
|`swingLen`|5|3–10|SL càng rộng — R càng lớn — cần RR cao hơn|
|`rr`|2.0|1.5–3.0||
|Timeframe|15m/1H|5m → Daily|5m quá nhiễu, daily pullback rất hiếm|
