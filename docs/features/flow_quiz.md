# Luồng Xử Lý Database Khi Trả Lời: Quiz System

Module **Quiz** (Bài Kiểm Tra/Sát Hạch) là một module biệt lập, chuyên biệt cho đánh giá năng lực một lần, khác hoàn toàn với các cơ chế Flashcard/Typing/MCQ nhắm mục tiêu lặp lại (Spaced Repetition).
Bởi vậy, luồng dữ liệu tác động tới CSDL khi chọn Đáp án cho **Quiz** có nhiều khác biệt. Nó tránh ảnh hưởng làm nhiễu lịch học tập dài hạn của FSRS.

Quá trình này chủ yếu đi qua module `quiz`, và cập nhật `score_logs` cho mục đích Gamification, nhưng **Tuyệt Đối Không Ghi Đè FSRS (ItemMemoryState)**.

---

## 1. Trạng Thái Người Chơi Trong Phiên Bài Thi (`learning_sessions` / `quiz_attempts`)

Bài thi không dùng session thông thường. Nó lưu trữ qua mô hình `quiz_attempts` (Lần thi) và `quiz_answers` (Các đáp án chi tiết chưa nộp).
Khi người dùng **Click Chọn Đáp Án (A, B, C...)**:
- **Trạng thái lưu tậm**: Nếu hệ thống cho phép "chọn và sửa", câu trả lời của người dùng có thể chỉ được lưu trong localStorage hoặc cập nhật tạm thời bằng API (Upsert) vào bảng **`quiz_answers`** liên kết với `attempt_id` hiện tại.
- Các cột được cập nhật: `selected_option_id`, `time_spent`, `is_flagged` (để review sau).
- **KHÔNG PHÊ DUYỆT (COMMIT) ĐIỂM SỐ**: Điểm số không được tính ngay lúc này để tránh làm lộ kết quả, trừ khi đây là Quiz dạng "Chữa Ngay" (Instant Feedback).

## 2. Nộp Bài Thi (Sự kiện Submit Toàn Bộ)

Hành vi ghi DB hàng loạt bắt đầu khi Session kết thúc. Người dùng bấm **Hoàn Thành Bài Kiểm Tra**.
Logic API `QuizSessionService.submit_quiz()` diễn ra:

### A. Kiểm Tra Chấm Điểm
- Quét qua toàn bộ `quiz_answers` của lần thi (`quiz_attempts.attempt_id`).
- JOIN vào bảng `quiz_options` (hoặc `learning_items`) để check `is_correct = True`.
- Cập nhật đồng loạt các field `is_correct` trên các bản ghi `quiz_answers`.

### B. Cập Nhật Tổng Lượt Thi (`quiz_attempts`)
- Update `score` (Điểm), `correct_count`, `incorrect_count`.
- `end_time` = now(), `status` chuyển từ "playing" -> "completed".

### C. FSRS By-Pass (Bỏ Qua FSRS) 🚫
- Dữ liệu Quiz (đặc biệt là bài tự đánh giá cuối ngày/cuối khoá) **không** đổ kết quả Đúng/Sai vào thuật toán FSRS.
- Trí nhớ (Stability/Difficulty) ở `item_memory_states` giữ nguyên. Lý do: Thi cử là việc kiểm tra thước đo chứ không phải một chu kỳ lặp nội tại tự thân, nếu ép FSRS update sẽ làm phồng (inflate) Stability không có chủ đích.

### D. Hệ Thống Điểm Thưởng & Huy Hiệu (Gamification)
Module `quiz` sẽ kích hoạt **Signal `quiz_completed.send()`**. Gamification module lắng nghe để vinh danh:
- **Tặng điểm lớn**: Quiz thưởng điểm sỉ (bulk) bằng một record `INSERT INTO score_logs` với `score_change` bằng điểm từ bài thi kèm hệ số độ khó, `reason` = "Passed Final Quiz".
- Cập nhật số tổng điểm `users.total_score`.
- Module Badges quét điểm. Nếu người dùng đạt Perfect (100% đúng) -> tự động `INSERT` một danh hiệu mới vào `user_badges` (ví dụ "Quiz Master - Thần Khảo Thí").

## 3. History Module (`study_logs`)
- (Tuỳ chọn) Đôi khi Quiz không đi qua `study_logs` từng câu. History Module chỉ ghi lại 1 log cha (Dạng Event) đại diện việc người dùng vừa hoàn thành bài test tên XYZ với 80/100đ, hoặc tạo các log riêng lẻ cho dạng Quiz Instant Feedback dựa vô tuỳ biến codebase.

---

### Tóm Lược (Executive Summary)
**Khi Trả Lời và Submit Quiz, hệ thống sinh ra cơ chế DB:**
1. **Trong lúc làm bài**: `UPDATE / INSERT` vào bảng lưu nháp `quiz_answers` liên kết với `quiz_attempts` đang mở. Không tác động điểm số. Không lộ đáp án.
2. **Khi bấm Nộp Bài**:
   - Máy kiểm tra toàn diện, `UPDATE quiz_attempts` gắn Tag "completed", gán điểm tổng.
   - 🚫 **Bảo Hiểm**: Khóa (Lock) bảng `item_memory_states` (FSRS) khỏi cập nhật. Bài thi chỉ là "Ảnh Chụp" để xem chứ không thay đổi nhịp sinh học Spaced Repetition của Flashcard.
   - `INSERT score_logs` -> Trao điểm thưởng lớn một lần duy nhất vào `total_score` người dùng. Bắn Signal cấp Huy Hiệu nếu điểm xuất sắc 100%.
