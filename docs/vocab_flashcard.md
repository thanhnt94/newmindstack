# Vocabulary Flashcard Module Documentation

## 1. Tổng quan (Overview)
Module `vocab_flashcard` (Flashcard từ vựng) là thành phần cốt lõi của MindStack, cung cấp trải nghiệm học tập lặp lại ngắt quãng (Spaced Repetition) cho người dùng. Module này đã được refactor theo kiến trúc **Modular Monolith** (Hexagonal Style), tách biệt rõ ràng giữa Business Logic (Engine), Data Access (Services), và Presentation (Routes).

## 2. Kiến trúc Module (Module Architecture)
Module tuân thủ cấu trúc thư mục sau:
- `engine/`: Chứa core logic, thuật toán FSRS, cấu hình và định nghĩa các mode.
- `services/`: Chứa các service hỗ trợ như `FlashcardQueryBuilder`, `FlashcardService`, `CardPresenter`.
- `routes/`: Chứa API và View routes.
- `interface.py`: Cung cấp điểm truy cập công khai duy nhất cho các module khác.

### Các thành phần quan trọng:
- **FlashcardEngine**: Singleton quản lý logic trung tâm (lấy thẻ, xử lý câu trả lời, tính điểm).
- **FlashcardQueryBuilder**: Helper xây dựng các truy vấn SQLAlchemy phức tạp để lọc thẻ.
- **FSRSInterface**: Cổng giao tiếp với module `fsrs` để quản lý trạng thái trí nhớ của thẻ.

## 3. Chế độ Học tập Duy nhất (Single SRS Mode)
MindStack Flashcard đã được tối ưu hóa để chỉ sử dụng **duy nhất một chế độ học tập thông minh (SRS)**. Hệ thống tự động quản lý thứ tự ưu tiên trong cùng một phiên học mà không cần người dùng phải chọn lựa:

| Mode | ID | Mô tả | Logic Lọc & Sắp xếp |
| :--- | :--- | :--- | :--- |
| **SRS (Học tập)** | `srs` | Chế độ duy nhất, tự động ưu tiên thẻ cần ôn. | 1. **Thẻ đến hạn**: Ngẫu nhiên.<br>2. **Thẻ mới**: Tuần tự. |

## 4. Cơ chế Lựa chọn Thẻ (Card Selection Mechanism)
Việc chọn thẻ tuân theo một quy trình thống nhất trong cùng một luồng (flow):
1. **Lọc thẻ khả dụng**: Hệ thống chỉ lấy những thẻ có trạng thái `NEW` hoặc đã đến hạn ôn tập (Retrievability < threshold).
2. **Ưu tiên thẻ đến hạn (Due)**: Xuất hiện trước và được xáo trộn ngẫu nhiên để tăng hiệu quả ghi nhớ.
3. **Thẻ mới (New)**: Tự động xuất hiện sau khi hết thẻ đến hạn, được sắp xếp theo thứ tự trong bộ thẻ.
4. **Resuming**: Nếu phiên học bị gián đoạn, thẻ đang học dở sẽ được ưu tiên hiển thị lại.

## 5. Logic FSRS & Scoring
- **Rating 4 nút**: Hệ thống bắt buộc sử dụng 4 nút đánh giá (`Again`, `Hard`, `Good`, `Easy`) để tối ưu hóa thuật toán FSRS.
- **Tiến trình**:
    - Mỗi câu trả lời sẽ cập nhật trực tiếp `stability` và `difficulty` của thẻ qua FSRS.
    - Điểm số được thưởng dựa trên chất lượng câu trả lời và streak.




## 6. Tính năng Media & UI
- **Âm thanh (Audio)**: Tự động phát âm thanh (autoplay), hỗ trợ prefetch thẻ tiếp theo để giảm độ trễ. Người dùng có thể yêu cầu tạo lại audio từ text.
- **Hình ảnh (Image)**: Hỗ trợ đính kèm hình ảnh cho cả mặt trước và mặt sau. Có tính năng tìm kiếm và gán ảnh từ AI.
- **Giao diện**:
    - Sử dụng `aura_mobile` cho trải nghiệm di động.
    - SSR (Server-Side Rendering) cho thẻ đầu tiên để tăng tốc độ tải trang.
    - SPA (Single Page Application) cho các thẻ tiếp theo thông qua API `/get_flashcard_batch`.

## 7. Quy trình Session (Session Lifecycle)
1. **Khởi tạo**: Route `/start/...` tạo bản ghi session trong DB và cookie.
2. **Vòng lặp**: Client fetch thẻ -> Người dùng trả lời -> Gửi kết quả (`submit_answer`) -> API trả về stats & srs data -> Fetch thẻ tiếp theo.
3. **Kết thúc**: Khi hết thẻ hoặc người dùng chọn kết thúc, session status chuyển sang `completed`.
