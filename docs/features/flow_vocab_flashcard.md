# Luồng Xử Lý Database Khi Trả Lời: Vocab Flashcard

Khi người dùng đánh giá (rate) một thẻ từ vựng (Flashcard) trong quá trình học, một loạt các bản ghi sẽ được ghi vào Cơ sở dữ liệu thông qua kiến trúc Modular Monolith.

Quá trình này chủ yếu đi qua các module: `vocabulary`, `session`, `fsrs`, `gamification`, và `learning_history`.

---

## 1. Trạng Thái Học Tập Cốt Lõi (`item_memory_states`)
**Thuộc module: `fsrs`**

Đánh giá của Flashcard (1: Again, 2: Hard, 3: Good, 4: Easy) là dữ liệu đầu vào trực tiếp cho thuật toán **FSRS v5**.
Khi nhận được `rating`, hệ thống gọi `FSRSInterface.process_review()`:
- **Cập nhật dòng hiện có**: Ghi đè chỉ số `stability`, `difficulty`, `state` (New/Learning/Review/Relearning) và `due_date`.
- **Thống kê cá nhân thẻ**: Tăng `repetitions` (số lần lặp), `lapses` (số lần quên nếu đánh giá mức 1), tính toán lại `streak` và `incorrect_streak`.
- **Ghi nhận lịch sử**: Cập nhật `last_review` = now().

## 2. Lịch Sử Học Tập Chi Tiết (`study_logs`)
**Thuộc module: `learning_history`**

Song song với việc cập nhật trạng thái FSRS, một log chi tiết về tương tác này được tạo mới (Insert) vào bảng `study_logs` thông qua `HistoryInterface`:
- **Thông tin cơ bản**: `user_id`, `item_id`, `container_id`, `session_id`.
- **Hành vi**: `rating` (từ 1 đến 4), `is_correct` (True nếu rating > 1, False nếu = 1), `review_duration` (thời gian lật thẻ).
- **Snapshot FSRS**: Cột `fsrs_snapshot` lưu trữ một bản sao dạng JSON trạng thái bộ nhớ (stability, difficulty...) *vào thời điểm ngay sau khi đánh giá*. Tránh mất dấu liệu FSRS sau này khi nó thay đổi.
- **Context**: Bổ sung thiết bị (Mobile/Desktop) vào `context_snapshot`.

## 3. Quản Lý Điểm Số & Gamification (`score_logs` & `user_streaks`)
**Thuộc module: `gamification`**

Ngay sau khi `study_logs` và `item_memory_states` ghi nhận hoàn tất, module `fsrs` sẽ bắn ra tín hiệu (Signal) `card_reviewed.send()`. Module `gamification` lắng nghe tín hiệu này và kích hoạt `PointReceiver`:
- **Insert `score_logs`**: Tạo một log cộng điểm (nếu trả lời đúng). Dữ liệu log bao gồm `user_id`, `score_change` (số điểm kiếm được), và `reason` ("Flashcard Review").
- **Update bảng `users`**: Cộng `score_change` vào `total_score` của người dùng.
- **Chuỗi học tập (Streak)**: Controller tự động cập nhật bảng `user_streaks`, có thể tăng `current_streak` nếu đây là hoạt động đầu tiên trong ngày.

## 4. Trạng Thái Phiên Học (`learning_sessions`)
**Thuộc module: `session`**

Toàn bộ quá trình đánh giá thường diễn ra trong một **Session**. Khi một đánh giá hoàn tất:
- **Session Progress**: Bảng `learning_sessions` được cập nhật. Cột `processed_item_ids` (định dạng JSON) sẽ được append ID của flashcard vừa đánh giá vào để đánh dấu là đã học.
- **Session Stats**: Cập nhật tăng `correct_count` hoặc `incorrect_count` tùy thuộc vào kết quả `rating`.
- **Xác định trạng thái hoàn thành**: Nếu số lượng `processed_item_ids` bằng `total_items`, `status` chuyển thành `completed` và trigger cấp thêm bonus (nếu có).

---

### Tóm Lược (Executive Summary)
**Một cú click Rating Flashcard sẽ sinh ra:**
1. `UPDATE item_memory_states` -> Cập nhật lịch FSRS.
2. `INSERT study_logs` -> Lưu file log siêu chi tiết (kèm snapshot).
3. `UPDATE learning_sessions` -> Cập nhật tiến độ Session.
4. `INSERT score_logs` -> Ghi nhận điểm thưởng.
5. `UPDATE users` -> Tổng điểm cá nhân tăng lên.
