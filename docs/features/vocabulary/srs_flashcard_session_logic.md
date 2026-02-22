# Chi tiết Phiên Học Flashcard SRS (SRS Flashcard Session Detail)

Tài liệu này mô tả chi tiết cách thức hoạt động của một phiên học Flashcard sử dụng thuật toán **SRS (Spaced Repetition System)** trong MindStack, bao gồm logic lựa chọn thẻ, vòng đời phiên học và cơ chế cập nhật trạng thái bộ nhớ.

---

## 1. Thành Phần Cốt Lõi (Core Components)

Phiên học SRS được vận hành bởi sự phối hợp của 4 thành phần chính:

1.  **`FlashcardEngine`**: Quản lý logic trung tâm, điều phối việc lấy thẻ (`get_next_batch`) và xử lý câu trả lời (`process_answer`).
2.  **`FlashcardQueryBuilder`**: Xây dựng các truy vấn CSDL phức tạp để lọc và sắp xếp thẻ dựa trên trạng thái FSRS.
3.  **`FSRSInterface`**: Cổng giao tiếp với module FSRS để tính toán và lưu trữ các chỉ số bộ nhớ (Stability, Difficulty, Due Date).
4.  **`LearningSession` (Module Session)**: Ghi lại tiến trình của phiên học, hỗ trợ tính năng học tiếp (resume) khi người dùng quay lại.

---

## 2. Logic Lựa Chọn Thẻ (Selection Logic)

Trong chế độ SRS, hệ thống không chọn thẻ ngẫu nhiên. Quy trình chọn thẻ của `FlashcardQueryBuilder` tuân theo thứ tự ưu tiên sau:

### Bước 1: Lọc Thẻ "Cần Ôn" (Due Items)
- **Tiêu chuẩn**: Thẻ có `due_date <= now()` hoặc mức độ ghi nhớ (**Retrievability**) giảm xuống dưới **90%**.
- **Sắp xếp**: Thẻ cũ nhất (quá hạn lâu nhất) hoặc có Retrievability thấp nhất thường được ưu tiên.
- **Xáo trộn**: Các thẻ đến hạn được xáo trộn ngẫu nhiên (Shuffle) để tránh việc người học ghi nhớ theo thứ tự thay vì nội dung.

### Bước 2: Bổ sung Thẻ "Mới" (New Items)
- Nếu số lượng thẻ đến hạn ít hơn `card_limit` của phiên học, hệ thống sẽ lấy thêm thẻ ở trạng thái `NEW` (chưa từng học).
- **Sắp xếp**: Thẻ mới được lấy theo thứ tự nhập liệu (Sequential) để đảm bảo lộ trình học tập logic.

### Bước 3: Cơ chế Giới hạn (Limit)
- Phiên học sẽ dừng lại khi đạt đến giới hạn số lượng thẻ đã cấu hình (ví dụ: 20 thẻ/phiên).

---

## 3. Vòng Đời Phiên Học (Session Lifecycle)

1.  **Khởi tạo (Initialization)**: 
    - Khi bắt đầu, một bản ghi `learning_sessions` được tạo với `status="active"`.
    - Danh sách `item_ids` được xác định và lưu vào session.
2.  **Thực thi (Execution)**:
    - Client (Trình duyệt) gửi yêu cầu lấy batch thẻ đầu tiên.
    - Sau mỗi thẻ được trả lời, ID của thẻ đó được thêm vào mảng `processed_item_ids` trong DB.
    - Nếu người dùng tắt trình duyệt, hệ thống sẽ sử dụng `processed_item_ids` để lọc bỏ các thẻ đã làm khi người dùng quay lại.
3.  **Hoàn thành (Completion)**:
    - Khi `processed_item_ids` đủ số lượng thẻ đã định, session chuyển sang `status="completed"`.

---

## 4. Xử lý Câu trả lời & Cập nhật FSRS

Mỗi khi người dùng chọn một trong 4 nút đánh giá (Again, Hard, Good, Easy), một chuỗi các hành động diễn ra tại Backend:

| Rating | Tác động (DSR Model) | Trạng thái tiếp theo |
| :--- | :--- | :--- |
| **1 - Again** | Stability giảm mạnh, Difficulty tăng. | `RELEARNING` |
| **2 - Hard** | Stability tăng nhẹ, Difficulty tăng nhẹ. | `REVIEW` |
| **3 - Good** | Stability tăng ổn định, Difficulty giảm nhẹ. | `REVIEW` |
| **4 - Easy** | Stability nhảy vọt, Difficulty giảm mạnh. | `REVIEW` |

### Quy trình Dữ liệu (Data Flow):
1.  `FSRSInterface` tính toán `Stability`, `Difficulty` và `Due Date` mới.
2.  `item_memory_states` được cập nhật record tương ứng.
3.  `study_logs` ghi lại chi tiết lượt học kèm snapshot chỉ số FSRS tại thời điểm đó.
4.  `score_logs` ghi nhận điểm số dựa trên chất lượng trả lời và streak.
5.  Signal `card_reviewed` được phát ra để các module khác (như Gamification) cập nhật rank/thành tích.

---

## 5. Các Chế độ mở rộng (Extended Modes)

Mặc dù SRS là chế độ mặc định và thông minh nhất, `FlashcardEngine` còn hỗ trợ:
- **Sequential**: Học theo thứ tự nhập liệu, không quan tâm FSRS.
- **Shuffled**: Học ngẫu nhiên toàn bộ bộ thẻ.
- **Cram**: Ôn tập tập trung vào các thẻ đã học nhưng đang có độ khó cao.

---

> [!TIP]
> Để đạt hiệu quả cao nhất, người dùng nên hoàn thành toàn bộ thẻ "Đến hạn" mỗi ngày. Thuật toán FSRS v5 sẽ tự động giãn cách các thẻ đã thuộc và kéo gần các thẻ khó, giúp giảm tải khối lượng học tập mà vẫn giữ được trí nhớ bền vững.
