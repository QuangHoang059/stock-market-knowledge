# 02. Resistance/Support Breakout + Volume

> Pine Script v6 · Breakout · Volume confirmation.

---

## 1. Mục đích

Bắt **breakout khỏi vùng tích lũy** (range/consolidation) khi:

1. Giá phá **resistance** (hoặc **support**) đã hình thành trong N nến trước.
2. Khối lượng **đột biến** vượt ngưỡng trung bình → xác nhận "tiền thật" đẩy giá, không phải nhiễu.

Volume filter là chìa khoá phân biệt breakout thật với fakeout.

---

## 2. Khi nào hoạt động tốt / xấu

### Phù hợp

- Sau một giai đoạn **sideway rõ rệt** (range hẹp, EMA xếp ngang, ATR thấp).
- Thị trường có **volume profile ổn định** (crypto, futures, cổ phiếu mid/large cap).
- Khung 15m (intraday) hoặc 1H (swing).

### Không phù hợp

- **Gap đầu phiên** (mở cửa) — nến đầu tiên hay có volume spike giả do spread lớn, breakout sáng thường fail.
- **Thị trường thanh khoản thấp** (cổ phiếu penny, token ít volume) — bất kỳ lệnh nào cũng đẩy giá, "volume" không phản ánh dòng tiền thật.
- **Tin quan trọng sắp ra** → breakout xảy ra trước tin có thể bị hút ngược (stop hunt).

---

## 3. Cơ chế toán học / chỉ báo

**Resistance / Support** được xác định bằng **rolling high / low** của N nến **trước đó** (loại trừ nến hiện tại để tránh lookahead):

```text
resistance[n] = max(high[i])  với i = n+1 .. n+lookback
support[n]    = min(low[i])   với i = n+1 .. n+lookback
```

Trong Pine Script dùng `ta.highest(high[1], lookback)` — `[1]` nghĩa là lấy high **của nến trước**, loại trừ high nến hiện tại.

**Volume MA** là SMA của `volume`:

```text
volMA = SMA(volume, volLen)
```

**Tín hiệu breakout + volume**:

```text
long  = close > resistance  AND  volume > volMA × volMult
short = close < support     AND  volume > volMA × volMult
```

`volMult = 1.5` là ngưỡng phổ biến — volume > 1.5× trung bình = thanh khoản bất thường, có thể là dòng tiền lớn tham gia.

---

## 4. Tại sao chọn tham số mặc định

|Input|Mặc định|Ý nghĩa|
|---|---|---|
|`lookback`|20|Đủ dài để xác định một "vùng tích lũy" thực sự (trên 15m: ~5 giờ, trên 1H: gần 1 ngày).|
|`volLen`|20|Tương ứng cùng cửa sổ — so sánh volume hiện tại với nền 20 nến.|
|`volMult`|1.5|1.5× trung bình là mức "đáng kể" nhưng không quá hiếm (≈ top 10–20% nến).|
|`rr`|2.0|Cân bằng R:R chuẩn cho breakout.|

**Khi tăng `lookback`** → resistance/support "xa hơn" → ít breakout hơn nhưng breakout nào cũng quan trọng hơn.

**Khi giảm** → nhiều tín hiệu nhưng dễ bị breakout giả trong nhiễu ngắn hạn.

**Khi tăng `volMult`** → lọc chặt hơn, ít tín hiệu nhưng chất lượng cao.

---

## 5. Luật

### Long

1. `resistance = highest(high[1], lookback)`.
2. `close > resistance` (giá đóng cửa phá lên trên).
3. `volume > volMA × volMult` (xác nhận thanh khoản).
4. Entry ở giá đóng cửa nến tín hiệu.

### Short

1. `support = lowest(low[1], lookback)`.
2. `close < support`.
3. `volume > volMA × volMult`.
4. Entry ở giá đóng cửa nến tín hiệu.

### Stop Loss

- Long: dưới **đáy nến breakout** (`low` của nến tín hiệu).
- Short: trên **đỉnh nến breakout** (`high` của nến tín hiệu).

