# 06. Bollinger Squeeze Breakout

> Pine Script v6 · Volatility breakout · Khung 15m/1H.

---

## 1. Mục đích

**Squeeze** trong Bollinger Bands = khoảng cách giữa upper/lower band **thu hẹp** đáng kể so với trung bình — dấu hiệu thị trường đang **"nén" năng lượng** trước khi bung một biến động lớn.

Chiến lược này **chờ squeeze xảy ra** rồi vào lệnh theo hướng breakout (phá upper/lower band) **kèm volume xác nhận**.

---

## 2. Khi nào hoạt động tốt / xấu

### Phù hợp

- **Trước các sự kiện lớn**: FOMC, earnings, token unlock — thị trường tích lũy trước tin rồi bùng nổ khi tin ra.
- **Range consolidation dài**: ít nhất vài chục nến đi ngang.
- Có **volume tăng** khi breakout (xác nhận dòng tiền).

### Không phù hợp

- **Squeeze giả**: range hẹp nhưng tin không ra, giá tiếp tục đi ngang thêm.
- **Whipsaw sau breakout**: giá phá band rồi quay lại ngay.
- Thị trường **chết** (volume cực thấp, không ai quan tâm) — squeeze có thể kéo dài vô tận.

---

## 3. Cơ chế toán học / chỉ báo

**Bollinger Bands width** đo biến động tương đối:

```text
width   = (upper − lower) / basis
avgWidth = SMA(width, 50)
squeeze  = width < avgWidth × 0.8
```

Hệ số `0.8` nghĩa là BB hiện tại **hẹp hơn 80% trung bình 50 nến** = đang squeeze. Có thể chỉnh thành 0.6 (rất chặt) hoặc 1.0 (rất lỏng).

**Volume confirmation**:

```text
volOK = volume > SMA(volume, 20) × 1.5
```

**Tín hiệu**:

```text
long  = squeeze[1] (squeeze hình thành nến trước)  AND  close > upper  AND  volOK
short = squeeze[1]                                   AND  close < lower AND  volOK
```

Điều kiện `squeeze[1]` đảm bảo squeeze **đã có** trước khi breakout, không phải đang hình thành.

---

## 4. Tại sao chọn tham số mặc định

|Input|Mặc định|Ý nghĩa|
|---|---|---|
|`bbLen`|20|Cửa sổ tính BB & width.|
|`bbMult`|2.0|Độ rộng band chuẩn.|
|`widthLen`|50|Đủ dài để avgWidth ổn định, không quá nhạy với regime ngắn hạn.|
|`volLen`|20|So sánh volume hiện tại với nền gần.|
|`volMult`|1.5|Ngưỡng "thanh khoản bất thường".|
|`rr`|2.0||

**Khi tăng `widthLen`** → so sánh với regime dài hơn → squeeze phải rõ ràng hơn.

**Khi giảm hệ số squeeze từ 0.8 xuống 0.6** → chỉ bắt squeeze rất chặt → ít tín hiệu nhưng breakout nổ mạnh hơn.

---

## 5. Luật

1. BB width < 80% trung bình 50 nến (squeeze nến trước).
2. Giá phá upper band + volume > 1.5× MA → **Long**.
3. Giá phá lower band + volume > 1.5× MA → **Short**.
4. SL đặt ở **vùng tích lũy** trước squeeze (lowest low / highest high 10 nến).
5. TP **2R**.

---

## 6. Pine Script v6

```pine
//@version=6
strategy("06 - Bollinger Squeeze Breakout", overlay=true, pyramiding=0)

bbLen = input.int(20, "BB Length")
bbMult = input.float(2.0, "BB Multiplier")
widthLen = input.int(50, "Width Average")
volLen = input.int(20, "Volume MA")
volMult = input.float(1.5, "Volume Multiplier")
rr = input.float(2.0, "Risk/Reward")

basis = ta.sma(close, bbLen)
dev = ta.stdev(close, bbLen) * bbMult
upper = basis + dev
lower = basis - dev

width = (upper - lower) / basis
avgWidth = ta.sma(width, widthLen)

squeeze = width < avgWidth * 0.8
volOK = volume > ta.sma(volume, volLen) * volMult

longCond = squeeze[1] and close > upper and volOK
shortCond = squeeze[1] and close < lower and volOK

if longCond
    sl = ta.lowest(low, 10)
    risk = close - sl
    if risk > 0
        strategy.entry("Long", strategy.long)
        strategy.exit("Long Exit", "Long", stop=sl, limit=close + risk * rr)

if shortCond
    sl = ta.highest(high, 10)
    risk = sl - close
    if risk > 0
        strategy.entry("Short", strategy.short)
        strategy.exit("Short Exit", "Short", stop=sl, limit=close - risk * rr)

plot(basis, "Basis")
plot(upper, "Upper")
plot(lower, "Lower")
```

---

## 7. Ví dụ số (minh hoạ)

TSLA 1H, đang consolidation trước earnings:

- Giá dao động 250–255 suốt 30 giờ, BB rất hẹp.
- `basis = 252.5`, `width = (256 − 249) / 252.5 = 0.028`, `avgWidth = 0.045` → squeeze = `0.028 < 0.045 × 0.8 = 0.036`.
- Sau earnings: nến mở cửa tăng mạnh, `close = 262`, `volume = 8M` > `volMA × 1.5 = 6M`.
- → **Long** tại 262.
- SL = `ta.lowest(low, 10)` = 248 → **R = 14**.
- TP = 262 + 2 × 14 = **290**.

Biến động sau earnings có thể đẩy giá ±5–10% → TP 290 hoàn toàn khả thi.

---

## 8. Rủi ro chính & lưu ý chỉnh tham số

### Rủi ro

- **Squeeze kéo dài**: thị trường tiếp tục consolidation → không có tín hiệu → cơ hội nằm im.
- **Breakout một chiều rồi đảo chiều**: phá upper rồi quay về lower trong vài nến (rare nhưng có thể xảy ra sau earnings "buy the rumor, sell the news").
- **Volume không tăng khi breakout**: có squeeze nhưng phá band mà volume không cao → khả năng fake breakout.
- **SL bị hit ngay khi breakout**: vùng tích lũy rộng → R lớn → cần TP xa hơn.

### Lưu ý khi tối ưu

- Có thể thêm **TEMA** (Triple EMA) hoặc **Keltner Channels** để định nghĩa squeeze chuẩn hơn (TTM Squeeze dùng Keltner thay vì SMA BB width).
- Tăng `widthLen` lên 100 để so sánh với regime dài hơn — phù hợp với swing trade.
- Tránh trade squeeze trong giờ thị trường thanh khoản thấp.

---

## 9. Timeframe gợi ý & Inputs chính

|Input|Mặc định|Khoảng hợp lý|Ghi chú|
|---|---|---|---|
|`bbLen`|20|14–30||
|`bbMult`|2.0|1.5–2.5||
|`widthLen`|50|30–100|Dài hơn — squeeze chuẩn hơn|
|`volLen`|20|10–50||
|`volMult`|1.5|1.2–3.0|Crypto: 2.0+|
|`rr`|2.0|1.5–4.0|Sau tin, có thể RR cao hơn (vd: 3) với trailing stop|
|Timeframe|15m/1H|5m → Daily|Daily squeeze hiếm nhưng breakout rất mạnh|
