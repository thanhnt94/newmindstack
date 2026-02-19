# Tài liệu Cấu trúc Cơ sở dữ liệu MindStack

Tài liệu này mô tả chi tiết các bảng (tables), các cột (columns) và mục đích sử dụng của chúng trong hệ thống MindStack. Cấu trúc được tổ chức theo module.

## 1. Core Models (Learning Core)
Các model cốt lõi quản lý nội dung học tập chung (Course, Flashcard, Quiz).

### 1.1 `learning_containers` (Bảng chứa nội dung học tập)
Bảng cha (Polymorphic Parent) cho tất cả các loại bộ sưu tập nội dung học tập (Course, Flashcard Set, Quiz Set).
- **`container_id`**: (PK, Integer) ID duy nhất của container.
- **`creator_user_id`**: (Integer) ID người dùng tạo container.
- **`container_type`**: (String) Loại container (Discriminator): `COURSE`, `FLASHCARD_SET`, `QUIZ_SET`, `BASE_CONTAINER`.
- **`title`**: (String) Tiêu đề của container.
- **`description`**: (Text) Mô tả chi tiết.
- **`cover_image`**: (String) URL ảnh bìa.
- **`tags`**: (String) Các nhãn phân loại (comma separated).
- **`is_public`**: (Boolean) Trạng thái công khai của content.
- **`created_at`**: (DateTime) Thời gian tạo.
- **`updated_at`**: (DateTime) Thời gian cập nhật gần nhất.
- **`ai_prompt`**: (Text) Prompt tùy chỉnh cho AI khi sinh nội dung trong container này.
- **`ai_capabilities`**: (JSON) Các khả năng AI được bật cho container này.
- **`media_image_folder`**, **`media_audio_folder`**: (String) Đường dẫn thư mục chứa media.
- **`settings`**: (JSON) Cấu hình tùy chỉnh khác.

### 1.2 `learning_items` (Bảng phần tử học tập)
Bảng cha (Polymorphic Parent) cho các phần tử nội dung cụ thể (Flashcard, Lesson, Quiz Question).
- **`item_id`**: (PK, Integer) ID duy nhất của item.
- **`container_id`**: (FK, Integer) Thuộc về container nào.
- **`group_id`**: (FK, Integer) Thuộc về nhóm nào (nếu có, xem `learning_groups`).
- **`item_type`**: (String) Loại item (Discriminator): `FLASHCARD`, `LESSON`, `QUIZ_MCQ`.
- **`content`**: (JSON) Nội dung chi tiết của item (ví dụ: `{front: "...", back: "..."}` cho flashcard).
- **`order_in_container`**: (Integer) Thứ tự sắp xếp trong container.
- **`custom_data`**: (JSON) Dữ liệu tùy chỉnh mở rộng.
- **`search_text`**: (Text) Văn bản được index để phục vụ tìm kiếm.

### 1.3 `learning_groups`
Nhóm các learning items lại với nhau (ví dụ: Unit, Chapter trong Course).
- **`group_id`**: (PK, Integer) ID nhóm.
- **`container_id`**: (FK, Integer) Thuộc về container nào.
- **`group_type`**: (String) Loại nhóm.
- **`content`**: (JSON) Metadata của nhóm (tiêu đề, mô tả...).

### 1.4 `user_container_states`
Lưu trạng thái tương tác của người dùng với một container (Đã thích, Đã ẩn, Lần cuối truy cập).
- **`id`**: (PK, Integer) ID.
- **`user_id`**: (FK, Integer) Người dùng.
- **`container_id`**: (FK, Integer) Container.
- **`is_archived`**: (Boolean) Đã lưu trữ (ẩn) hay chưa.
- **`is_favorite`**: (Boolean) Đánh dấu yêu thích.
- **`last_accessed`**: (DateTime) Lần cuối truy cập.
- **`settings`**: (JSON) Cài đặt cá nhân cho container này.

### 1.5 `item_memory_states` (FSRS & Tiến độ học tập)
Lưu trữ tiến độ học tập chi tiết của người dùng đối với từng Item, sử dụng thuật toán FSRS-5. (Thay thế bảng `learning_progress` cũ).
- **`state_id`**: (PK, Integer).
- **`user_id`**: (FK, Integer).
- **`item_id`**: (FK, Integer).
- **`stability`**: (Float) Độ ổn định của trí nhớ.
- **`difficulty`**: (Float) Độ khó của item.
- **`state`**: (Integer) Trạng thái FSRS (0: New, 1: Learning, 2: Review, 3: Relearning).
- **`due_date`**: (DateTime, index) Thời gian cần ôn tập tiếp theo.
- **`last_review`**: (DateTime) Lần ôn tập gần nhất.
- **`repetitions`, `lapses`**: (Integer) Số lần lặp lại, số lần quên.
- **`streak`, `incorrect_streak`**: (Integer) Chuỗi đúng/sai liên tiếp.
- **`times_correct`, `times_incorrect`**: (Integer) Tổng số lần đúng/sai.
- **`data`**: (JSON) Dữ liệu tùy chỉnh khác (ví dụ: `note`, `markers`, `completion_percentage`).
- **`created_at`, `updated_at`**: (DateTime) Thời gian tạo và cập nhật.

