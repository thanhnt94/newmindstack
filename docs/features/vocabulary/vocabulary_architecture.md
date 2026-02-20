# Kiến Trúc Điểu Phối Module Từ Vựng (Vocabulary Architecture)

Module **Vocabulary** (`mindstack_app/modules/vocabulary/`) là module lớn nhất và phức tạp nhất của MindStack. Nó không chỉ phục vụ một chế độ học đơn lẻ, mà là một siêu-module (Super-Module) chứa nhiều chế độ học (Game Modes) khác nhau dùng chung một tệp dữ liệu cốt lõi (Flashcard Set).

Tài liệu này giải thích cấu trúc phân nhánh và Trái tim điều phối (Driver) của nó.

---

## 1. Mẫu Thiết Kế Điều Phối (The Driver Pattern)

Tại thư mục gốc của module có một file cực kỳ quan trọng: **`driver.py`**.
Đây là **Strategy Pattern / Abstract Factory**:
- Khi người dùng muốn bắt đầu học, Request chỉ chứa `learning_mode` (ví dụ: `typing`, `mcq`, `matching`).
- Thay vì dùng một hàm `if/else` khổng lồ dài hàng ngàn dòng, hệ thống sử dụng `SessionManagerFactory`.
- Nhà máy (Factory) này sẽ nhìn vào Chuỗi cấu hình và khởi tạo (Instantiate) đúng Class Manage phụ trách logic cho chế độ đó:
  - `"flashcard"` -> `FlashcardSessionManager`
  - `"mcq"` -> `MCQSessionManager`
  - `"typing"` -> `TypingSessionManager`
  - `"listening"` -> `ListeningSessionManager`

Tất cả các Session Managers này đều phải kế thừa từ một **BaseSessionManager** (đặt ở tầng `session`) để đảm bảo chúng có chung bộ khung chuẩn: Khởi tạo -> Lấy Điểm -> Nộp câu trả lời -> Hoàn Thành.

---

## 2. Cấu Trúc Các Game Modes (Thư mục con)

Module `vocabulary` được chia thành các thư mục con, mỗi thư mục chính là một "Game Mode". Những cái đã có docs riêng (Flashcard, MCQ, Typing) nằm ở file khác. Dưới đây là kiến trúc của các chế độ bô sung:

### A. Chế Độ Listening (Nghe / Điền Tự Do)
Nằm tại `vocabulary/listening/`.
- **Logic hoạt động**: Trái ngược với Typing (viết bằng mắt), Listening giấu hoàn toàn Text chữ. Client tải Audio bằng Pre-fetch (xem `audio_tts_management.md`), tự động Autoplay.
- **Xử lý phía Server**: `ListeningSessionManager` cực kỳ giống `TypingSessionManager`, nó sẽ nhận Input Text của người dùng, gọi hàm đo khoảng cách chuỗi (Levenshtein Distance) và rẽ nhánh Rating (1 đến 4). FSRS được nạp cho trạng thái Listening.
- **Tính năng mở rộng**: Listening chịu thiệt thòi lớn từ Homophones (Từ đồng âm khác nghĩa). Engine có thể cần cấu hình bỏ qua sai sót về viết hoa, tổ hợp dấu câu để công bằng.

### B. Chế Độ Matching (Game Nối Thẻ)
Nằm tại `vocabulary/matching/`.
- **Logic hoạt động**: Đây là Game đòi hỏi 100% Client-Side Physics (như Animation bay lượn, Click 2 thẻ nối vào nhau sẽ biến mất nếu trùng khớp ID).
- **Xử lý phía Server**: Backend `MatchingSessionManager` làm việc rất nhàn! Nó không cần đánh giá từng cú Click của User. Đầu phiên, nó xuất ra toàn bộ JSON N-Cặp thẻ bị trộn lẫn. User chơi ở Web Browser.
- **Kết thúc (Submit)**: Khi bảng Web đã Clear, User gửi 1 Request duy nhất lên API chứa Tổng thời gian hoàn thành (Time Spent) và các Cặp Gợi ý đã dùng. 
- **DB Flow**: Tuyệt đối **KHÔNG CẬP NHẬT FSRS**, vì matching không phản ánh trí nhớ từng thẻ độc lập. Chỉ đổ 1 record duy nhất vào `score_logs` nạp điểm thưởng Time-Trial (đua top).

### C. Chế Độ Speed (Lật Thẻ Tốc Độ Bão Ảnh)
Nằm tại `vocabulary/speed/`.
- **Logic hoạt động**: Speed mode là một bài huấn luyện cơ rèn phản xạ (Muscle Memory). Màn hình flashcard bắt buộc lật tự động sau 1-2 giây. User chỉ được ấn nút SpaceBar nếu thẻ hiển thị Trùng khớp với Nghĩa gốc, và ấn Phím Mũi Tên nếu không khớp (True/False Binary).
- **Xử lý phía Server**: Tương tự MCQ nhưng tốc độ cao. Dữ liệu nạp về Backend gồm N thẻ đúng và M thẻ sai.
- **DB Flow**: FSRS có thể cập nhật dưới một chuẩn Hard-Capped Multiplier riêng (vì đây là nhận diện - recognition, không phải Truy xuất - Recall).

---

## 3. Tương Lai Dễ Dàng Thêm Mode Mới (Plug-and-Play)

Nhờ kiến trúc Modular này, nếu tháng sau MindStack muốn làm chế độ "Dịch Câu (Translation)", quy trình sẽ vô cùng mượt mà:
1. Tạo thư mục `vocabulary/translation/`.
2. Tạo File `session_manager.py` chứa class `TranslationSessionManager(BaseSessionManager)`.
3. Nhúng class đó vào Enum của `driver.py`.
4. Không cần sửa bất kỳ dòng code Dataloader hay FSRS core nào. Đã có thể bắt đầu chơi Game mới.
