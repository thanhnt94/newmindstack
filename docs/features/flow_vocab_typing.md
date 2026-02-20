# Luồng Xử Lý Database Khi Trả Lời: Vocab Typing

Chế độ học **Typing (Luyện Gõ Cụm Từ)** yêu cầu độ chính xác câu trả lời từ người dùng. Hệ thống sẽ so sánh từng ký tự người dùng gõ với bộ dữ liệu hệ thống (sau khi loại bỏ dấu câu, khoảng trắng thừa...).

Quá trình này đi qua các module: `vocabulary.typing`, `session`, `fsrs`, `gamification`, và `learning_history`.

---

## 1. So Khớp Đáp Án & Session Manager

Khi người dùng nhấn Submit chuỗi văn bản đã gõ (ví dụ `user_input="apple"`), frontend gửi nó cho API của `TypingSessionManager`.
- So khớp (`fuzzy_match` hoặc `exact_match`) diễn ra ở cấp Memory của trình duyêt và Python.
- Dựa trên độ lệch (Levenshtein Distance) hoặc khớp 100%, hệ thống tự động sinh ra một mức `rating` thích hợp.
  - **Khớp 100%**: `rating = 3` (Good) hoặc `rating = 4` (Easy) nếu quá nhanh.
  - **Gần đúng (Typo 1-2 ký tự)**: Thường là `rating = 2` (Hard).
  - **Sai lệch nhiều / Submit rỗng**: `rating = 1` (Again).

Bảng `learning_sessions`:
- Cập nhật số câu `correct_count` hoặc `incorrect_count`.
- Cột `processed_item_ids` (định dạng JSON) lưu Item ID vừa được nạp.
- `last_activity` = datetime.utcnow().

## 2. Trạng Thái Trí Nhớ (FSRS)
**Thuộc module: `fsrs`**

Typing cung cấp tín hiệu bộ nhớ (Recall) rất mạnh, mạnh hơn cả Flashcard thông thường, do đó sự tương tác với FSRS diễn ra trọn vẹn:
- Tương tự Flashcard, cái `rating` vừa được sinh ngầm (implicit) ở bước 1 sẽ được bọc lại trong `TypingInterface` và ném sang `FSRSInterface.process_review()`.
- Bảng `item_memory_states` được `UPDATE`:
  - `stability`, `difficulty` thay đổi dựa trên mô hình DSR.
  - Chuyển `state` sang Review, hoặc Relearning nếu gõ sai (rating 1).
  - `due_date` được tính lại đẩy lịch ôn tập cho cụm từ này ra xa.

## 3. Nhật Ký Nghiên Cứu (`study_logs`)
**Thuộc module: `learning_history`**

Vì đặc trưng gõ chữ, bảng `study_logs` sẽ lưu giữ những sai lầm (typo) của người dùng làm tư liệu huấn luyện sau này (hoặc chỉ để user xem lại nhật ký gõ sai - Typo History).
- **Insert `study_logs`**:
  - `user_answer`: Chứa trọn vẹn văn bản nhập tay của người dùng (`"appl"`, `"aple"`).
  - `is_correct`: Do logic so khớp quyết định.
  - `rating`: Bằng mức độ đánh giá ẩn (1-4).
  - Cột `fsrs_snapshot`: Sao chép y hệt `stability`/`difficulty` hiện tại.
  - `review_duration`: Thời gian gõ. Nếu > 15-20 giây, có thể bị trừ Time Bonus trong Gamification.

## 4. Điểm Số Tuyệt Đối (`score_logs`)
**Thuộc module: `gamification`**

- Tín hiệu `typing_answered.send()` kích hoạt module `gamification`.
- Do tính chất khó của Typing, **Hệ số nhân điểm (Multiplier)** cho chế độ Typing thường cao hơn MCQ hay Flashcard (ví dụ x1.5 điểm cơ bản).
- **Tạo bản ghi `score_logs`** với lý do "Typing Correct". Điểm số được thiết kế gồm Cơ Bản (Base) + Thưởng Typing Khó (Hard Mode Bonus).
- Tổng thu nhập `score_change` được cập nhật chèn đè lên `users.total_score`. Chuỗi `user_streaks` cũng được tăng nếu đây là lần gõ đúng chuỗi (streak).

---

### Tóm Lược (Executive Summary)
**Submit cụm từ "Hello World" sẽ sinh ra:**
1. Thuật toán phân tích chuỗi văn bản -> Đổi văn bản thành Rating 1->4.
2. `UPDATE learning_sessions` -> Chuyển Item sang processed.  
3. `UPDATE item_memory_states` -> Feed Rating ngầm đó vào FSRS để lên lịch. Gõ sai (Rating 1) -> Trượt về Relearning.
4. `INSERT study_logs` -> Lưu Cụm từ gốc mà người dùng vừa gõ để có lịch sử Typo.
5. `INSERT score_logs` -> Cộng điểm x1.5 vì chế độ khó. Tăng `total_score`.
