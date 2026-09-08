# 05. RSI + Bollinger Bands Mean Reversion

> Pine Script v6 · Mean reversion · Khung 15m/1H.

---

## 1. Mục đích

Đây là chiến lược **mean reversion** (giá sẽ quay về trung bình) — **ngược với tất cả strategies trước** (đều theo trend hoặc breakout).

Ý tưởng: khi giá vượt ra ngoài Bollinger Band **kèm RSI extreme** → giá đã "over-extend" và **nhiều khả năng quay về**.

---

## 2. Khi nào hoạt động tốt / xấu

### Phù hợp

- Thị trường **sideway / range** rõ rệt.
- **Crypto altcoin / penny stock** dễ pump-dump tạo RSI cực trị rồi revert.
- Khung 15m / 1H — đủ nhanh để tận dụng swing trong range.

### Không phù hợp

- **Trending mạnh**: giá xuyên band rồi đi tiếp, không revert → SL hit.
- **Tin quan trọng**: breakout tin có thể đẩy RSI > 90 trong nhiều giờ, không revert.
- **Thị trường kém thanh khoản**: RSI/BB có thể cho tín hiệu sai do spread lớn.

---

## 3. Cơ chế toán học / chỉ báo

**Bollinger Bands** (BB) — dải biến động quanh SMA:

```text
basis = SMA(close, 20)
dev   = stdev(close, 20) × 2
upper = basis + dev
lower = basis − dev
```

Mặc định `bbMult = 2.0` nghĩa là dải BB bao phủ ~95% giá trong điều kiện phân phối chuẩn. Giá chạm/đóng trên `upper` hoặc dưới `lower` = "extreme".

**RSI (Relative Strength Index)** — đo tốc độ và biên độ thay đổi giá:

```text
gain = max(close − close[1], 0)
loss = max(close[1] − close, 0)
RS   = EMA(gain, 14) / EMA(loss, 14)
RSI  = 100 − 100 / (1 + RS)
```

RSI < 30 = oversold, RSI > 70 = overbought. Hai ngưỡng này **là heuristic**, không phải định luật.

**Tín hiệu Long (mean reversion từ oversold)**:

```text
close[1]  < lower[1]   // nến trước đóng dưới band dưới
AND
rsi[1]    < 30         // RSI vùng oversold
AND
close     > lower      // hiện tại đã đóng cửa quay lại trong band
```

Giá đã oversold rồi **bật ngược lên vào band** — entry khi xác suất revert cao.

**Tín hiệu Short** là đối xứng.

---

## 4. Tại sao chọn tham số mặc định

|Input|Mặc định|Ý nghĩa|
|---|---|---|
|`bbLen`|20|Chuẩn Bollinger Bands — vừa đủ mượt.|
|`bbMult`|2.0|95% phân phối chuẩn. Tăng lên 2.5 — ít tín hiệu nhưng extreme hơn.|
|`rsiLen`|14|Chuẩn phổ biến của Wilder (tác giả RSI).|
|`rr`|1.5|TP **1.5R** (thấp hơn trend strategies) vì mean reversion thường diễn ra nhanh, không kỳ vọng trend dài.|

**Khi giảm `bbMult`** → band hẹp hơn → nhiều tín hiệu extreme (nhưng kém ý nghĩa).

**Khi tăng `rsiLen`** → RSI mượt hơn → ít tín hiệu oversold/overbought.

---

## 5. Luật

### Long

1. Nến trước: `close[1] < lower[1]` (đóng dưới band dưới).
2. Nến trước: `rsi[1] < 30` (oversold).
3. Hiện tại: `close > lower` (quay lại trong band).
4. Entry.

### Short

1. `close[1] > upper[1]`.
2. `rsi[1] > 70`.
3. `close < upper`.
4. Entry.

### Stop Loss

Swing low/high 5 nến.

### Take Profit

**1.5R**.

---

## 6. Pine Script v6

