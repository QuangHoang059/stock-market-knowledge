# 📈 stock-market-knowledge

Bộ tài liệu kiến thức + công cụ Python đánh giá cổ phiếu, tổng hợp các trường phái đầu tư/giao dịch phổ biến, áp dụng cho thị trường **Việt Nam** (dữ liệu qua `vnstock`) và thị trường quốc tế (qua Yahoo Finance).

> ⚠️ Toàn bộ nội dung mang tính **giáo dục**, **không phải khuyến nghị đầu tư**.

---

## 📚 Mục lục tài liệu

| # | Bài | Trường phái / Chủ đề |
|---|-----|----------------------|
| 01 | [Nhận thức & Khái niệm Cơ bản](01_Nhan_Thuc_&_Khai_Niem_Co_Ban.md) | Khái niệm, chỉ báo kỹ thuật (MA/RSI/MACD/BB), nến Nhật, xu hướng, lệnh giao dịch. |
| 02 | [Triết lý Đầu tư Giá trị (Buffett)](02_Triet_Ly_Dau_Tu_Gia_Tri_Buffett.md) | Moat, ROE, nợ, biên an toàn, định giá. |
| 03 | [Hệ thống Tăng trưởng (CANSLIM)](03_He_Thong_Tang_Truong_CANSLIM.md) | 7 tiêu chí O'Neil, cúp tay cầm, FTD. |
| 04 | [Wyckoff & VSA](04_Ly_Thuyet_Wyckoff_&_VSA.md) | Dấu chân dòng tiền, tích lũy/phân phối, Spring/UTAD. |
| 05 | [Sóng Elliott & Fibonacci](05_Nguyen_Ly_Song_Elliott.md) | Cấu trúc 5-3, 3 quy tắc, mục tiêu Fib. |
| 06 | [Quản trị Rủi ro & Kỷ luật](06_Quan_Tri_Rui_Ro_&_Ky_Luat.md) | R:R, position sizing, cắt lỗ 7–8%, chốt lời 20–25%. |

### Lộ trình học gợi ý

1. **Nền tảng** → bài 01 (đọc biểu đồ, nến, chỉ báo) + bài 06 (quản trị rủi ro — quan trọng nhất).
2. **Chọn cổ phiếu** → bài 02 (giá trị, dài hạn) **hoặc** bài 03 (tăng trưởng, bứt phá).
3. **Điểm vào/ra** → bài 04 (Wyckoff/VSA) + bài 05 (Fibonacci mục tiêu giá).
4. **Luôn quay lại** bài 06 để giữ kỷ luật.

---

## 🛠️ Công cụ đánh giá (`tools/`)

Bộ script Python chấm điểm một mã cổ phiếu theo **3 trường phái** + rủi ro, dùng dữ liệu thật:

```bash
# Cài đặt
pip install -r requirements.txt

# Đánh giá đầy đủ (cơ bản + kỹ thuật + rủi ro)
python -m tools.evaluate FPT

# Theo từng trường phái
python -m tools.evaluate FPT --style value       # Buffett
python -m tools.evaluate FPT --style growth      # CANSLIM
python -m tools.evaluate FPT --style technical   # Kỹ thuật/Wyckoff/Fib

# Chỉ số (qua Yahoo) / kèm quản trị rủi ro
python -m tools.evaluate ^VNINDEX --style technical
python -m tools.evaluate FPT --capital 200000000 --risk 1.5
```

Chi tiết tham số & cách đọc kết quả: [`tools/README.md`](tools/README.md).

### Nguồn dữ liệu

- **Cổ phiếu VN**: `vnstock` — lịch sử giá (OHLCV) + báo cáo tài chính (ROE, nợ, biên lợi nhuận, EPS…).
- **Chỉ số quốc tế / mã nước ngoài**: Yahoo Finance (`^VNINDEX`, `^GSPC`, `AAPL`…).
- `main.py` — bot Telegram cảnh báo giá (ví dụ lấy giá realtime, dùng chung lớp dữ liệu).

---

## 🤖 Skill Claude: `/danh-gia-co-phieu`

Project đi kèm skill `.claude/skills/danh-gia-co-phieu/` để Claude chạy công cụ và **diễn giải kết quả theo đúng kiến thức** ở bài 01–06, xuất verdict tiếng Việt (điểm mạnh/yếu, tín hiệu kỹ thuật, khuyến nghị & rủi ro, disclaimer).

---

## ⚖️ Miễn trừ trách nhiệm

Mọi phân tích là công cụ **hỗ trợ ra quyết định**, không thay thế nhận định của bạn. Đầu tư chứng khoán có rủi ro mất vốn. **Quyết định và trách nhiệm cuối cùng thuộc về bạn.**
