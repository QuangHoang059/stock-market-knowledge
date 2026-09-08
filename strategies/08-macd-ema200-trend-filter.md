# 08. MACD + EMA200 Trend Filter

> Pine Script v6 · Trend + momentum · Khung 1H/4H.

---

## 1. Mục đích

Kết hợp **trend filter dài hạn** (EMA200) với **momentum ngắn hạn** (MACD crossover) để chỉ trade theo hướng trend lớn.

Ý tưởng:

- EMA200 = "hướng gió chính" — nếu giá trên EMA200, ưu tiên **Long**; nếu dưới, ưu tiên **Short**.
- MACD crossover = "cơn gió cục bộ" — xác nhận momentum đang hỗ trợ hướng đó.

Chỉ vào lệnh khi **cả hai cùng chiều** — giảm đáng kể tín hiệu ngược trend.

---

## 2. Khi nào hoạt động tốt / xấu

### Phù hợp

- Thị trường có **xu hướng rõ ở khung lớn** (daily, 4H).
- **Crypto top-cap** (BTC, ETH), **chỉ số chứng khoán lớn**, **FX majors** — có "trend lớn" thực sự.
- Khung 1H / 4H cho entry, EMA200 xác định từ daily hoặc 4H.

### Không phù hợp

- **Range dài hạn** quanh EMA200 (giá dao động qua lại EMA200) — MACD cắt lên/xuống liên tục, SL hit.
- **Thị trường penny** — EMA200 không có ý nghĩa thống kê.
- Khi giá quá xa EMA200 (kéo dài > 10%) — pullback về EMA200 sẽ rất sâu, R:R xấu.

---

## 3. Cơ chế toán học / chỉ báo

**EMA200**: trung bình động mũ 200 nến — đại diện "xu hướng dài hạn". Trên khung 4H, 200 nến = ~33 ngày; trên daily = 200 ngày (~10 tháng).

**MACD (Moving Average Convergence Divergence)** đo khoảng cách giữa EMA12 và EMA26:

```text
macdLine  = EMA(close, 12) − EMA(close, 26)
signalLine = EMA(macdLine, 9)
hist      = macdLine − signalLine
```

Khi `macdLine` cắt lên `signalLine` → momentum tăng đang tăng tốc (bullish). Khi histogram > 0 → phe mua chiếm ưu thế rõ.

**Tín hiệu Long**:

```text
close > EMA200                // trend lớn là tăng
ta.crossover(macdLine, signal) // momentum đang tăng tốc
hist > 0                      // xác nhận MACD đã "bullish"
```

**Tín hiệu Short** là đối xứng.

---

## 4. Tại sao chọn tham số mặc định

|Input|Mặc định|Ý nghĩa|
|---|---|---|
|EMA200|200|Chuẩn "trend dài hạn" trong phân tích kỹ thuật.|
|MACD 12/26/9|12, 26, 9|Chuẩn Gerald Appel (tác giả MACD).|
|`rr`|2.0||
|`swingLen`|5|Swing 5 nến cho SL.|

**Tại sao EMA200?** Vì đây là mốc phổ biến nhất các tổ chức theo dõi. EMA100 cũng OK nhưng EMA200 là "điểm phân chia" kinh điển giữa bull / bear market.

**Tại sao cần histogram > 0?** Crossover đơn thuần có thể xảy ra khi MACD vẫn âm → tín hiệu yếu. Histogram > 0 xác nhận MACD đã vượt zero line.

---

## 5. Luật

### Long

1. `close > EMA200`.
2. `MACD cắt lên Signal`.
3. `Histogram > 0`.
4. Entry.

### Short

1. `close < EMA200`.
2. `MACD cắt xuống Signal`.
3. `Histogram < 0`.
4. Entry.

### Stop Loss

- Long: swing low 5 nến.
- Short: swing high 5 nến.

### Take Profit

**2R**.

---

## 6. Pine Script v6

```pine
//@version=6
strategy("08 - MACD + EMA200", overlay=true, pyramiding=0)

ema200 = ta.ema(close, 200)

[macdLine, signalLine, hist] = ta.macd(close, 12, 26, 9)

rr = input.float(2.0, "Risk/Reward")
swingLen = input.int(5, "Swing Length")

longCond = close > ema200 and ta.crossover(macdLine, signalLine) and hist > 0
shortCond = close < ema200 and ta.crossunder(macdLine, signalLine) and hist < 0

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

plot(ema200, "EMA200")
```

---

## 7. Ví dụ số (minh hoạ)

BTCUSDT 4H, giá đang trong uptrend dài hạn từ 25,000 lên 70,000:

|Bar|Close|EMA200|MACD|Signal|Hist|
|---|---|---|---|---|---|
|Bar #1|60,000|45,000|800|750|+50|
|Bar #2|60,500|45,100|850|770|+80|
|Bar #3|61,000|45,200|920|810|+110|
|Bar #4|61,800|45,300|980|850|+130|

Giả sử bar #1 MACD cắt lên Signal (đã xảy ra trước đó). Bar #4 MACD tiếp tục mở rộng, hist > 0:

- Entry = 61,800 (giả định tín hiệu mới ở bar này)
- SL = swing low 5 nến = 60,000 → **R = 1,800**
- TP = 61,800 + 2 × 1,800 = **65,400**

---

## 8. Rủi ro chính & lưu ý chỉnh tham số

### Rủi ro

- **EMA200 lag rất lớn**: trong downtrend, EMA200 phản ứng chậm → vào Short **sau khi giá đã giảm nhiều**, R:R thực tế xấu.
- **EMA200 bị xuyên liên tục trong range**: tín hiệu nhiễu.
- **MACD whipsaw**: ở khung nhỏ (15m), MACD cắt lên/xuống liên tục → kết hợp EMA200 không giúp được nhiều.
- **EMA200 tính trên timeframe hiện tại** có ý nghĩa khác nhau: trên 1H, 200 nến = ~8 ngày; trên Daily = 200 ngày. Cần đảm bảo timeframe **đủ lớn** để EMA200 thực sự là trend filter.

### Lưu ý khi tối ưu

- **Multi-timeframe**: tính EMA200 trên Daily, MACD trên 4H → 4H dùng EMA200 của daily. Cách này giữ trend filter ổn định dù trade trên khung nhỏ hơn.
- Có thể thay EMA200 bằng **EMA100** cho tín hiệu nhanh hơn (rủi ro lag ít hơn).
- Kết hợp **volume**: chỉ trade khi volume tăng khi MACD cross → tăng xác suất.

---

## 9. Timeframe gợi ý & Inputs chính

|Input|Mặc định|Khoảng hợp lý|Ghi chú|
|---|---|---|---|
|EMA200|200|100–200|100 cho swing, 200 cho position|
|MACD|12, 26, 9|8/17/9 hoặc 5/35/5|Có thể thay cho crypto|
|`rr`|2.0|1.5–3.0||
|`swingLen`|5|3–10||
|Timeframe|1H/4H|4H → Daily|1H nhiễu, Daily ít tín hiệu|
