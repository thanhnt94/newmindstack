# Tài liệu Kiến trúc Cơ sở Dữ liệu

Tài liệu này trình bày chi tiết kiến trúc cơ sở dữ liệu cho ứng dụng MindStack. Dự án sử dụng **Flask-SQLAlchemy** làm ORM (Object Relational Mapper).

## 1. Tổng quan

Cơ sở dữ liệu được thiết kế xung quanh một mô hình nội dung linh hoạt. Trong khi người dùng và quyền hạn tuân theo cấu trúc quan hệ truyền thống, nội dung học tập cốt lõi (flashcard, bộ câu hỏi) sử dụng một **phương pháp kết hợp**:
*   **Các cột quan hệ** để lập chỉ mục, sắp xếp và khóa ngoại.
*   **Các cột JSON** (`content`) để lưu trữ dữ liệu giáo dục thực tế (câu hỏi, câu trả lời, đường dẫn đa phương tiện). Điều này cho phép thêm các trường mới (như các tùy chọn quiz cụ thể hoặc lời nhắc AI tùy chỉnh) mà không cần chạy các migration cơ sở dữ liệu.

## 2. Các mô hình học tập cốt lõi (`learning.py`)

Đây là các bảng quan trọng nhất cho hệ thống quản lý nội dung.

### `learning_containers`
Đại diện cho một "Bộ" hoặc "Khóa học". Đây là đối tượng cha cho tất cả nội dung.

| Cột | Kiểu dữ liệu | Mô tả |
| :--- | :--- | :--- |
| `container_id` | Integer (PK) | ID duy nhất. |
| `container_type` | String | Giống như Enum: `'FLASHCARD_SET'`, `'QUIZ_SET'`, `'COURSE'`. |
| `title` | String | Tiêu đề của bộ. |
| `creator_user_id`| Integer (FK) | ID của `User` đã tạo. |
| `is_public` | Boolean | Nếu `True`, hiển thị cho tất cả người dùng. |
| `ai_settings` | JSON | Lưu trữ **cũ** cho cấu hình AI. |
| `ai_prompt` | Text | Trường **mới** có cấu trúc cho lời nhắc AI tùy chỉnh. |
| `ai_capabilities`| JSON | Trường **mới** có cấu trúc cho các cờ khả năng (ví dụ: `['supports_pronunciation']`). |
| `media_image_folder` | String | Đường dẫn thư mục gốc cho hình ảnh (ví dụ: `flashcard/n5/images`). |
| `media_audio_folder` | String | Đường dẫn thư mục gốc cho âm thanh. |

### `learning_items`
Đại diện cho một "Thẻ" hoặc "Câu hỏi" đơn lẻ.

| Cột | Kiểu dữ liệu | Mô tả |
| :--- | :--- | :--- |
| `item_id` | Integer (PK) | ID duy nhất. |
| `container_id` | Integer (FK) | Container cha. |
| `item_type` | String | Giống như Enum: `'FLASHCARD'`, `'QUIZ_MCQ'`, `'LESSON'`. |
| `order_in_container` | Integer | Thứ tự sắp xếp (1, 2, 3...). |
| `content` | JSON | **Rất quan trọng:** Lưu trữ dữ liệu thực tế. Cấu trúc thay đổi theo `item_type`. |

#### Cấu trúc JSON: Flashcard (`content`)
```json
{
  "front": "Hello",
  "back": "Xin chào",
  "front_img": "path/to/img.png",
  "back_audio_url": "path/to/audio.mp3",
  "ai_explanation": "Chú thích ngữ pháp chi tiết...",
  "supports_pronunciation": true
}
```

#### Cấu trúc JSON: Quiz (`content`)
```json
{
  "question": "Chọn động từ đúng.",
  "options": {
    "A": "Go",
    "B": "Went",
    "C": "Gone",
    "D": "Going"
  },
  "correct_answer": "B",
  "explanation": "Vì đây là thì quá khứ.",
  "question_image_file": "path/to/q.png"
}
```

### `learning_groups`
Được sử dụng để nhóm các item lại với nhau (ví dụ: một đoạn văn đọc hiểu được chia sẻ bởi 5 câu hỏi).

| Cột | Kiểu dữ liệu | Mô tả |
| :--- | :--- | :--- |
| `group_id` | Integer (PK) | ID duy nhất. |
| `content` | JSON | Lưu trữ dữ liệu được chia sẻ (ví dụ: `{ "text": "Đoạn văn dài...", "external_id": "P1" }`). |

---

## 3. Quản lý Người dùng (`user.py`)

### `users`
Bảng người dùng tiêu chuẩn.

| Cột | Kiểu dữ liệu | Mô tả |
| :--- | :--- | :--- |
| `user_id` | Integer (PK) | ID duy nhất. |
| `username` | String | Tên đăng nhập duy nhất. |
| `user_role` | String | `'admin'`, `'user'`, `'free'`. |
| `total_score` | Integer | Điểm Gamification. |
| `current_*` | FKs | Theo dõi phiên hoạt động hiện tại (ví dụ: `current_flashcard_container_id`). |

### Bảng tiến độ người dùng
Theo dõi trạng thái học tập cho các item cụ thể.

*   **`flashcard_progress`**: Sử dụng logic Hệ thống lặp lại ngắt quãng (SRS).
    *   `easiness_factor` (Float): Hệ số thuật toán Sm-2.
    *   `interval` (Int): Số ngày cho đến lần ôn tập tiếp theo.
    *   `next_due` (DateTime): Thời điểm hiển thị thẻ lại.
*   **`quiz_progress`**: Theo dõi số liệu thống kê hiệu suất.
    *   `times_correct`, `times_incorrect`.
*   **`user_container_states`**: Cài đặt cho từng người dùng đối với một bộ (ví dụ: có được yêu thích không? đã lưu trữ không?).

### `container_contributors`
Quản lý quyền chỉnh sửa (chế độ Cộng tác/Nhóm).
*   Liên kết `user_id` và `container_id` với `permission_level` (ví dụ: `'editor'`).

---

## 4. Hệ thống & Cộng tác (`system.py`, `flashcard_collab.py`)

### `system_settings`
Cấu hình toàn cầu (ví dụ: giới hạn API, chế độ bảo trì) được lưu trữ dưới dạng các cặp Khóa-Giá trị.

### `flashcard_collab_rooms`
Hỗ trợ các phiên học nhóm flashcard theo thời gian thực.
*   `status`: `'lobby'`, `'active'`, `'completed'`.
*   `host_user_id`: Chủ phòng.

### `flashcard_room_progress`
Theo dõi "bộ nhớ" của một phòng cộng tác (trạng thái SRS) độc lập với từng người dùng, cho phép một nhóm tiến bộ cùng nhau.