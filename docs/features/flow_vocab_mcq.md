# Luồng Xử Lý Database Khi Trả Lời: Vocab MCQ

Trong chế độ học **Multiple Choice Questions (MCQ) - Trắc Nghiệm**, dòng thời gian và cách hệ thống lưu trữ có một vài khác biệt tinh tế so với Flashcard, chủ yếu do MCQ có khái niệm đáp án cụ thể (A, B, C, D) chứ không tự đánh giá (Rating).

Quá trình này đi qua các module liên kết: `vocabulary.mcq`, `session`, `gamification`, và `learning_history`. Tùy thuộc cấu hình (bật/tắt FSRS cho MCQ), module `fsrs` cũng có thể tham gia.

---

## 1. Trạng Thái Phiên Học (`learning_sessions`)

Bước xử lý đầu tiên khi người dùng chọn một đáp án (ví dụ bấm A) thông qua `MCQSessionManager.submit_answer()`:
- Dữ liệu `session_data` JSON trong bảng `learning_sessions` được kéo lên.
- Hệ thống kiểm tra đáp án submit có khớp với `correct_key` trong bộ dữ liệu MCQ của Session hay không để đánh giá **Đúng/Sai**.
- Cột `processed_item_ids` ghi nhận Item đã hoàn tất xử lý.
- Bộ đếm `correct_count` hoặc `incorrect_count` được tăng lên tương ứng. `last_activity` được cập nhật = now().

## 2. Thay Đổi Trạng Thái Trí Nhớ (Tùy Chọn FSRS)

Khác với Flashcard, FSRS cho MCQ có thể được cấu hình để bật/tắt (thường MCQ có trọng số ảnh hưởng trí nhớ thấp hơn). Nếu FSRS được bật cho chế độ MCQ:
- Một ánh xạ ngầm (implicit mapping) được tạo ra. Trả lời Đúng (First Try) thường ánh xạ thành Rating 3 (Good). Trả lời Sai ánh xạ thành Rating 1 (Again).
- Giao diện `FSRSInterface.process_interaction()` (hoặc tương tự) được gọi.
- Bảng `item_memory_states` (`stability`, `difficulty`, `due_date`) được update. Với MCQ, sự tăng trưởng `stability` thường bị kìm hãm (hard-capped) ở môi trường học nhận diện (recognition), không mạnh bằng học truy xuất chủ động (recall) như Flashcard.

## 3. Lịch Sử Học Tập (`study_logs`)

Log tương tác được ghi vào bảng `study_logs` (qua module `learning_history`):
- **Phản hồi chính xác**: Ghi nhận `user_answer` (chính xác phương án người dùng đã bấm, ví dụ "Apple") và `is_correct` (True/False).
- Không có `rating` (trừ khi hệ thống tự ngầm dịch mức độ Đúng/Sai sang Rating để thống nhất).
- **Duration**: `review_duration` ghi nhận số milli-giây kể từ khi câu hỏi hiển thị cho đến khi click.
- **FSRS & Gami Snapshots**: Cột `fsrs_snapshot` và `gamification_snapshot` sẽ lưu thông số sau khi tính điểm.

## 4. Gamification (`score_logs`)

Khi người dùng trả lời **đúng** (đặc biệt trong lần đầu - First Try):
- Tín hiệu `mcq_answered.send()` (hoặc `item_reviewed`) được bắn ra.
- **Chấm điểm linh hoạt**: Điểm `score_base` cho MCQ thường khác với Flashcard. Có tính thêm Bonus điệm cho tốc độ trả lời (Time Bonus) và số câu đúng liên tiếp (Streak Bonus ngay trong session).
- Ghi nhận `INSERT INTO score_logs` với `score_change` và `reason` = "MCQ Correct Answer".
- **`users.total_score`** được cộng dồn điểm mới.
- Nếu trả lời Sai, thường `score_change` = 0 và không có `INSERT` nào vào `score_logs` để tiết kiệm dung lượng DB.

---

### Tóm Lược (Executive Summary)
**Một click chọn B (Sai) hoặc C (Đúng) trong MCQ sẽ sinh ra:**
1. Trích xuất đáp án và kiểm tra Đúng/Sai qua Session Engine.
2. `UPDATE learning_sessions` -> Chuyển Item sang processed, tăng biến đếm.
3. `UPDATE item_memory_states` -> Nếu MCQ được cấu hình nạp vào FSRS, hệ thống tự dịch Đúng/Sai sang Rating tương đương để update lịch.
4. `INSERT study_logs` -> Lưu câu trả lời cụ thể của User thành chuỗi text.
5. `INSERT score_logs` -> Nạp điểm (Time Bonus, Streak Bonus) nếu đúng. Tăng `total_score` trên user.
