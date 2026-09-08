# 07. VWAP Pullback

> Pine Script v6 · Intraday trend · VWAP.

---

## 1. Mục đích

VWAP (Volume-Weighted Average Price) là "giá trung bình có trọng số theo khối lượng" của **phiên hiện tại** — phản ánh "giá công bằng" mà các tổ chức tham chiếu.

Chiến lược này dùng VWAP như **dynamic support/resistance trong phiên**:

- Uptrend intraday: giá pullback về VWAP rồi bật lên → Long.
- Downtrend intraday: pullback lên VWAP rồi bật xuống → Short.

---

## 2. Khi nào hoạt động tốt / xấu

### Phù hợp

- **Intraday** (5m / 15m) trên thị trường có thanh khoản cao: futures (ES, NQ), crypto (BTC, ETH), FX majors.
- Phiên có **xu hướng rõ** (London / NY session mở).
- Volume lớn — VWAP phản ánh dòng tiền thật.

### Không phù hợp

- **Multi-day**: VWAP reset mỗi phiên → không có ý nghĩa qua đêm.
- **Cổ phiếu penny** ít volume: VWAP bị nhiễu.
- **Tin quan trọng giữa phiên**: VWAP "nhảy" do spike volume, ý nghĩa dynamic support mất đi.

---

## 3. Cơ chế toán học / chỉ báo

**VWAP** tích luỹ `hlc3 × volume` rồi chia cho tổng volume kể từ đầu phiên:

```text
VWAP = Σ(hlc3 × volume) / Σ(volume), tính từ đầu phiên
```

Trong Pine v6, `ta.vwap(hlc3)` tự động reset theo **session** (theo symbol — thường là ngày). Một số sàn/equity reset theo NYSE session 09:30–16:00 ET, crypto có thể theo UTC 00:00.

**Tín hiệu Long** (pullback trong uptrend intraday):

```text
close > VWAP            // giá đang trên VWAP
VWAP > VWAP[1]          // VWAP đang tăng — phe mua chiếm ưu thế trong phiên
low   ≤ VWAP            // pullback chạm VWAP
close > VWAP            // bật lên trên VWAP
```

**Tín hiệu Short** là đối xứng (giá dưới VWAP + VWAP giảm + high chạm VWAP + đóng cửa dưới).

---

## 4. Tại sao chọn tham số mặc định

|Input|Mặc định|Ý nghĩa|
|---|---|---|
|`rr`|1.5|TP 1.5R — phù hợp với intraday (target thường gần).|
|`swingLen`|5|SL theo swing 5 nến — trên 5m tương đương 25 phút.|
|VWAP source|`hlc3`|Trung bình (high + low + close) / 3 — phổ biến nhất.|

**Tại sao RR = 1.5 (thấp hơn 2R của các strategy khác)?** Intraday trend thường diễn ra trong vài giờ, target hợp lý không quá xa. Kỳ vọng win rate cao hơn (~50%+) để bù RR thấp.

---

## 5. Luật

### Long

1. `close > VWAP`.
2. `VWAP > VWAP[1]` (VWAP tăng).
3. `low ≤ VWAP` (pullback chạm VWAP).
4. `close > VWAP` (bật lên).
5. Entry ở giá đóng cửa nến tín hiệu.

### Short

1. `close < VWAP`.
2. `VWAP < VWAP[1]` (VWAP giảm).
3. `high ≥ VWAP` (pullback chạm VWAP).
4. `close < VWAP` (bật xuống).
5. Entry.

### Stop Loss

- Long: swing low 5 nến (`ta.lowest(low, swingLen)`).
- Short: swing high 5 nến (`ta.highest(high, swingLen)`).

### Take Profit

**1.5R**.

---

## 6. Pine Script v6

```pine
//@version=6
strategy("07 - VWAP Pullback", overlay=true, pyramiding=0)

rr = input.float(1.5, "Risk/Reward")
swingLen = input.int(5, "Swing Length")

vwap = ta.vwap(hlc3)

longCond = close > vwap and vwap > vwap[1] and low <= vwap and close > vwap
shortCond = close < vwap and vwap < vwap[1] and high >= vwap and close < vwap

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

plot(vwap, "VWAP")
```

---

## 7. Ví dụ số (minh hoạ)

ES futures 5m phiên NY, BTC-like symbol. Phiên bắt đầu 09:30 ET:

|Nến|Close|VWAP|Low|Quan sát|
|---|---|---|---|---|
|09:30|4,500|4,500|4,495|Open|
|09:35|4,510|4,503|4,502|Giá trên VWAP, VWAP tăng|
|09:40|4,520|4,510|4,512|Uptrend hình thành|
|09:45|4,508|4,512|4,505|Low = 4,505 ≤ VWAP = 4,512 — pullback|
|09:50|4,518|4,514|4,510|Close = 4,518 > VWAP = 4,514 — bật lên|

Tín hiệu Long ở nến 09:50.

- Entry = 4,518
- SL = `ta.lowest(low, 5)` = 4,500 (nến 09:30) → **R = 18**
- TP = 4,518 + 1.5 × 18 = **4,545**

ES thường hit target trong vòng 1–2 giờ tiếp theo.

---

## 8. Rủi ro chính & lưu ý chỉnh tham số

### Rủi ro

- **VWAP bị "xuyên" trong ranging session**: giá dao động qua lại VWAP liên tục → whipsaw. Cách hạn chế: thêm filter ADX > 20.
- **Phiên có tin quan trọng**: VWAP có thể "nhảy" 50–100 points trong 1 phút, mọi pullback cũ trở nên vô nghĩa.
- **Cuối phiên**: VWAP hành vi khác (volume giảm, spread rộng) → tránh trade sau 15:30 ET với US equity.
- **Crypto 24/7**: cần xác định "session" cho VWAP (UTC 00:00 hay theo Asia/US session?).

### Lưu ý khi tối ưu

- Kết hợp **VWAP + EMA9** trên khung 5m: VWAP cho context phiên, EMA9 cho momentum cục bộ.
- Có thể dùng **anchored VWAP** (aVWAP) thay vì session VWAP — neo VWAP vào một swing high/low quan trọng.
- Tăng `swingLen` lên 8–10 cho khung 1m (5 nến quá ngắn, dễ bị noise quét SL).

---

## 9. Timeframe gợi ý & Inputs chính

|Input|Mặc định|Khoảng hợp lý|Ghi chú|
|---|---|---|---|
|`rr`|1.5|1.0–2.5|Intraday target thường gần|
|`swingLen`|5|3–10|1m: 8–10 ; 5m: 5 ; 15m: 3–5|
|VWAP source|`hlc3`|`hlc3` / `close`|`hlc3` chuẩn hơn|
|Timeframe|5m/15m|1m → 1H|1H quá thô cho VWAP session|
