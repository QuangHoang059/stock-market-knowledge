# 03. Breakout + Retest

> Pine Script v6 · Breakout nâng cao · Market structure.

---

## 1. Mục đích

Nâng cấp của **strategy #2 (Breakout + Volume)**. Thay vì vào lệnh ngay khi giá phá level, chiến lược này **đợi giá quay lại "hôn" level cũ** rồi bật lên lại — một mô hình rất phổ biến trong market structure: **breakout → retest → tiếp tục**.

Logic cốt lõi: khi giá phá resistance, level đó trở thành **support mới**. Nếu giá quay về chạm support mới mà không xuyên thủng → xác suất tiếp tục tăng cao hơn.

---

## 2. Khi nào hoạt động tốt / xấu

### Phù hợp

- Thị trường đã **có trend ngầm** (Higher High / Higher Low).
- **Volume** ổn định — breakout có dòng tiền thật.
- Khung **15m / 1H** — đủ nhanh để retest xảy ra trong vài nến.

### Không phù hợp

- **Range / sideway dài hạn** — breakout liên tục nhưng retest fail ngay.
- **Tin quan trọng** — breakout tin thường one-way, không retest.
- Thị trường **thanh khoản thấp** — giá có thể "xuyên" rồi trôi đi, retest không xảy ra.

---

## 3. Cơ chế toán học / chỉ báo

Strategy dùng **state machine** (máy trạng thái) ẩn trong Pine:

```text
State 0: WAITING — chưa có breakout
State 1: WAITING_RETEST_LONG  — đã phá resistance, đợi giá quay về
State 2: WAITING_RETEST_SHORT — đã phá support, đợi giá quay về
```

Trong code gốc:

- `var float brokenResistance = na` — lưu mức resistance vừa bị phá.
- `var float brokenSupport = na` — lưu mức support vừa bị phá.
- `var bool waitingLongRetest / waitingShortRetest` — cờ trạng thái.

**Điều kiện retest (Long)**:

```text
low  ≤  brokenResistance  +  ATR(14) × 0.2     // chạm hoặc xuyên nhẹ
AND
close > brokenResistance                        // đóng cửa lại trên
```

`ATR × 0.2` là **buffer** cho phép giá xuyên qua level một chút (do slippage, spread, nhiễu) trước khi bật lại. Nếu không có buffer, nhiều retest hợp lệ sẽ bị bỏ sót.

**ATR (Average True Range)** đo biến động trung bình:

```text
TR  = max(high − low, |high − prevClose|, |low − prevClose|)
ATR = SMA(TR, 14)  hoặc  EMA(TR, 14)
```

---

## 4. Tại sao chọn tham số mặc định

|Input|Mặc định|Ý nghĩa|
|---|---|---|
|`lookback`|20|Xác định "structure" của range (HH/HL, LH/LL).|
|`atrLen`|14|Chuẩn phổ biến cho ATR, cân bằng giữa mượt và phản ứng.|
|`atrBuf`|0.2|20% ATR là đủ để chấp nhận nhiễu quanh level, không quá rộng để mất ý nghĩa "chạm".|
|`rr`|2.0|R:R chuẩn.|

**Khi tăng `atrBuf`** → cho phép giá xuyên sâu hơn trước khi tính là retest → bắt được nhiều retest hơn nhưng có thể nhận cả fake breakdown.

**Khi giảm về 0** → chỉ chấp nhận retest khi low chạm đúng level → quá khắt khe.

---

## 5. Luật

### Long

1. `close > resistance` → lưu `brokenResistance = resistance`, bật cờ `waitingLongRetest = true`.
2. Đợi nến tiếp theo: `low ≤ brokenResistance + ATR × 0.2` **AND** `close > brokenResistance`.
3. Entry ở giá đóng cửa nến retest.
4. Reset cờ.

### Short

1. `close < support` → lưu `brokenSupport = support`, bật `waitingShortRetest`.
2. Đợi: `high ≥ brokenSupport − ATR × 0.2` **AND** `close < brokenSupport`.
3. Entry.

### Stop Loss

- Long: dưới **đáy nến retest** (`low`).
- Short: trên **đỉnh nến retest** (`high`).

### Take Profit

**2R**.

---

## 6. Pine Script v6

