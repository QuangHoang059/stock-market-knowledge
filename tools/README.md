# Bộ công cụ đánh giá cổ phiếu (`tools/`)

Bộ script Python chấm điểm cổ phiếu theo 3 trường phái — **giá trị (Buffett)**,
**tăng trưởng (CANSLIM)**, **kỹ thuật** — kèm module **quản trị rủi ro**. Dữ liệu
thật qua **vnstock** (cổ phiếu Việt Nam) và **Yahoo Finance** (chỉ số/mã nước ngoài).

Mọi ngưỡng chấm điểm tham chiếu chặt theo tài liệu bài 01–06 trong cùng repo.

## Cài đặt

```bash
pip install -r requirements.txt
```

## Cách dùng (CLI)

```bash
cd stock-market-knowledge

# Đánh giá đầy đủ (cơ bản + kỹ thuật + rủi ro) — mặc định style=auto
python -m tools.evaluate FPT

# Chỉ một trường phái
python -m tools.evaluate FPT --style value
python -m tools.evaluate FPT --style growth
python -m tools.evaluate FPT --style technical

# Tính position sizing với vốn & rủi ro riêng
python -m tools.evaluate FPT --capital 200000000 --risk 1.5

# Chỉ số / mã nước ngoài (chỉ có kỹ thuật, Yahoo)
python -m tools.evaluate ^VNINDEX --style technical
python -m tools.evaluate AAPL --style technical

# Xuất JSON để xử lý tiếp
python -m tools.evaluate FPT --json
```

## Kiến trúc

| File | Trách nhiệm | Tham chiếu |
|------|-------------|------------|
| `data.py` | Lớp dữ liệu: OHLCV, cơ bản (tự tính ROE/ROA/biên/D-E/EPS/định giá), xu hướng chỉ số | — |
| `indicators.py` | Chỉ báo kỹ thuật thuần pandas/numpy: SMA/EMA/RSI/MACD/Bollinger/ATR/OBV/VWAP, `rs_rank` | 01 |
| `value_score.py` | Bảng điểm giá trị Buffett (8 tiêu chí có trọng số) | 02 |
| `canslim_score.py` | Bảng điểm tăng trưởng CANSLIM (C-A-N-S-L-I-M) | 03 |
| `technical.py` | Phân tích kỹ thuật tổng hợp: xu hướng, S/R, nến, RSI/MACD/BB, Wyckoff/VSA, Elliott/Fib | 01, 04, 05 |
| `risk.py` | Position sizing + R:R + stop ATR | 06 |
| `report.py` | Lắp báo cáo Markdown + verdict tổng hợp | — |
| `evaluate.py` | CLI duy nhất — điều phối toàn bộ pipeline | — |

## Bảng ngưỡng chấm điểm

| Nhóm | Tiêu chí | Ngưỡng |
|------|----------|--------|
| Giá trị | ROE | ≥ 15% & duy trì |
| Giá trị | ROA | ≥ 10% |
| Giá trị | Debt/Equity | < 0.5 |
| Giá trị | Current Ratio | > 1.5 |
| Giá trị | PEG | ≤ 1 |
| Giá trị | Biên an toàn (Graham) | ≥ 20% |
| CANSLIM | C — EPS quý YoY | ≥ 25% |
| CANSLIM | A — EPS năm (3 năm) | ≥ 25%/năm |
| CANSLIM | N — gần đỉnh 52 tuần | ≤ ~5% |
| CANSLIM | L — RS rank | ≥ 70 (lý tưởng 80–90) |
| CANSLIM | M — hướng thị trường | Giá > MA50 > MA200 |
| Kỹ thuật | RSI quá mua/bán | > 70 / < 30 |
| Kỹ thuật | MA stack uptrend | Giá > MA20 > MA50 > MA200 |
| Kỹ thuật | Fibonacci thoái lui | 23.6 / 38.2 / 50 / 61.8 % |
| Kỹ thuật | Fibonacci mở rộng | 161.8 % (có thể 261.8) |
| Rủi ro | Rủi ro/lệnh | 1–2% vốn |
| Rủi ro | Cắt lỗ | 7–8% (O'Neil) |
| Rủi ro | R:R (Reward:Risk) | ≥ 2:1 |

## Dùng như thư viện

```python
from tools import data as D, technical as T, value_score as V, risk as R

hist = D.get_history("FPT", years=3)
fund = D.get_fundamentals("FPT")
print(V.score_value(fund).score)          # điểm Buffett 0–100
print(T.analyze(hist)["bias"])            # bull / bear / neutral
print(R.position_size(1e8, 0.015, 72300, 69000).to_dict())
```

## Lưu ý dữ liệu (caveat)

- vnstock chỉ cung cấp **4 quý gần nhất** → CANSLIM "C" dùng tăng trưởng EPS năm
  thay cho EPS quý YoY (có ghi chú trong báo cáo).
- Dữ liệu **tổ chức (CANSLIM "I")** hạn chế ở VN → đánh dấu NA, cần kiểm tra thủ công
  (các CTĐT lớn, lượng nắm giữ).
- Elliott/Fibonacci và Wyckoff/VSA **mang tính chủ quan** — đây là công cụ tham chiếu,
  không phải tín hiệu duy nhất (xem caveat trong bài 04, 05).

> ⚠️ Kết quả là phân tích tự động, **không phải khuyến nghị đầu tư**.