### 1.6 `learning_sessions`
Lưu trữ thông tin về các phiên học (Session) đang diễn ra hoặc đã kết thúc.
- **`session_id`**: (PK, Integer).
- **`user_id`**: (FK, Integer).
- **`learning_mode`**: (String) Chế độ học (flashcard, typing, etc.).
- **`mode_config_id`**: (String) ID cấu hình chế độ học.
- **`set_id_data`**: (JSON) Danh sách các set ID tham gia session.
- **`status`**: (String) Trạng thái session (active, completed).
- **`total_items`, `correct_count`, `incorrect_count`, `vague_count`**: Thống kê kết quả session.
- **`points_earned`**: (Integer) Tổng điểm kiếm được trong session.
- **`processed_item_ids`**: (JSON) Danh sách các item đã học.
- **`current_item_id`**: (FK, Integer) Item đang hiển thị.
- **`session_data`**: (JSON) Dữ liệu trạng thái tạm thời của session.
- **`start_time`, `end_time`, `last_activity`**: Các mốc thời gian.

---

## 2. Authentication Module (Auth)

### 2.1 `users`
Bảng thông tin người dùng chính.
- **`user_id`**: (PK, Integer).
- **`username`**, **`email`**: (String) Tên đăng nhập và Email (Duy nhất).
- **`password_hash`**: (String) Mật khẩu đã mã hóa.
- **`user_role`**: (String) Vai trò (admin, user, free...).
- **`total_score`**: (Integer) Tổng điểm tích lũy.
- **`last_seen`**: (DateTime) Lần cuối hoạt động.
- **`avatar_url`**: (String) Đường dẫn ảnh đại diện.
- **`last_preferences`**: (JSON) Lưu cài đặt cá nhân của người dùng.

### 2.2 `user_sessions`
Lưu trạng thái phiên làm việc ngắn hạn (Transient state).
- **`user_id`**: (PK, FK) Người dùng.
- **`current_flashcard_container_id`**: (FK) Container flashcard đang chọn.
- **`current_quiz_container_id`**: (FK) Container quiz đang chọn.
- **`current_course_container_id`**: (FK) Course đang chọn.
- **`flashcard_button_count`**: (Integer) Cấu hình số nút khi học flashcard (3, 4, 6).

---

## 3. AI Module

### 3.1 `api_keys`
Quản lý các API Key của các nhà cung cấp AI (Google Gemini, OpenAI...).
- **`key_id`**: (PK, Integer).
- **`provider`**: (String) Nhà cung cấp (gemini, openai...).
- **`key_value`**: (String) Giá trị Key.
- **`is_active`, `is_exhausted`**: Trạng thái của Key.

### 3.2 `ai_token_logs`
Ghi log việc sử dụng AI để theo dõi chi phí và token.
- **`log_id`**: (PK, Integer).
- **`provider`, `model_name`**: Model AI được dùng.
- **`input_tokens`, `output_tokens`**: Số lượng token tiêu thụ.
- **`feature`**: Tính năng nào đã gọi AI (explanation, chat...).

### 3.3 `ai_cache`
Cache lại các phản hồi từ AI để tiết kiệm chi phí.
- **`cache_id`**: (PK, Integer).
- **`prompt_hash`**: (String) Hash của prompt đầu vào (để tìm kiếm nhanh).
- **`response_text`**: (Text) Nội dung AI trả về.

### 3.4 `ai_contents` (AI Explanations)
Lưu trữ nội dung do AI tạo ra cho các Learning Item (Giải thích, Ví dụ, Dịch nghĩa...).
- **`content_id`**: (PK, Integer).
- **`item_id`**: (FK, Integer) Gắn với learning item nào.
- **`content_type`**: (String) Loại nội dung (`explanation`, `example`, `mnemonic`).
- **`content_text`**: (Text) Nội dung văn bản (hỗ trợ Markdown/BBCode).
- **`is_primary`**: (Boolean) Có phải nội dung chính hiển thị mặc định không.
- **`created_at`, `updated_at`**: (DateTime) Thời gian tạo và cập nhật.

---

## 4. Collab Module (Collaborative Learning)