```pine
//@version=6
strategy("03 - Breakout Retest", overlay=true, pyramiding=0)

lookback = input.int(20, "Structure Lookback", minval=2)
rr       = input.float(2.0, "Risk/Reward", minval=0.1)
atrLen   = input.int(14, "ATR Length")
atrBuf   = input.float(0.2, "ATR Retest Buffer")

resistance = ta.highest(high[1], lookback)
support    = ta.lowest(low[1], lookback)
atr        = ta.atr(atrLen)

var float brokenResistance = na
var float brokenSupport = na
var bool waitingLongRetest = false
var bool waitingShortRetest = false

if close > resistance
    brokenResistance := resistance
    waitingLongRetest := true

if close < support
    brokenSupport := support
    waitingShortRetest := true

longRetest = waitingLongRetest and low <= brokenResistance + atr * atrBuf and close > brokenResistance
shortRetest = waitingShortRetest and high >= brokenSupport - atr * atrBuf and close < brokenSupport

if longRetest
    sl = low
    risk = close - sl
    if risk > 0
        strategy.entry("Long", strategy.long)
        strategy.exit("Long Exit", "Long", stop=sl, limit=close + risk * rr)
    waitingLongRetest := false

if shortRetest
    sl = high
    risk = sl - close
    if risk > 0
        strategy.entry("Short", strategy.short)
        strategy.exit("Short Exit", "Short", stop=sl, limit=close - risk * rr)
    waitingShortRetest := false

plot(resistance, "Resistance")
plot(support, "Support")
```

---

## 7. Ví dụ số (minh hoạ)

Setup: BTCUSDT 1H, `lookback = 20`, `ATR(14) = 50`.

1. Giá tích lũy 5 ngày quanh 29,500–30,000. `resistance = 30,000`.
2. Nến #1: `close = 30,150` → **breakout** lên trên 30,000. Lưu `brokenResistance = 30,000`, bật cờ chờ retest.
3. Hai nến tiếp theo giá đi lên 30,400 rồi quay đầu.
4. Nến #4: `low = 29,990` (chạm/xuyên nhẹ 30,000, trong buffer `30,000 + 50 × 0.2 = 30,010`), `close = 30,080` (> 30,000) → **retest thành công**.
5. Entry = 30,080, SL = `low` = 29,990 → **R = 90**.
6. TP = 30,080 + 2 × 90 = **30,260**.

So với strategy #2 (vào ngay breakout): entry của strategy #3 = 30,080 tốt hơn 30,150 (mua rẻ hơn 70 USD), nhưng phải **đợi thêm vài nến** và có rủi ro giá không retest.

---

## 8. Rủi ro chính & lưu ý chỉnh tham số

### Rủi ro

- **Không bao giờ retest**: giá breakout rồi one-way, không quay lại → bỏ lỡ cơ hội. Cách hạn chế: bật song song strategy #2 để không bỏ lỡ, hoặc đặt timeout (vd: nếu sau 10 nến không retest thì huỷ cờ).
- **Buffer quá rộng**: nếu `atrBuf = 1.0`, "retest" có thể là breakdown thật, SL dễ bị hit.
- **State machine lỗi thời**: nếu một level bị phá 2 lần, code vẫn dùng lần gần nhất — chấp nhận được nhưng cần nhớ khi đọc chart.
- **Whipsaw trong range**: range hẹp dễ sinh breakout giả, retest fail liên tục.

### Lưu ý khi tối ưu

- Nên thêm **timeout** cho cờ `waitingLongRetest` — nếu sau N nến không có retest thì reset cờ (code gốc chưa có, có thể tự thêm).
- Kết hợp với **volume** tăng đột biến lúc breakout sẽ tăng xác suất retest thành công.
- Với khung daily, `atrBuf` nên lớn hơn (0.3–0.5) vì nến daily có biến động rộng.

---

## 9. Timeframe gợi ý & Inputs chính

|Input|Mặc định|Khoảng hợp lý|Ghi chú|
|---|---|---|---|
|`lookback`|20|10–50|Đủ để vẽ HH/HL rõ ràng|
|`atrLen`|14|10–20||
|`atrBuf`|0.2|0.1–0.5|Daily: 0.3–0.5 ; intraday: 0.1–0.2|
|`rr`|2.0|1.5–3.0||
|Timeframe|15m/1H|5m → Daily|Intraday: retest nhanh, daily: retest có thể mất 1–3 ngày|
