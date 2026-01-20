# MindStack SRS Algorithm (FSRS-5 / Spec v9.0)

## Overview
MindStack chuyển sang sử dụng bộ thư viện chính thức **`fsrs` (Python version of FSRS-RS)** để tối ưu hóa khả năng dự đoán ghi nhớ. Thuật toán tuân thủ chuẩn FSRS-5 (19 tham số) với nhân xử lý bằng Rust để đảm bảo hiệu suất và độ chính xác cao nhất.

---

## Part 1: Thang Điểm (0-7) & Mapping
Hệ thống sử dụng thang điểm linh hoạt, ánh xạ về 4 mức đánh giá của FSRS:

| Nguồn | Điểm (Score) | FSRS Rating | Ý nghĩa |
|-------|--------------|-------------|---------|
| Flashcard | 0-1 | Again (1) | Quên hoàn toàn |
| Flashcard | 2 | Hard (2) | Nhớ vất vả |
| Flashcard | 3-4 | Good (3) | Nhớ bình thường |
| Flashcard | 5-7 | Easy (4) | Nhớ rất dễ |

| Flashcard | 5-7 | Easy (4) | Nhớ rất dễ |

> [!NOTE]
> **Hybrid Logic (Wrapper):**
> Hệ thống sử dụng logic "lai" để tối ưu hóa trải nghiệm:
> 1. **Core**: FSRS-RS tính toán Stability/Difficulty chuẩn.
> 2. **Wrapper**: Áp dụng hệ số nhân (Multiplier) cho kết quả Interval:
>    - **MCQ (Score 6)**: Interval x 1.5 (Thưởng).
>    - **Typing (Score 7)**: Interval x 2.5 (Thưởng lớn).
>    - **Hard (Score 2)**: Interval x 0.8 (Giảm nhẹ).
> 3. **Safety Caps**: Min 20 phút - Max 365 ngày.

---

## Part 2: FSRS-5 Scheduler
Thuật toán sử dụng lớp `fsrs.Scheduler` để tính toán trạng thái thẻ (`fsrs.Card`). 
- **Stability (S)**: Khả năng ổn định của trí nhớ (tính bằng ngày).
- **Difficulty (D)**: Độ khó của mục từ (từ 1.0 đến 10.0).

---

## Part 3: Interval Calculation (Minute-Level Precision)
Khoảng cách ôn tập ($I$) được tính dựa trên **Desired Retention ($d$)** do người dùng cấu hình trong cài đặt:
$$I = S \cdot \frac{\ln(d)}{\ln(0.9)}$$

*Ví dụ: Với $d = 0.90$, $I = S$. Với $d = 0.95$, $I \approx 0.46 \cdot S$.*

---

## Part 4: Native Metrics & UI Mapping
1. **Retention (Khả năng ghi nhớ)**: $R = 0.9^{elapsed / stability}$ (Hiển thị chính: **% Ghi nhớ**)
2. **Mastery (Thông thạo)**: 
   $$Mastery = 0.1 + 0.9 \cdot (1 - \exp(-0.03 \cdot Stability))$$
   *(Dùng cho visualization độ bền vững của trí nhớ)*

> [!IMPORTANT]
> Toàn bộ các chỉ số nội bộ được chuẩn hóa về thang **0.0 - 1.0** (decimal). Việc nhân lên 100% chỉ thực hiện ở lớp hiển thị (UI layer).

---

## Part 5: Safety Valve & Caps
- **Khoảng cách tối thiểu**: 20 phút.
- **Khoảng cách tối đa**: 365 ngày.

---

## Code References
- [`hybrid_fsrs.py`](../mindstack_app/modules/learning/logics/hybrid_fsrs.py) - Wrapper cho thư viện `fsrs`
- [`unified_srs.py`](../mindstack_app/modules/learning/logics/unified_srs.py) - Tích hợp SRS vào hệ thống chung