### 4.1 `flashcard_collab_rooms` & `quiz_battle_rooms`
Phòng học nhóm (Flashcard) và phòng thi đấu (Quiz Battle).
- **`room_id`**: (PK).
- **`room_code`**: (String) Mã phòng để tham gia.
- **`host_user_id`**: (FK) Chủ phòng.
- **`container_id`**: (FK) Nội dung học tập của phòng.
- **`status`**: (String) Trạng thái phòng (lobby, active, completed).

### 4.2 `flashcard_collab_participants` & `quiz_battle_participants`
Danh sách người tham gia trong phòng.
- **`participant_id`**, **`room_id`**, **`user_id`**.
- **`score` / `correct_answers`**: Điểm số trong phòng.

---

## 5. Gamification Module

### 5.1 `badges` & `user_badges`
Hệ thống huy hiệu.
- **`Badge`**: Định nghĩa huy hiệu, điều kiện đạt được (`condition_type`, `condition_value`).
- **`UserBadge`**: Lưu huy hiệu người dùng đã đạt được.

### 5.2 `score_logs`
Lịch sử chi tiết việc thay đổi điểm số của người dùng.
- **`log_id`**: (PK, Integer).
- **`user_id`**: (FK, Integer).
- **`item_id`**: (FK, Integer, Optional) Gắn với câu hỏi cụ thể.
- **`item_type`**: (String, Optional) Loại item (FLASHCARD, QUIZ, etc.).
- **`score_change`**: (Integer) Số điểm thay đổi (+ hoặc -).
- **`reason`**: (String) Lý do thay đổi (ví dụ: "Flashcard Answer").
- **`timestamp`**: (DateTime, index) Thời gian ghi nhận.

### 5.3 `user_streaks`
Theo dõi chuỗi học tập liên tiếp (Streak) của người dùng.
- **`user_id`**: (PK, FK, Integer).
- **`current_streak`**: (Integer) Chuỗi hiện tại.
- **`longest_streak`**: (Integer) Chuỗi kỷ lục.
- **`last_activity_date`**: (Date) Ngày hoạt động gần nhất để tính streak.
- **`updated_at`**: (DateTime) Thời gian cập nhật.

---

## 6. Goals Module

### 6.1 `goals`
Định nghĩa các mục tiêu có sẵn (ví dụ: "Review 50 cards daily").
- **`goal_code`**: Mã mục tiêu.
- **`metric`**: Chỉ số cần đo lường.
- **`default_target`**: Mục tiêu mặc định.

### 6.2 `user_goals` & `goal_progress_logs`
Mục tiêu cụ thể của người dùng và tiến độ thực hiện theo ngày.

---

## 7. History Module (Learning History)

### 7.1 `study_logs`
Lưu chi tiết từng tương tác học tập (Click trả lời, Đánh giá thẻ...).
- **`log_id`**: (PK, Integer).
- **`user_id`, `item_id`**: (FK, Integer).
- **`timestamp`**: (DateTime, index) Thời gian log.
- **`rating`**: Đánh giá (1-4).
- **`user_answer`**: (Text) Nội dung câu trả lời của người dùng.
- **`is_correct`**: (Boolean) Đúng/Sai.
- **`review_duration`**: (Integer) Thời gian phản hồi (ms).
- **`session_id`**: (FK, Integer) Thuộc session nào.
- **`container_id`**: (FK, Integer) Thuộc container nào.
- **`learning_mode`**: (String) Chế độ học khi log được tạo.
- **`fsrs_snapshot`**: (JSON) Lưu trạng thái FSRS (stability, difficulty, interval) tại thời điểm học.
- **`gamification_snapshot`**: (JSON) Lưu chi tiết điểm số (base score, multipliers, breakdown).
- **`context_snapshot`**: (JSON) Lưu các thông ngữ cảnh khác.

---

## 8. Notification Module

### 8.1 `notifications`
Thông báo nội bộ trong hệ thống.
- **`title`, `message`, `type`**.
- **`is_read`**: Đã đọc chưa.

### 8.2 `push_subscriptions`
Đăng ký nhận thông báo đẩy (Web Push) trên trình duyệt.

---

## 9. Ops Module

### 9.1 `background_tasks` & `background_task_logs`
Quản lý và theo dõi các tác vụ chạy ngầm (Celery tasks).

---

## 10. Stats Module

### 10.1 `user_metrics` & `daily_stats`
Thống kê tổng hợp và thống kê theo ngày (Dashboard reporting).

---

## 11. Notes Module

### 11.1 `notes`
Hệ thống ghi chú đa năng, có thể gắn vào bất kỳ thực thể nào.
- **`reference_type`**, **`reference_id`**: Xác định thực thể được ghi chú (ví dụ: `item`, `container`).
- **`content`**: Nội dung ghi chú.
