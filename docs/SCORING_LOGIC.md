# Logic Tính Điểm Hệ Thống (Scoring Logic - Phiên bản Cân Bằng)

Hệ thống tính điểm đã được tinh chỉnh để tạo ra sự thử thách, tránh việc tăng điểm quá nhanh và tập trung thưởng cho việc ghi nhớ các kiến thức khó.

## 1. Công Thức Tính Điểm Mới

Điểm số được tính toán dựa trên độ khó và khả năng ghi nhớ thực tế của người dùng:
**Tổng điểm = Điểm Cơ Bản * (1 + Hệ số Độ Khó + Hệ số Thử Thách) + Thưởng Chuỗi**

---

### A. Điểm Cơ Bản (Base Score - Đã tinh chỉnh)
Giá trị mặc định thấp để tạo tính thử thách nhưng vẫn đảm bảo người dùng được cộng điểm khi bắt đầu học:
- **Again (1)**: `1` XP (Điểm tối thiểu khi tham gia học)
- **Hard (2)**: `2` XP 
- **Good (3)**: `4` XP
- **Easy (4)**: `7` XP

### B. Thưởng Độ Khó (Difficulty Bonus)
Thưởng cho các thẻ có độ khó cao (D=1..10).
- **Hệ số**: `Độ khó / 20.0` (Thưởng tối đa +50% điểm cơ bản khi D=10).
- **Ví dụ**: Trả lời "Good" (5 XP) cho thẻ độ khó 10 -> Thưởng thêm 2.5 XP (~3 XP).

### C. Thưởng Thử Thách (Challenge Bonus - Quan trọng)
Thưởng dựa trên chỉ số **Stability** (Độ ổn định trí nhớ). Stability càng thấp (nghĩa là thẻ mới hoặc sắp quên), điểm thưởng càng cao.
- **Hệ số**: `1.0 / (Stability + 1.0)`.
- **Hiệu quả**: 
  - Thẻ mới (S=0): Thưởng thêm **+100%** điểm cơ bản.
  - Thẻ đã nhớ lâu (S=100 ngày): Thưởng thêm rất ít (~1%).
  - Logic này giúp người dùng nhận nhiều điểm hơn khi học kiến thức mới hoặc cứu những thẻ sắp quên.

### D. Thưởng Chuỗi (Streak Bonus - Thu gọn)
Chuỗi trả lời đúng vẫn được thưởng nhưng với mức độ hạn chế hơn:
- **Điều kiện**: Chuỗi >= `10` (Ngưỡng cao hơn).
- **Giá trị**: `Chuỗi / 10` (Cộng 1 điểm cho mỗi 10 chuỗi liên tiếp).
- **Giới hạn**: Tối đa `10` XP.

---

## 2. Các Tham Số Cấu Hình (Admin)

| Tham số | Ý nghĩa | Mặc định mới |
|:---|:---|:---:|
| `SCORING_STREAK_THRESHOLD` | Ngưỡng chuỗi bắt đầu thưởng | 10 |
| `SCORING_STREAK_CAP` | Giới hạn điểm thưởng chuỗi | 10 |
| `DAILY_GOAL_SCORE` | Thưởng mục tiêu ngày | 20 |

### Bổ sung: Quiz & Minigames
Điểm thưởng cho các hoạt động khác cũng được tinh chỉnh giảm xuống:
- **Quiz**: Đúng 1 câu: `5` XP \| Hoàn thành lần đầu: `3` XP
- **Minigames**:
  - Trắc nghiệm (MCQ): `3` XP
  - Gõ từ (Typing): `5` XP
  - Nghe chép (Listening): `4` XP
  - Tốc độ (Speed): `2` XP
  - Ghép thẻ (Matching): `1` XP

---

## 3. Tại sao điểm tăng chậm hơn?
Hệ thống mới ưu tiên **Chất lượng** hơn **Số lượng**:
1. Đòi hỏi bạn phải đối mặt với kiến thức khó để nhận được nhiều điểm.
2. Việc cày chuỗi (streak) không còn mang lại quá nhiều lợi thế như trước, giúp bảng xếp hạng công bằng hơn.
3. Tập trung vào việc "Học mới" và "Ôn tập đúng lúc".
