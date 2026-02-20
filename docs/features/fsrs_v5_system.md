# Hệ Thống FSRS v5 trong MindStack

Tài liệu này giải thích chi tiết về thuật toán **FSRS (Free Spaced Repetition Scheduler) phiên bản 5** được sử dụng trong MindStack để quản lý quá trình ôn tập ngắt quãng (Spaced Repetition) cho người học.

Kiến trúc FSRS của MindStack được thiết kế theo mô hình **Modular Monolith**, tách biệt hoàn toàn Logic tính toán (Engine) với Database (Models) và Framework.

---

## 1. FSRS v5 Là Gì?

FSRS (Free Spaced Repetition Scheduler) là một trong những thuật toán lập lịch ôn tập hiện đại và tối ưu nhất hiện nay dựa trên mô hình **DSR (Difficulty, Stability, Retrievability)**. Khác với thuật toán SuperMemo-2 (SM-2) truyền thống (như Anki mặc định), FSRS v5 sử dụng các công thức tối ưu và mạng nơ-ron nhỏ gọn gọn gọn nhẹ nhắm mục tiêu tối đa hóa hiệu quả ghi nhớ của người dùng thông qua việc dự đoán chính xác khi nào người dùng sắp quên một kiến thức.

### Mô Hình DSR (3 chỉ số cốt lõi)
1. **Difficulty (D - Độ Khó)**: Thể hiện độ khó của một thẻ Flashcard (thang điểm từ 1 đến 10). Giá trị càng cao, thẻ càng khó nhớ.
2. **Stability (S - Sự Ổn Định)**: Thời gian (tính bằng ngày) lưu giữ trí nhớ cho đến khi tỷ lệ nhớ (Retrievability) giảm xuống 90% (R = 0.9). S càng cao, trí nhớ càng bền vững.
3. **Retrievability (R - Khả năng truy xuất)**: Mức độ có thể nhớ được một thông tin tại bất kỳ thời điểm nào (Từ 0% đến 100%). Khi `R` giảm xuống một ngưỡng (ví dụ: < 90%), thẻ cần được đưa ra ôn tập lại.

---

## 2. Bốn Trạng Thái Trí Nhớ (Memory States)

MindStack quản lý 4 trạng thái học tập của một Item (thẻ từ vựng, câu hỏi):

1. **`0 - NEW` (Mới)**: Thẻ chưa từng được học. Các chỉ số S, D đều bằng 0.
2. **`1 - LEARNING` (Đang Học)**: Thẻ đang trong giai đoạn học ban đầu (mới được mở khóa). Khi thẻ chuyển từ `NEW` sang `LEARNING`, hệ thống cấp Stability ban đầu dựa trên đánh giá của người dùng.
3. **`2 - REVIEW` (Ôn Tập)**: Thẻ đã được học qua giai đoạn đầu và bước vào chu kỳ ôn tập ngắt quãng dài hạn.
4. **`3 - RELEARNING` (Học Lại)**: Khi người dùng **Quên (Again)** một thẻ đang ở trạng thái `REVIEW`, nó sẽ rớt xuống trạng thái `RELEARNING`. Sau khi ôn tập thành công, nó quay lại `REVIEW`.

---

## 3. Hệ Thống 4 Nút Đánh Giá (Ratings)

Khi người dùng xem một Flashcard, họ đánh giá chất lượng ghi nhớ của chính mình bằng 4 mức độ:

| Rating | Nút (UI) | Ý nghĩa | Tác động tới FSRS |
| :--- | :--- | :--- | :--- |
| **1** | **Chưa Nhớ (Again)** | Quên hoàn toàn nội dung hoặc sai. | Thẻ vào trạng thái `RELEARNING` (hoặc giữ `LEARNING`). Stability giảm mạnh, Difficulty tăng. |
| **2** | **Khó (Hard)** | Nhớ nhưng mất nhiều thời gian, thấy khó. | Stability tăng nhẹ, Difficulty tăng nhẹ. |
| **3** | **Bình Thường (Good)** | Nhớ tốt, tốc độ vừa phải. | Stability tăng ổn định, Difficulty có xu hướng giảm nhẹ. |
| **4** | **Dễ (Easy)** | Nhớ ngay lập tức, quá dễ. | Thẻ tốt, Stability nhảy vọt (khoảng cách ôn tập lần sau rất xa), Difficulty giảm đáng kể. |