```pine
//@version=6
strategy("05 - RSI Bollinger Mean Reversion", overlay=true, pyramiding=0)

bbLen = input.int(20, "BB Length")
bbMult = input.float(2.0, "BB Multiplier")
rsiLen = input.int(14, "RSI Length")
rr = input.float(1.5, "Risk/Reward")

basis = ta.sma(close, bbLen)
dev = ta.stdev(close, bbLen) * bbMult
upper = basis + dev
lower = basis - dev

rsi = ta.rsi(close, rsiLen)

longCond = close[1] < lower[1] and rsi[1] < 30 and close > lower
shortCond = close[1] > upper[1] and rsi[1] > 70 and close < upper

if longCond
    sl = ta.lowest(low, 5)
    risk = close - sl
    if risk > 0
        strategy.entry("Long", strategy.long)
        strategy.exit("Long Exit", "Long", stop=sl, limit=close + risk * rr)

if shortCond
    sl = ta.highest(high, 5)
    risk = sl - close
    if risk > 0
        strategy.entry("Short", strategy.short)
        strategy.exit("Short Exit", "Short", stop=sl, limit=close - risk * rr)

plot(basis, "BB Basis")
plot(upper, "BB Upper")
plot(lower, "BB Lower")
```

---

## 7. Ví dụ số (minh hoạ)

ETHUSDT 1H, giá dao động trong range 3,200–3,400:

|Chỉ số|Giá trị|
|---|---|
|SMA(20)|3,300|
|StdDev(20)|40|
|Lower band|3,300 − 40 × 2 = 3,220|
|Upper band|3,300 + 40 × 2 = 3,380|

Giả sử giá giảm mạnh trong 3 nến:

- Nến #1: close = 3,180 → `close < lower = 3,220`
- RSI(14) = 25 → < 30
- Nến #2: open thấp, low = 3,150, close = 3,260 → `close > lower = 3,220`
- → **Tín hiệu Long** ở nến #2, entry = 3,260.
- SL = `ta.lowest(low, 5)` = 3,150 → **R = 110**.
- TP = 3,260 + 1.5 × 110 = **3,425**.

Giá 3,425 vẫn trong range hợp lý — kỳ vọng TP hit trong vài nến.

---

## 8. Rủi ro chính & lưu ý chỉnh tham số

### Rủi ro

- **Trending kill mean reversion**: nếu thị trường bắt đầu trending sau khi bạn vào lệnh, giá tiếp tục xuyên band → SL hit. **Đây là rủi ro lớn nhất** của mean reversion.
- **BB và RSI cùng extreme nhưng giá vẫn giảm**: trong panic dump, RSI có thể giữ < 30 trong nhiều giờ.
- **Whipsaw trong range hẹp**: nhiều tín hiệu liên tiếp, phí giao dịch ăn lợi nhuận.
- **RR thấp (1.5R)** → cần win rate cao (~45%+) để có expectancy dương.

### Lưu ý khi tối ưu

- **Kết hợp trend filter**: chỉ trade mean reversion khi ADX < 25 (thị trường đang range). Khi ADX > 25, hãy tắt strategy này.
- Có thể thêm **điều kiện volume khôi phục** lúc entry (volume tăng khi giá bật ngược lên) để xác nhận.
- Với crypto, RSI 25/75 có thể tốt hơn 30/70 vì crypto biến động mạnh hơn.

---

## 9. Timeframe gợi ý & Inputs chính

|Input|Mặc định|Khoảng hợp lý|Ghi chú|
|---|---|---|---|
|`bbLen`|20|14–30||
|`bbMult`|2.0|1.8–2.5|Range hẹp: 1.8 ; trending: 2.5|
|`rsiLen`|14|7–21|7 cho nhanh, 21 cho mượt|
|`rr`|1.5|1.0–2.0|Mean reversion thường TP gần band đối diện|
|Timeframe|15m/1H|5m → 4H|Trending mạnh: tránh dùng|
