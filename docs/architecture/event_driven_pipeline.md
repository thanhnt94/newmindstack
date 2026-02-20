# Kiến Trúc Hướng Sự Kiện (Event-Driven Pipeline)

Một trong những sức mạnh cốt lõi của kiến trúc **Modular Monolith** trong MindStack là khả năng Decoupling (Tách Nới Lỏng) các Module thông qua **Sự Kiện (Events / Signals)**.

Nếu không có hệ thống Sự kiện, Module A sẽ phải import trực tiếp hàm của Module B và Module C để xử lý hậu quả, dẫn đến mã nguồn bị dính chặt (Spaghetti Code) và Dễ Lỗi (Circular Dependencies).

MindStack giải quyết bài toán này thông qua thư viện `Blinker`.

---

## 1. Triết Lý Thiết Kế (Publish-Subscribe Pattern)

Hệ thống hoạt động theo mô hình **Pub-Sub**:
1. **Publisher (Bên phát)**: Bất cứ khi nào một sự kiện quan trọng xảy ra (VD: User trả lời đúng một Flashcard), Module chịu trách nhiệm chính sẽ lớn tiếng "Thông báo" (Emit/Send) sự kiện đó kèm theo dữ liệu (Payload). Publisher KHÔNG CẦN QUAN TÂM ai sẽ nghe.
2. **Subscriber (Bên nghe)**: Bất kỳ Module nào khác quan tâm đến sự kiện đó có thể đăng ký (Subscribe) để Lắng nghe. Khi sự kiện xảy ra, hàm Callback của Subscriber sẽ được tự động kích hoạt.

---

## 2. Các File `events.py` và `signals.py`

Mỗi Module thường có 2 file liên quan đến Sự Kiện:
- **`signals.py`**: Nơi GIỚI THIỆU (Define) các Sự kiện mà Module này sở hữu để phát ra.
  ```python
  # Trong mindstack_app/modules/fsrs/signals.py
  from blinker import Namespace
  
  _signals = Namespace()
  
  # Bắn ra khi một Card được review xong
  card_reviewed = _signals.signal('card_reviewed')
  ```

- **`events.py`**: Nơi ĐĂNG KÝ (Connect) Lắng nghe các Sự kiện từ các Module khác.
  ```python
  # Trong mindstack_app/modules/gamification/events.py
  from mindstack_app.modules.fsrs.signals import card_reviewed
  from .services.scoring_service import ScoringService

  @card_reviewed.connect
  def on_card_reviewed(sender, **kwargs):
      # Xử lý tặng điểm cho người dùng tại đây
      ScoringService.award_points(kwargs.get('user_id'), kwargs.get('rating'))
  ```

---

## 3. Bản Đồ Sự Kiện Cốt Lõi (Core Event Map)

Dưới đây là một số dòng luân chuyển sự kiện (Signal Flows) cực kỳ tấp nập trong MindStack:

### A. Lifecycle Học Tập (Learning Events)
- Phát ra: `card_reviewed` (FSRS), `typing_answered` (Typing), `quiz_completed` (Quiz).
- Lắng nghe: 
  - `Gamification`: Để kích hoạt bộ đếm Streak, cấp Time Bonus và Nạp điểm vào `score_logs`.
  - `Learning_History`: Để Insert dữ liệu nguyên thủy (Raw Data) vào `study_logs` phục vụ Data Analytics.
  - `Goals`: Để kiểm tra xem mục tiêu "Học 50 từ / ngày" của người dùng đã hoàn thành chưa.

### B. Lifecycle Nội Dung (Content Events)
- Phát ra: `content_created`, `content_updated`, `content_deleted` (Từ Content Management).
- Lắng nghe:
  - `AI_Generator`: Để biết cần phải chạy lại Job sinh Audio hay Dịch câu nếy Content thay đổi.
  - `Search`: Để Cập nhật lại Index (Full-Text Search).

### C. Lifecycle Người Dùng (User Events)
- Phát ra: `user_registered`, `user_logged_in` (Từ Auth).
- Lắng nghe:
  - `Notification`: Gửi Email "Welcome to MindStack" hoặc Cảnh báo Đăng nhập lạ.
  - `Gamification`: Tặng quà tân thủ.

---

## 4. Kiểm Soát Sự Kiện Đáng Cậy (Resiliency)

Hiện tại hệ thống Signal của Flask/Blinker hoạt động trong **Cùng Một Tiến Trình (Synchronous In-Process)**. 
Điều này có nghĩa là khi Hàm A phát sự kiện, nó sẽ đợi Hàm B (Listener) chạy xong rồi mới chạy tiếp. 

**Tuy nhiên, với các tác vụ quá Nặng (Gửi Email, Gọi API Open AI):**
- Hàm Listener (trong `events.py`) sẽ KHÔNG tự làm mà thay vào đó đùn đẩy công việc (Offload) cho hệ thống **Background Tasks (Celery / RQ)**.
- Ví dụ:
  ```python
  @user_registered.connect
  def send_welcome_email(sender, user_id):
      # Không gửi Email làm treo HTTP Request. Ném Task cho Celery chạy ngầm.
      celery_send_email.delay(user_id)
  ```
