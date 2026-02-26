# Tài liệu Logic Chế độ Vocab MCQ (Multiple Choice Question)

Tài liệu này giải thích chi tiết về logic hoạt động, quy trình tạo câu hỏi và thuật toán lựa chọn đáp án gây nhiễu (distractor) trong chế độ học trắc nghiệm (MCQ) của MindStack.

## 1. Tổng quan về Engine
Chế độ MCQ sử dụng `MCQEngine` để tạo câu hỏi. Đây là lớp xử lý logic thuần túy (pure logic), không truy vấn trực tiếp cơ sở dữ liệu.

## 2. Quy trình Lựa chọn Đáp án Gây nhiễu (SmartDistractorSelector)

Hệ thống áp dụng quy trình 4 bước tối ưu hóa bẫy hình thái (morphological traps), giúp người học phân biệt các từ có vẻ ngoài giống nhau nhưng nghĩa khác nhau:

### Bước 1: Phân tích và Lọc Hình thái (Morphological Filtering)
Hệ thống phân loại từ vựng theo cấu trúc chữ Nhật Bản để nhận diện "hình thái":
- **K**: Kanji, **H**: Hiragana, **C**: Katakana.
- Ví dụ: `招待` (Mẫu: **KK** - 2 Kanji), `招く` (Mẫu: **KH** - Kanji + Hiragana).

**Nguyên tắc Ưu tiên tuyệt đối:** 
- Nếu tìm đủ số lượng đáp án nhiễu có **cùng cấu trúc hình thái** với đáp án đúng, hệ thống sẽ **CHỈ sử dụng** các từ này. 
- Điều này giúp loại bỏ các từ "trông quá khác biệt" (như ví dụ `招待` và `招く` sẽ không xuất hiện cùng nhau nếu có đủ các từ 2 Kanji khác).

### Bước 2: Lọc thô An toàn (Hard Filter)
Để đảm bảo tính logic, hệ thống loại bỏ các mục từ nếu:
- Mặt **Front** (Từ vựng) giống hệt nhau.
- Mặt **Back** (Nghĩa) giống hệt nhau.
- Chuỗi văn bản hiển thị (**Text**) của lựa chọn giống hệt nhau.

### Bước 3: Chấm điểm Bẫy Hình thái (Trickiness Scoring)
Hệ thống chấm điểm để chọn ra những "cái bẫy" chất lượng nhất. Các tiêu chí cộng điểm:
- **Cùng Pattern Hình thái (+100 điểm):** Đảm bảo các từ có cùng cấu trúc (như cùng là 2 Kanji) luôn đứng đầu danh sách lựa chọn.
- **Dùng chung Kanji (Shared Kanji Bonus - Trọng số rất cao: +50 điểm/chữ):** Ưu tiên cực cao cho các từ dùng chung ký tự Kanji với đáp án đúng (ví dụ: `招待` và `招集` chung chữ `招`).
- **Độ tương đồng chiều dài (+20 điểm):** Thưởng điểm nếu số lượng ký tự của đáp án sai bằng đáp án đúng.

### Bước 4: Lựa chọn Cuối cùng (Final Selection)
- Hệ thống xáo trộn ngẫu nhiên danh sách đã chấm điểm (để các đáp án bằng điểm không bị cố định vị trí).
- Sắp xếp giảm dần theo điểm số và cắt lấy đúng số lượng đáp án nhiễu cần thiết (thường là 3 từ để tạo thành 4 lựa chọn).

## 3. Logic Kiểm tra Đáp án
- **Đúng**: Trả về `quality: 5` và cộng điểm thưởng theo cấu hình `VOCAB_MCQ_CORRECT_BONUS`.
- **Sai**: Trả về `quality: 0` và không cộng điểm.
- Hệ thống ghi lại lịch sử câu trả lời để phục vụ thuật toán SRS (Spaced Repetition System).