### Take Profit

**2R**.

---

## 6. Pine Script v6

```pine
//@version=6
strategy("02 - Breakout + Volume", overlay=true, pyramiding=0)

lookback = input.int(20, "Breakout Lookback", minval=2)
volLen   = input.int(20, "Volume MA")
volMult  = input.float(1.5, "Volume Multiplier", minval=0.1)
rr       = input.float(2.0, "Risk/Reward", minval=0.1)

resistance = ta.highest(high[1], lookback)
support    = ta.lowest(low[1], lookback)
volMA      = ta.sma(volume, volLen)

longCond  = close > resistance and volume > volMA * volMult
shortCond = close < support and volume > volMA * volMult

if longCond
    sl = low
    risk = close - sl
    if risk > 0
        strategy.entry("Long", strategy.long)
        strategy.exit("Long Exit", "Long", stop=sl, limit=close + risk * rr)

if shortCond
    sl = high
    risk = sl - close
    if risk > 0
        strategy.entry("Short", strategy.short)
        strategy.exit("Short Exit", "Short", stop=sl, limit=close - risk * rr)

plot(resistance, "Resistance")
plot(support, "Support")
```

---

## 7. Ví dụ số (minh hoạ)

Giả sử BTCUSDT 15m, `lookback = 20`:

|Chỉ số|Giá trị|
|---|---|
|`resistance` (cao nhất 20 nến trước)|30,000|
|`support` (thấp nhất 20 nến trước)|29,200|
|`volMA` (SMA volume 20 nến)|1,000 BTC|
|`volMult`|1.5 — ngưỡng = 1,500 BTC|

Các nến gần nhất dao động 29,300–29,950, không phá 30,000. Đến một nến:

- `high = 30,120`, `low = 29,980`, `close = 30,080` → phá resistance 30,000.
- `volume = 2,200 BTC` > 1,500 → đủ điều kiện volume.
- → **Long** entry = 30,080.
- SL = `low` của nến = 29,980 → **R = 30,080 − 29,980 = 100**.
- TP = 30,080 + 2 × 100 = **30,280**.

Nếu giá chạm 30,280, lời 2R. Nếu quay về 29,980, lỗ 1R.

---

## 8. Rủi ro chính & lưu ý chỉnh tham số

### Rủi ro

- **Fakeout / bull trap**: giá phá level rồi quay lại ngay trong vài nến. Cách hạn chế: chờ nến xác nhận đóng cửa (đã làm) hoặc kết hợp với strategy #3 (Breakout + Retest).
- **Volume "ảo"**: trong một số sàn, wash trading làm volume cao bất thường. Luôn kiểm tra trên sàn uy tín.
- **Resistance/support cũ đã cũ**: `lookback = 20` chỉ phản ánh vùng gần nhất. Có những level quan trọng từ 100 nến trước mà strategy này bỏ qua.
- **Whipsaw khi range hẹp**: nếu `resistance` và `support` quá gần, breakout xảy ra liên tục, phí giao dịch sẽ ăn hết lợi nhuận.

### Lưu ý khi tối ưu

- Có thể thêm filter ADX > 25 để đảm bảo đang có momentum, không phải noise.
- Với crypto, nên tăng `volMult` lên 2.0 vì volume spike ở crypto rất phổ biến.
- Với cổ phiếu thanh khoản thấp, `lookback` nên nhỏ (10) để resistance/support cập nhật thường xuyên.

---

## 9. Timeframe gợi ý & Inputs chính

|Input|Mặc định|Khoảng hợp lý|Ghi chú|
|---|---|---|---|
|`lookback`|20|10–50|10 cho intraday, 50 cho swing dài|
|`volLen`|20|10–50|Nên bằng `lookback` để so sánh công bằng|
|`volMult`|1.5|1.2–3.0|Crypto: 2.0+ ; cổ phiếu lớn: 1.5|
|`rr`|2.0|1.5–3.0||
|Timeframe|15m/1H|5m → 4H|Khung càng nhỏ càng nhiều tín hiệu giả|
