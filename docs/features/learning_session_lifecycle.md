# Vòng Đời Một Phiên Học (Learning Session Lifecycle)

Một **Session (Phiên Học)** là một mạch chảy khép kín mà người dùng trải qua mỗi lần "Ngồi vào bàn học". Việc cấu trúc Session có State (Trạng thái) rất quan trọng để lưu giữ tiến độ học dở dang giúp người dùng đang học bằng Web có thể tắt máy và lát mở Điện thoại lên vẫn thấy học tiếp 15/20 câu cũ.

Module trung tâm: `session`.

---

## 1. Khởi Tạo Phiên (Session Initialization)

Khi người dùng bấm "Study" một bộ thẻ Flashcard Set. Request bay vào Controller.
1. Khởi tạo một đối tượng (Object) trong bộ nhớ: `FlashcardSessionManager(user_id, set_id)` hoặc `MCQSessionManager`.
2. Truy xuất Cấu Hình (Configuration): Lấy ra người dùng đang thiết lập học 20 hay 50 thẻ mỗi phiên, có trộn ngẫu nhiên (Shuffle) không? Có theo FSRS (Chỉ hiện thẻ Đến Hạn) hay không?
3. Bốc Nhặt (Item Selecting / Dispatching):
   - Móc nối Module FSRS, lấy danh sách `item_ids` đủ tiêu chuẩn.
   - Truy vấn Table `learning_items` từ Database lấy Full JSON Content (Mặt trước/sau thẻ).
4. Khởi tạo Row CSDL: `INSERT INTO learning_sessions`:
   - Ghi nhận `session_id`, `learning_mode=flashcard`.
   - Ghi Mảng rỗng vào `processed_item_ids = []` (Chưa học câu nào).
   - Gán `status="active"`, `start_time=now()`.

## 2. Thực Thi & Tương Tác Giữa Chừng (In-Flight Processing)

Hệ thống lúc này trả về View HTML `session.html` cho Front-End với Data truyền ngầm (VD: JSON List 20 từ).
Người dùng thao tác lật thẻ và chấm điểm từng dòng qua Ajax API.
Cho mỗi một thẻ học qua (Loop):
1. **Lưu Nháp Tức Thời (Checkpointing)**: Tại Front-End hoặc API (Tuỳ thiết kế). Mỗi lần qua 1 Thẻ, `processed_item_ids` trong Database liên tục được Append (bồi đắp) ID mới nhất. (VD: `[101, 105, 120]`).
2. Nếu người dùng tắt Browser đột ngột. Một giờ sau quay lại truy cập URL Session. Hệ thống check xem `session.status == 'active'`, lấy `processed_item_ids`. Gạch bỏ 101, 105, 120 đi và chỉ phục vụ danh sách thẻ từ câu Số 4 trên UI. Nối liền mạch.

## 3. Hoàn Thành Lượt Cuối (Session Completion Threshold)

Khi số lượng List Câu hỏi rỗng (Hoặc `length(processed) == length(total)`), sự kiện **Kết Phiên** kích hoạt.
1. Đóng băng Database: `UPDATE learning_sessions SET status='completed', end_time=now()`.
2. Trả về Response cuối cùng cho Script Flashcard `{"is_finished": True, "redirect_url": "/dashboard/stats"}`.
3. Kích Thích Tâm Lý (The Final Reward): Module Session bắn sự kiện `session_completed.send(...)`. Gamification nhận tín hiệu, nếu Session này người dùng học 50/50 câu đúng, thưởng danh hiệu "Tuyệt Đối" kèm Combo Bonus.

## 4. Hậu Xử Lý Dữ Liệu Rác (Garbage Collection & Orphan Sessions)

Một vấn đề kỹ thuật phổ biến là "Orphan Sessions" - Các Session bị bỏ hoang.
- Trường hợp 1: Người học lập Session nhưng sau đó đi ăn Cơm, không bao giờ đánh giá hết 20 thẻ để chuyển trạng thái `status='completed'`.
- Trường hợp 2: Ngày hôm sau họ tạo lại Session Học mới tinh, bỏ Session cũ vĩnh viễn ở trạng thái `'active'`.
- *Cách giải quyết của MindStack*: Sử dụng Module `ops` (Background Tasks) có cài siêu xe CronJob dọn dẹp mỗi nửa đêm lúc 02:00 sáng. Query `SELECT * FROM learning_sessions WHERE status='active' AND last_activity < NOW() - 5 hours`.
- Các session này bị tự động hủy khóa (`status='expired'`) để Database không bị phình to. Giải phóng Memory.
