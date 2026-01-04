# Cấu Trúc Cơ Sở Dữ Liệu (Database Schema)

Tài liệu này mô tả chi tiết các Models (Bảng) trong cơ sở dữ liệu của ứng dụng, bao gồm ý nghĩa của từng bảng và các trường thông tin quan trọng.

---

## 1. Người Dùng & Cấu Hình (User & Settings)

### 1.1. Bảng `users` (Model: `User`)
Lưu trữ thông tin tài khoản người dùng chính.

*   `user_id` (PK): ID duy nhất của người dùng.
*   `username`: Tên đăng nhập.
*   `email`: Địa chỉ email.
*   `password_hash`: Mật khẩu đã mã hóa.
*   `user_role`: Vai trò (`admin`, `user`, `free`).
*   `total_score`: Tổng điểm thưởng (Diamond) tích lũy được.
*   `last_preferences` (JSON): Lưu cấu hình cá nhân (ví dụ: số nút flashcard).
*   *Quan hệ*:
    *   1-1 với `user_sessions`.
    *   1-n với `learning_progress`.
    *   1-n với `review_logs`.

### 1.2. Bảng `user_sessions` (Model: `UserSession`)
Lưu trạng thái phiên làm việc ngắn hạn (Transient State). Tách biệt khỏi bảng `users` để tối ưu hiệu năng.

*   `user_id` (PK/FK): ID người dùng.
*   `current_flashcard_container_id`: Bộ flashcard đang học hiện tại.
*   `current_quiz_container_id`: Bộ câu hỏi đang thi hiện tại.
*   `current_flashcard_mode`: Chế độ flashcard (`basic`, `cram`...).
*   `current_quiz_mode`: Chế độ quiz (`standard`, `battle`...).

### 1.3. Bảng `user_container_states` (Model: `UserContainerState`)
Lưu cấu hình riêng của người dùng cho từng Bộ học tập (Container).

*   `user_id` (FK): Người dùng.
*   `container_id` (FK): Bộ học tập.
*   `is_favorite`: Đánh dấu yêu thích.
*   `is_archived`: Đánh dấu lưu trữ.
*   `settings` (JSON): Cấu hình chi tiết (ví dụ: filter, sort cho bộ này).

---

## 2. Nội Dung Học Tập (Learning Content)

### 2.1. Bảng `learning_containers` (Model: `LearningContainer`)
Đại diện cho một bộ học tập (Course, Deck, Quiz Set).

*   `container_id` (PK): ID bộ học.
*   `title`: Tên bộ học.
*   `container_type`: Loại (`flashcard`, `quiz`, `course`...).
*   `media_image_folder` / `media_audio_folder`: Đường dẫn thư mục chứa tài nguyên media.
*   `ai_settings` (Property): Cấu hình AI (prompt, capabilities).

### 2.2. Bảng `learning_items` (Model: `LearningItem`)
Đại diện cho một đơn vị kiến thức nhỏ nhất (Một từ vựng, một câu hỏi).

*   `item_id` (PK): ID item.
*   `container_id` (FK): Thuộc về bộ nào.
*   `item_type`: Loại item (`FLASHCARD`, `QUIZ_MCQ`...).
*   `content` (JSON): Nội dung chi tiết.
    *   *Flashcard*: `{ "front": "...", "back": "...", "image": "..." }`
    *   *Quiz*: `{ "question": "...", "options": [...], "answer": "..." }`
*   `ai_explanation`: Giải thích tự động bởi AI.
*   `search_text`: Văn bản thuần túy dùng để tìm kiếm.

---

## 3. Tiến Độ & Dữ Liệu Học Tập (Progress & Data)

### 3.1. Bảng `learning_progress` (Model: `LearningProgress`)
Bảng lõi lưu trữ tiến độ SRS (Lặp lại ngắt quãng) của người dùng.

*   `progress_id` (PK): ID tiến độ.
*   `user_id` (FK): Người dùng.
*   `item_id` (FK): Item đang học.
*   `learning_mode`: Chế độ học (`flashcard`, `quiz`, `memrise`...).
    *   *Lưu ý*: Một item có thể có nhiều dòng progress cho các mode khác nhau.
*   **SRS Fields (SM-2 Algorithm):**
    *   `status`: Trạng thái (`new`, `learning`, `reviewing`, `mastered`).
    *   `box` / `interval`: Khoảng cách ôn tập (phút/ngày).
    *   `easiness_factor`: Hệ số dễ nhớ.
    *   `repetitions`: Số lần đã học.
    *   `due_time`: Thời gian cần ôn tập tiếp theo.
*   `mastery`: Độ thành thạo (0.0 - 1.0) dùng cho tính Memory Power.

### 3.2. Bảng `review_logs` (Model: `ReviewLog`)
"Hộp đen" ghi lại lịch sử từng lần học chi tiết (Log).

*   `log_id` (PK): ID log.
*   `timestamp`: Thời gian học.
*   `review_type`: Loại bài học (`flashcard`, `quiz`...).
*   `rating`: Đánh giá của người dùng (0-5 cho Flashcard).
*   `is_correct`: Đúng/Sai (cho Quiz).
*   `duration_ms`: Thời gian suy nghĩ (milliseconds).
*   `score_change`: Điểm số đạt được trong lần này.

### 3.3. Bảng `score_logs` (Model: `ScoreLog`)
Lịch sử biến động điểm thưởng (Gamification).

*   `log_id` (PK): ID log.
*   `score_change`: Số điểm cộng/trừ.
*   `reason`: Lý do (ví dụ: "Flashcard Answer", "Daily Bonus").

---

## 4. Sơ Đồ Quan Hệ (Relationship Diagram)

*   `User` 1 --- n `LearningProgress` n --- 1 `LearningItem`
*   `User` 1 --- n `ReviewLog` n --- 1 `LearningItem`
*   `LearningContainer` 1 --- n `LearningItem`

---
*Tài liệu được cập nhật ngày: 04/01/2026*
