# 06. Quản trị Rủi ro & Kỷ luật Thực thi

Kỹ thuật chọn cổ phiếu tốt (bài 02–05) chỉ có giá trị khi đi kèm **quản trị rủi ro**. Mục tiêu không phải "đúng mọi lệnh" mà **sống sót đủ lâu** để những lần đúng bù đắp những lần sai. Đây là bài học quan trọng nhất của giao dịch.

---

## 1. Tỷ lệ Lợi nhuận / Rủi ro (Reward : Risk)

> ⚠️ **Lưu ý quy ước**: "R:R" có hai cách ghi dễ nhầm. Bài này dùng **Reward : Risk** (lãi : lỗ). Một số tài liệu ghi ngược (Risk/Reward) nên sẽ thấy "≤ 0.5" — hai cách nói cùng một ý: **lãi tiềm năng ≥ 2 lần lỗ**.

- **Tối thiểu R:R = 2:1** (lãi kỳ vọng gấp đôi lỗ); lý tưởng **≥ 3:1**.
- Ví dụ O'Neil: chốt lời **20–25%** vs cắt lỗ **7–8%** → R:R ≈ **3:1**.
- Chỉ vào lệnh khi **R:R đạt ngưỡng**; nếu không, bỏ qua — kỷ luật "không giao dịch" cũng là một quyết định.

## 2. Quy mô vị thế (Position Sizing)

Nguyên tắc vàng: mỗi lệnh chỉ rủi ro **1% – 2% tổng vốn** (không phải giải ngân 1–2%, mà là **số tiền sẵn sàng mất** nếu dính stop-loss).

**Công thức 1 — theo % cắt lỗ (giải ngân vốn):**

```text
Vốn giải ngân = (Vốn tài khoản × Rủi ro%) / Cắt lỗ%
```

Ví dụ: vốn 100 triệu, rủi ro 1% (1 triệu), stop-loss 5% → giải ngân = 1.000.000 / 0.05 = **20 triệu**.

**Công thức 2 — theo số cổ phiếu (chính xác hơn khi đã có giá cụ thể):**

```text
Tiền rủi ro      = Vốn tài khoản × Rủi ro%
Số cổ phiếu mua  = Tiền rủi ro / (Giá vào − Giá cắt lỗ)
```

Ví dụ: vốn 100 triệu, rủi ro 1% (1 triệu); giá vào 100, stop 95 (mất 5/cp) → số cp = 1.000.000 / 5 = **200.000 cp** (giá trị vị thế 20 triệu).

> Hai công thức cho cùng kết quả khi (Giá vào − Giá cắt lỗ)/Giá vào = Cắt lỗ%.

## 3. Kỷ luật cắt lỗ & chốt lời (theo O'Neil)

| Hành động | Quy tắc |
|-----------|---------|
| **Cắt lỗ (Stop Loss)** | Tuyệt đối cắt khi giá giảm **7–8%** từ điểm mua — **không ngoại lệ**, không hy vọng. |
| **Chốt lời (Take Profit)** | Đạt **+20–25%** từ điểm bứt phá chuẩn → chốt (ít nhất một phần). |
| **Quy tắc giữ (8-week rule)** | Nếu cổ phiếu **tăng > 20% chỉ trong 3 tuần đầu** → có thể là siêu cổ phiếu → **giữ thêm ít nhất 8 tuần**. |
| **Không round-trip** | Đã có lãi đáng kể thì **không để giá quay lại dưới điểm mua** (dùng trailing stop). |

## 4. Nguyên tắc kỷ luật bổ sung

- **Trailing stop**: khi giá có lãi, **kéo stop theo** mức giá cao dần để khóa lợi nhuận, không để lãi biến lỗ.
- **Không gộp lỗ (averaging down)**: đừng mua thêm chỉ vì giá giảm để "giảm giá vốn" — thường là cách tự hủy hoại tài khoản.
- **Pyramid khi lãi**: chỉ bổ sung thêm vào các vị thế **đang có lãi** và đi đúng xu hướng.
- **Giới hạn tập trung**: không để một mã/nhóm ngành chiếm phần vốn quá lớn.
- **Giới hạn lỗ theo ngày/tuần**: cạn kiệt vốn đến mức đặt trước → **dừng giao dịch** để lấy lại bình tĩnh.

## 5. Tâm lý & nhật ký

- Ghi **nhật ký giao dịch**: lý do vào, điểm cắt lỗ, kết quả, bài học — cải thiện qua thời gian.
- Chấp nhận **thua lỗ nhỏ là chi phí kinh doanh**, không coi là thất bại cá nhân.
- Khi **dính chuỗi thua** → giảm kích thước vị thế, không "gỡ" bằng cách tăng rủi ro.

---

> ⚠️ **Miễn trừ trách nhiệm**: Tài liệu mang tính giáo dục, **không phải khuyến nghị đầu tư**. Quản trị rủi ro là yếu tố **bắt buộc** nhưng không đảm bảo có lãi; thị trường luôn có rủi ro.
