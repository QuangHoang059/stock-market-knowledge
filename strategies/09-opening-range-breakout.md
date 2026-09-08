# 09. Opening Range Breakout (ORB)

> Pine Script v6 · Intraday breakout · Session-based.

---

## 1. Mục đích

**Opening Range** = high / low của **N phút đầu phiên** (thường 5–30 phút). Nhiều trader chuyên nghiệp dùng range này làm **"khung giá công bằng"** cho cả ngày.

Chiến lược: đợi giá phá khỏi opening range sau khi range hình thành, vào lệnh theo hướng phá.

Phù hợp với cổ phiếu Mỹ (NYSE/Nasdaq mở 09:30 ET) hoặc các sàn có session rõ ràng.

---

## 2. Khi nào hoạt động tốt / xấu

### Phù hợp

- **Cổ phiếu Mỹ** có volume cao, có "momentum open" (gap lên/xuống).
- **Crypto futures** trên sàn có session chính (CME futures, Binance perp).
- Ngày có **tin quan trọng** (FOMC, CPI, earnings lớn) — thường tạo breakout mạnh từ opening range.
- Khung 5m / 15m với opening range 15 phút.

### Không phù hợp

- **Cổ phiếu penny / low volume** — opening range bị nhiễu.
- **Phiên không có catalyst** → ORB thường fail, giá quay về giữa range.
- **Thị trường 24/7** không có session rõ ràng (spot crypto) — cần tự định nghĩa "session".

---

## 3. Cơ chế toán học / chỉ báo

**Xác định Opening Range**:

```text
inOR  = nến hiện tại nằm trong session đã định (vd: 09:30–09:45 ET)
orHigh = max(high)  trong các nến inOR
orLow  = min(low)   trong các nến inOR
```

Sau khi session kết thúc → `rangeReady = true`.

**Tín hiệu**:

```text
long  = close > orHigh  AND  close[1] <= orHigh   // phá lên trên OR High
short = close < orLow   AND  close[1] >= orLow    // phá xuống dưới OR Low
```

Điều kiện `close[1] <= orHigh` đảm bảo đây là **breakout mới**, không phải nến vẫn đang trong range.

Trong Pine, session kiểm tra bằng `time(timeframe.period, "0930-0945")` trả về timestamp hoặc `na`. `not na(...)` nghĩa là đang trong session.

---

## 4. Tại sao chọn tham số mặc định

|Input|Mặc định|Ý nghĩa|
|---|---|---|
|`sessionInput`|"0930-0945"|15 phút đầu phiên NYSE. Cần sửa theo thị trường (vd: crypto 00:00–00:15 UTC).|
|`rr`|2.0|R:R 2R tiêu chuẩn.|

**Tại sao 15 phút?** Là khung phổ biến nhất — đủ dài để giá hình thành range có ý nghĩa, đủ ngắn để breakout trong ngày. Có thể dùng 5m (quá nhạy) hoặc 30m (quá trễ).

---

## 5. Luật

### Long

1. Xác định OR High / OR Low trong 15 phút đầu phiên.
2. `close > OR High` **AND** `close[1] <= OR High` (phá mới).
3. Entry.

### Short

1. `close < OR Low` **AND** `close[1] >= OR Low`.
2. Entry.

### Stop Loss

- Long: **OR Low** (ngược range).
- Short: **OR High**.

### Take Profit

**2R**.

---

## 6. Pine Script v6

```pine
//@version=6
strategy("09 - Opening Range Breakout", overlay=true, pyramiding=0)

sessionInput = input.session("0930-0945", "Opening Range")
rr = input.float(2.0, "Risk/Reward")

inOR = not na(time(timeframe.period, sessionInput))

var float orHigh = na
var float orLow = na
var bool rangeReady = false

newDay = ta.change(time("D")) != 0

if newDay
    orHigh := na
    orLow := na
    rangeReady := false

if inOR
    orHigh := na(orHigh) ? high : math.max(orHigh, high)
    orLow := na(orLow) ? low : math.min(orLow, low)

if not inOR and not na(orHigh) and not na(orLow)
    rangeReady := true

longCond = rangeReady and close > orHigh and close[1] <= orHigh
shortCond = rangeReady and close < orLow and close[1] >= orLow

if longCond
    risk = close - orLow
    if risk > 0
        strategy.entry("Long", strategy.long)
        strategy.exit("Long Exit", "Long", stop=orLow, limit=close + risk * rr)

if shortCond
    risk = orHigh - close
    if risk > 0
        strategy.entry("Short", strategy.short)
        strategy.exit("Short Exit", "Short", stop=orHigh, limit=close - risk * rr)

plot(orHigh, "OR High")
plot(orLow, "OR Low")
```

---

## 7. Ví dụ số (minh hoạ)

AAPL phiên 09/03/2025:

- 09:30–09:45 ET: high = 180.50, low = 179.20 → OR High = 180.50, OR Low = 179.20.
- Range rộng = 1.30 USD.
- 09:50: nến mở 180.00, đóng 181.20 → close > OR High (180.50), close[1] = 180.00 ≤ 180.50 → **breakout Long**.
- Entry = 181.20
- SL = OR Low = 179.20 → **R = 2.00**
- TP = 181.20 + 2 × 2.00 = **185.20**

Trong phiên tiếp theo AAPL thường hit target hoặc gần target trước giờ đóng cửa.

---

## 8. Rủi ro chính & lưu ý chỉnh tham số

### Rủi ro

- **Fake breakout**: giá phá OR trong vài phút rồi quay lại range → "stop hunt" kinh điển.
- **Range quá rộng** (volatile open): R lớn, TP xa → có thể hit SL trước khi hit TP.
- **Range quá hẹp**: breakout dễ, nhưng target gần → không đáng risk.
- **Cần chỉnh session theo từng thị trường**: NYSE 09:30 ET, crypto có thể 00:00 UTC hoặc 09:00 UTC theo Asia session, CME futures 18:00 ET (rollover).
- **Holiday / half-day**: NYSE đóng cửa sớm ngày lễ → opening range có thể không hợp lệ.

### Lưu ý khi tối ưu

- Kết hợp **volume** tăng khi breakout — tăng xác suất thật.
- Có thể chờ **retest** OR High/Low sau breakout (giống strategy #3) để entry tốt hơn.
- Có thể thêm **filter giờ** chỉ trade trong 30 phút sau khi range hình thành, tránh breakout cuối phiên.

---

## 9. Timeframe gợi ý & Inputs chính

|Input|Mặc định|Khoảng hợp lý|Ghi chú|
|---|---|---|---|
|`sessionInput`|"0930-0945"|tuỳ thị trường|NYSE: 0930-0945; Crypto perp CME: 1800-1815; FX London: 0800-0815|
|`rr`|2.0|1.5–3.0||
|Timeframe|5m/15m|1m → 30m|1m quá nhiễu, 30m quá trễ|
