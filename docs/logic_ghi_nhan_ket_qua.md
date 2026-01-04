# Logic Ghi Nhận Kết Quả Học Tập (Learning Result Recording Logic)

Tài liệu này mô tả chi tiết logic ghi nhận kết quả cho mỗi câu trả lời của người dùng trong các chế độ học tập (Vocabulary và Quiz).

---

## 1. Vocabulary (Học Từ Vựng)

Bao gồm các chế độ: **Flashcard** (chính), và các chế độ phụ trợ (Review Mode, Cram Mode).

### 1.1. Flashcard (Học thẻ)

Đây là chế độ học chính áp dụng thuật toán Lặp lại ngắt quãng (Spaced Repetition System - SRS).

**Quy trình ghi nhận:**

1.  **Input (Đầu vào):**
    *   `item_id`: ID của từ vựng.
    *   `quality`: Mức độ ghi nhớ do người dùng tự đánh giá (0-5).
        *   `0-1`: Quên/Sai (Incorrect) - Cần học lại ngay.
        *   `2-3`: Mơ hồ/Khó (Hard/Vague) - Nhớ mang máng, cần ôn lại sớm.
        *   `4-5`: Nhớ/Dễ (Correct/Easy) - Đã thuộc, giãn thời gian ôn tập.

2.  **Processing (Xử lý - `FlashcardEngine.process_answer`):**
    *   **B1: Lấy dữ liệu cũ**: Truy vấn `LearningProgress` hiện tại của thẻ đó (interval, EF...).
    *   **B2: Tính toán SRS (`SrsService.update_unified`)**:
        *   Sử dụng kết hợp thuật toán SM-2 cải tiến và Memory Power.
        *   Tính `Next Review` (thời gian ôn tập tiếp theo).
        *   Tính `Memory Power` (Độ bền trí nhớ: 0-100%).
    *   **B3: Chấm điểm (Gaming Score)**:
        *   Cộng điểm Vàng/Kim cương vào `UserContainerState` và `User.total_score`.

3.  **Output (Lưu trữ):**
    *   Cập nhật `learning_progress`: Lưu trạng thái SRS mới.
    *   Tạo bản ghi `review_logs`: Lưu lịch sử lần học này.

---

## 2. Quiz (Trắc Nghiệm - MCQ)

Bao gồm các chế độ: **Quiz Single** và **Quiz Batch**.

**Quy trình ghi nhận:**

1.  **Input (Đầu vào):**
    *   `item_id`: ID của câu hỏi.
    *   `user_answer`: Đáp án người dùng chọn (Text hoặc ID option - Ví dụ: "apple").

2.  **Processing (Xử lý - `QuizEngine.check_answer`):**
    *   **B1: Kiểm tra đáp án**: So sánh với `correct_answers` trong DB (Ví dụ: `["apple", "Apple"]`).
    *   **B2: Quy đổi sang Quality** (nếu bật SRS):
        *   Đúng -> Quality = 4 (Good).
        *   Sai -> Quality = 1 (Again).
    *   **B3: Tính điểm (Score)**: Cộng điểm dựa trên kết quả Đúng/Sai.

3.  **Output (Lưu trữ):**
    *   Cập nhật `learning_progress` (với `learning_mode='quiz'`).
    *   Lưu `review_logs`.

---

## 3. Ví Dụ Minh Họa Dữ Liệu (Database Examples)

Dưới đây là ví dụ về dữ liệu thực tế được ghi vào database cho 2 trường hợp phổ biến.

### Trường hợp 1: Flashcard - Người dùng bấm "Khó" (Hard)

**Hành động:** Người dùng ôn tập thẻ "Hello", cảm thấy khó nhớ nên bấm nút **Khó**.
**Input:** `item_id=101`, `quality=2` (Hard).

**Dữ liệu cập nhật trong Database:**

1.  **Bảng `review_logs`** (Ghi Nhật Ký):
    ```json
    {
      "id": 505,
      "user_id": 1,
      "item_id": 101,
      "review_type": "flashcard",
      "rating": 2,           // Tương ứng mức 'Hard'
      "duration_ms": 3500,   // Thời gian xem thẻ: 3.5s
      "timestamp": "2026-01-04T12:00:00Z"
    }
    ```

2.  **Bảng `learning_progress`** (Cập nhật Tiến độ cho `mode='flashcard'`):
    *   **Trước khi học:** `interval=10 ngày`, `repetitions=3`, `easiness_factor=2.5`.
    *   **Sau khi học (Hard):**
        ```json
        {
          "id": 88,
          "item_id": 101,
          "learning_mode": "flashcard",
          "interval": 12,          // Interval tăng ít do bấm Khó (ví dụ: nhân 1.2)
          "easiness_factor": 2.35, // EF giảm nhẹ do thấy khó (-0.15)
          "repetitions": 4,        // Số lần học tăng lên
          "status": "learning",
          "due_time": "2026-01-16T12:00:00Z", // Due date = Today + 12 days
          "last_reviewed": "2026-01-04T12:00:00Z",
          "memory_power": 0.45     // Độ bền trí nhớ giảm/tăng tùy thuật toán
        }
        ```

---

### Trường hợp 2: Quiz - Người dùng chọn Đáp Án Đúng

**Hành động:** Người dùng làm câu trắc nghiệm nghĩa của từ "Cat", chọn đáp án "Con mèo".
**Input:** `item_id=202`, `user_answer="Con mèo"` (Đúng).

**Dữ liệu cập nhật trong Database:**

1.  **Bảng `review_logs`** (Ghi Nhật Ký):
    ```json
    {
      "id": 506,
      "user_id": 1,
      "item_id": 202,
      "review_type": "quiz",
      "rating": 4,           // Quy đổi: Đúng -> 4 (Good)
      "duration_ms": 2100,
      "timestamp": "2026-01-04T12:05:00Z"
    }
    ```

2.  **Bảng `learning_progress`** (Cập nhật Tiến độ cho `mode='quiz'`):
    *   *Lưu ý: Dữ liệu này tách biệt hoàn toàn với tiến độ Flashcard của từ "Cat".*
    *   **Trước khi thi:** User chưa từng làm Quiz từ này (`new`).
    *   **Sau khi thi (Đúng):**
        ```json
        {
          "id": 99,
          "item_id": 202,
          "learning_mode": "quiz",
          "interval": 1,           // Lần đầu đúng -> Review lại sau 1 ngày
          "easiness_factor": 2.5,  // Mặc định
          "repetitions": 1,
          "status": "learning",
          "due_time": "2026-01-05T12:05:00Z",
          "last_reviewed": "2026-01-04T12:05:00Z"
        }
        ```

---

## 4. Bảng Tóm Tắt So Sánh Input/Output

| Đặc điểm | Vocabulary (Flashcard) | Quiz (MCQ) |
| :--- | :--- | :--- |
| **Logic Đúng/Sai** | Dựa trên cảm nhận (Quality 0-5) | Dựa trên đáp án hệ thống (Đúng/Sai) |
| **Mục tiêu SRS** | Tối ưu hóa trí nhớ dài hạn | Kiểm tra & Củng cố kiến thức |
| **Ảnh hưởng Review** | Thay đổi lịch ôn tập mạnh mẽ | Có thể ảnh hưởng hoặc không (tùy config) |
| **Điểm thưởng** | Dựa trên Quality (Khó/Dễ) | Dựa trên Kết quả (Đúng/Sai) |

---
*Tài liệu được cập nhật ngày: 04/01/2026*