---

## 4. Hiện Thực trong MindStack (Implementation)

Thuật toán FSRS trong MindStack được triển khai tại module `mindstack_app/modules/fsrs/`.

### 4.1. Core Engine: `engine/core.py`
Toàn bộ logic toán học của FSRS v5 nằm trong tầng **Engine**. Engine này được viết dựa trên thư viện chuẩn Python, tuyệt đối độc lập với Flask và SQLAlchemy.

Nó nhận đầu vào là các **DTOs (Data Transfer Objects)** (từ `schemas.py`) và trả về kết quả tính toán:
- Bước 1: Tính toán khoảng cách (interval) dựa trên Rating và State hiện tại.
- Bước 2: Cập nhật `Difficulty` mới.
- Bước 3: Cập nhật `Stability` mới.
- Bước 4: Tính toán `Due Date` (ngày ôn tập tiếp theo).

### 4.2. Database Model: `ItemMemoryState`
Toàn bộ thông tin FSRS của một user cho một item cụ thể được lưu trong bảng (Model) `ItemMemoryState` (`models.py`):

```python
class ItemMemoryState(db.Model):
    __tablename__ = 'item_memory_states'
    
    state_id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, index=True, nullable=False)
    item_id = db.Column(db.Integer, index=True, nullable=False)
    container_id = db.Column(db.Integer, index=True) 

    # FSRS Core
    stability = db.Column(db.Float, default=0.0)
    difficulty = db.Column(db.Float, default=0.0)
    state = db.Column(db.Integer, default=State.New) # 0: New, 1: Learning, 2: Review, 3: Relearning
    
    # Scheduling
    last_review = db.Column(db.DateTime(timezone=True))
    due_date = db.Column(db.DateTime(timezone=True), index=True)
    
    # Stats
    repetitions = db.Column(db.Integer, default=0)
    lapses = db.Column(db.Integer, default=0)
    
    # Metadata
    data = db.Column(db.JSON) # Custom JSON
```

### 4.3. Interface & Service Layer
- **`interface.py`**: Điểm tiếp xúc (Gatekeeper) duy nhất cho việc lấy ra danh sách card Due (cần học), hoặc cập nhật một flashcard khi học viên vừa đánh giá.
- **`services/scheduler_service.py`**: Orchestrator gọi DB lấy `ItemMemoryState`, covert sang `ReviewLogInput` và đưa cho `engine/core.py` xử lý, sau đó lưu kết quả cập nhật về lại DB (`commit`) và bắn Signal `card_reviewed.send()`.

---

## 5. Quy Trình Vận Hành Tiêu Biểu (Happy Path)

1. User vào học một Flashcard. Hệ thống gọi `FSRSInterface.get_due_items(user_id, container_id)` để lấy danh sách cần ôn.
2. User bấm hiển thị đáp án, chọn Button đánh giá là **Good** (Rating = 3) trên Card ID 101.
3. API gọi đến `FSRSInterface.process_review(user_id, 101, 3, duration_ms)`.
4. `SchedulerService` lấy `ItemMemoryState(item_id=101)` tương ứng.
5. Cung cấp snapshot xuống tầng logic thuật toán `engine.calculate(...)`.
6. Tính toán xong, update Model:
   - `last_review` = now()
   - `due_date` = now + interval_days
   - `state` -> REVIEW (nếu đang ở LEARNING).
7. `db.session.commit()`
8. Bắn sự kiện `card_reviewed`. Module `history` và `gamification` lắng nghe để log thành tích người dùng.
