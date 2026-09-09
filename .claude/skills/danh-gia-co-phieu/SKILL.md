---
name: danh-gia-co-phieu
description: Đánh giá / phân tích một mã cổ phiếu Việt Nam hoặc chỉ số (FPT, DIG, VNINDEX...). Chạy bộ công cụ tools/ để chấm điểm theo giá trị (Buffett), tăng trưởng (CANSLIM), kỹ thuật, và lập kế hoạch rủi ro, sau đó diễn giải kết quả theo tài liệu bài 01–06. Dùng khi người dùng yêu cầu phân tích, đánh giá, chấm điểm, hoặc xem nên mua/theo dõi/tránh một mã cổ phiếu.
---

# Skill: Đánh giá cổ phiếu

Skill này điều phối bộ công cụ `tools/` trong thư mục `stock-market-knowledge/` để
đánh giá một mã cổ phiếu, rồi **diễn giải kết quả theo đúng kiến thức** trong các file
markdown bài 01–06 (nằm trong thư mục `lessons/`).

## Khi nào dùng

Khi người dùng yêu cầu (bằng tiếng Việt hoặc tiếng Anh) một trong các dạng:
- "đánh giá / phân tích / chấm điểm mã FPT"
- "FPT có nên mua không?", "cổ phiếu X tốt không"
- "xem cổ phiếu DIG theo trường phái giá trị / CANSLIM / kỹ thuật"
- "tính position sizing cho mã Y với vốn 200 triệu"

## Quy trình (luôn làm theo thứ tự)

### 1. Chạy công cụ đánh giá

Từ thư mục `stock-market-knowledge/`, chạy CLI `tools.evaluate`. Chọn `--style`:

| Nhu cầu người dùng | Lệnh |
|--------------------|------|
| Đánh giá toàn diện (mặc định) | `python -m tools.evaluate <MÃ>` |
| Chỉ đầu tư giá trị (Buffett) | `python -m tools.evaluate <MÃ> --style value` |
| Chỉ tăng trưởng (CANSLIM) | `python -m tools.evaluate <MÃ> --style growth` |
| Chỉ kỹ thuật | `python -m tools.evaluate <MÃ> --style technical` |
| Có vốn & rủi ro cụ thể | thêm `--capital 200000000 --risk 1.5` |
| Chỉ số / mã nước ngoài | `python -m tools.evaluate ^VNINDEX --style technical` |
| Cần xử lý tiếp bằng code | thêm `--json` |

Luôn dùng `python -m tools.evaluate` (không gọi `python tools/evaluate.py` trực tiếp)
để import package đúng.

### 2. Đọc báo cáo & diễn giải theo tài liệu

Ánh xạ điểm/score → ngưỡng trong tài liệu (đừng bịa ngưỡng):

- **Giá trị (bài 02)**: ROE ≥ 15% & duy trì, D/E < 0.5, Current ratio > 1.5,
  PEG ≤ 1, biên an toàn Graham ≥ 20%. Điểm ≥ 70 = MẠNH, 50–70 KHẢ QUAN, < 50 TRÁNH.
- **CANSLIM (bài 03)**: C = EPS quý YoY ≥ 25%, A = EPS năm ≥ 25%/3 năm,
  N = gần đỉnh 52 tuần, S = volume ngày tăng > ngày giảm, L = RS rank ≥ 70 (80–90 lý tưởng),
  I = tổ chức, M = chỉ số uptrend (Giá > MA50 > MA200).
- **Kỹ thuật (bài 01, 04, 05)**: RSI > 70 quá mua / < 30 quá bán; MA stack uptrend =
  Giá > MA20 > MA50 > MA200; Fibonacci thoái lui 23.6/38.2/50/61.8, mở rộng 161.8;
  Wyckoff: Spring/SOS = tích lũy, UTAD/phân phối = xả.
- **Rủi ro (bài 06)**: rủi ro 1–2%/lệnh, cắt lỗ 7–8% (O'Neil), R:R ≥ 2:1.
  Công thức: `Số CP = Tiền rủi ro / (Giá vào − Giá cắt lỗ)`.

### 3. Trình bày kết quả (tiếng Việt, cấu trúc cố định)

Luôn theo 6 mục này — ngắn gọn, không lặp nguyên văn báo cáo:

1. **Điểm mạnh** — các tiêu chí PASS nổi bật.
2. **Điểm yếu** — các FAIL quan trọng (đặc biệt nợ, định giá đắt, RS thấp).
3. **Tín hiệu kỹ thuật** — bias (bull/bear/neutral) + 2–3 tín hiệu nổi bật nhất.
4. **Đánh giá cơ bản** — điểm giá trị & CANSLIM + nhận định.
5. **Khuyến nghị & rủi ro** — khớp với verdict tổng hợp (MUA/THEO DÕI/TRÁNH)
   + kế hoạch vào/lỗ/lời (nếu người dùng hỏi position sizing).
6. **Disclaimer** — LUÔN nêu.

### 4. Bắt buộc nêu caveat dữ liệu

Nếu báo cáo có phần "Lưu ý dữ liệu", phải tóm tắt lại cho người dùng, đặc biệt:
- CANSLIM "C" dùng tăng trưởng EPS năm (vnstock chỉ có 4 quý).
- Dữ liệu tổ chức ("I") hạn chế ở VN → cần kiểm tra thủ công.
- Elliott/Fibonacci & Wyckoff mang tính chủ quan.

## Mẫu câu trả lời

> ### Đánh giá FPT — THEO DÕI (52/100 cơ bản, kỹ thuật NEUTRAL)
> **Điểm mạnh**: ROE 25.7% (duy trì ≥15%), biên ròng 16% tăng, EPS +10.7%/năm.
> **Điểm yếu**: D/E 1.01 (nợ cao > 0.5), PEG 1.75 (đắt), biên an toàn Graham −53%,
> RS rank 0 (tụt hậu thị trường).
> **Kỹ thuật**: NEUTRAL — MA đan nhau, MACD histogram dương nhưng cấu trúc LH/LL.
> **Cơ bản**: Giá trị KHẢ QUAN (52), nhưng CANSLIM TRÁNH (0) do xa đỉnh & thị trường chưa uptrend.
> **Khuyến nghị**: THEO DÕI — chờ giá gần đỉnh 52 tuần + VNINDEX uptrend + khối lượng
> tăng ngày. Nếu vào: 72,300 / cắt lỗ 69,400 (ATR) / mục tiêu 78,100 (R:R 2:1).
> **⚠️ Disclaimer**: Phân tích tự động từ vnstock/Yahoo, không phải khuyến nghị đầu tư.
> CANSLIM "C" dùng EPS năm do vnstock chỉ có 4 quý. Đầu tư có rủi ro mất vốn.

## Lưu ý

- Nếu công cụ báo "Không lấy được dữ liệu" → kiểm tra kết nối/mã, đừng bịa số liệu.
- Nếu người dùng hỏi mã mà công cụ không có (mã mới/niêmt yết chưa đủ lịch sử) → nói rõ
  giới hạn và gợi ý kiểm tra thủ công.
- Không chạy lệnh `evaluate` với dữ liệu giả; luôn dùng dữ liệu thật từ vnstock/Yahoo.
- Khi người dùng hỏi so sánh nhiều mã → chạy từng mã rồi lập bảng so sánh điểm tổng hợp.
