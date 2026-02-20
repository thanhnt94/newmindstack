# Hệ Thống Điểm Số & Gamification (MindStack)

MindStack sử dụng cơ chế điểm số (Gamification) để tạo động lực, thúc đẩy thói quen học tập của người dùng. Hệ thống này được tính toán theo thời gian thực (real-time) sau mỗi tương tác (trả lời đúng).

Module chịu trách nhiệm chính: `gamification`.

---

## 1. Lưu Trữ Điểm Số (Kép)

Hệ thống điểm số được lưu trữ ở hai nơi để đảm bảo cả tốc độ truy vấn lẫn tính vẹn toàn lịch sử giao dịch:

1. **Tổng điểm (Xếp hạng)**: Cột `total_score` trong bảng `users`.
   - Lưu trữ một con số Integer duy nhất (ví dụ: 12,450 điểm). Cột này được Update ngay lập tức sau mỗi lần có điểm mới. 
   - Dùng để hiển thị nhanh trên Header (HUD) và tính toán Leaderboard (Bảng xếp hạng).
2. **Lịch sử giao dịch (Score Logs)**: Bảng `score_logs`.
   - Giống như sao kê ngân hàng. Mỗi lần người dùng được cộng (hoặc trừ) điểm, một dòng (row) mới được `INSERT`.
   - Lưu trữ: `user_id`, `score_change` (+15 điểm), `reason` ("Flashcard Review", "Quiz Bonus"), và `timestamp`.
   - Dùng để vẽ biểu đồ thống kê học tập theo ngày và truy vết gian lận (nếu có).

---

## 2. Công Thức Tính Điểm Cơ Bản (Base Score)

Mỗi chế độ học có mức độ khó khác nhau, do đó Điểm Cơ Bản (Base Score) được quy định riêng biệt (tham khảo `config.py` của module gamification / scoring):

- **Flashcard (Tự đánh giá)**: `Base Score = 10`
  - Đòi hỏi sự trung thực. Nhấn Good/Easy được điểm.
- **Multiple Choice (MCQ)**: `Base Score = 12`
  - Đòi hỏi sự nhận diện đúng đáp án. Được cộng khi trả lời đúng (thường là First Try).
- **Typing (Gõ chữ)**: `Base Score = 15 -> 20`
  - Chế độ khó nhất đòi hỏi trí nhớ chủ động (Active Recall). Điểm cơ bản cao hơn để khuyến khích luyện tập.
- **Dịch nghĩa (Translate/Reading)**: `Base Score = 10`

---

## 3. Hệ Số Thưởng (Bonus Multipliers)

Để tăng tính cạnh tranh và kịch tính, hệ thống áp dụng hệ số nhân (Multiplier) lên Điểm Cơ Bản nếu thoả mãn điều kiện nhất định.
**Công thức thu nhập:** `Final Score = Base Score + Time Bonus + Streak Bonus`

### A. Thưởng Tốc Độ (Time Bonus)
Khuyến khích phản xạ nhanh. Dựa vào `review_duration` (thời gian từ lúc hiện câu hỏi đến lúc tick đáp án).
- Trả lời trong vòng `< 3 giây` -> **Bonus +50%** Base Score (hoặc cộng thẳng +5đ).
- Trả lời trong vòng `3 - 10 giây` -> **Không thưởng** (+0đ).
- Trả lời quá chậm `> 15 giây` -> Có thể bị **Trừ nhỏ** (Penalty).

### B. Thưởng Chuỗi Đúng Trúng Liên Tiếp (Session Streak Bonus)
Áp dụng trong độ dài của một Session học (Flashcard/MCQ).
- Bắt đầu từ câu thứ 3 trả lời đúng liên tiếp: Được cộng `Streak Multiplier`.
- Ví dụ: Trả lời đúng 5 câu liên tiếp -> Base Score (10đ) + Streak Bonus (5đ) = 15đ/câu.
- Nếu trả lời sai 1 câu -> Chuỗi (Combo) bị gãy về 0. Bắt đầu lại.

---

## 4. Chuỗi Ngày Học Liên Tiếp (Daily Streaks)

Khác với Session Streak (chuỗi câu đúng), `Daily Streak` là chuỗi **Số ngày học liên tiếp** truy xuất từ bảng `user_streaks` trong db.
- **Điều kiện duy trì**: Login và hoàn thành ít nhất 1 tương tác (Review Flashcard / Hoàn thành Quiz) trong vòng 24H (tính theo Timezone của User).
- Nếu qua 0:00 (nửa đêm) mà không học -> Streak gãy về 0. (Ghi chú: MindStack có thể có item "Streak Freeze - Đóng băng chuỗi" để bảo vệ trong tương lai).
- Nếu User duy trì Streak > 7 ngày, 30 ngày -> Có thể tặng điểm thưởng sỉ (Bulk Score Bonus) ví dụ tặng thẳng +500đ.

---

## 5. Tổng Kết Luồng Xử Lý (Event-Driven Pipeline)

Quá trình "Nạp Điểm" không bao giờ được viết trực tiếp bên trong logic học tập, mà dùng **Sự kiện (Signals)** để tách rời (Decouple):

1. **User gõ đúng câu trả lời (Typing Module)**.
2. Typing Module update Database xong xuôi, gửi thông báo ảo `typing_answered.send(user_id=1, duration=2s, is_correct=True, streak_count=5)`.
3. **Gamification Module** lắng nghe thông báo này.
   - Thấy `is_correct` = True.
   - Áp Base = 15đ.
   - Áp Time = +7đ (do duration=2s rất nhanh).
   - Áp Streak = +5đ (do đang đúng 5 câu liên tiếp).
   - Tổng = `27đ`.
4. Gamification Module `INSERT INTO score_logs (+27)` và `UPDATE users (+27 total_score)`.
5. Bắn thông tin trả về Frontend (qua WebSocket hoặc Response JSON) để UI hiện Popup thả tim / loé sáng / hiện dòng chữ màu xanh `+27 XP`.
