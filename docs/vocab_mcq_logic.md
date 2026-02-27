# Tài liệu Logic Chế độ Vocab MCQ (Multiple Choice Question)

Tài liệu này giải thích chi tiết về logic hoạt động, quy trình tạo câu hỏi và thuật toán lựa chọn đáp án gây nhiễu (distractor) trong chế độ học trắc nghiệm (MCQ) của MindStack.

## 1. Tổng quan về Engine
Chế độ MCQ sử dụng `MCQEngine` để tạo câu hỏi. Đây là lớp xử lý logic thuần túy (pure logic), không truy vấn trực tiếp cơ sở dữ liệu.

## 2. Quy trình Lựa chọn Đáp án Gây nhiễu (SmartDistractorSelector)

Hệ thống áp dụng quy trình 4 bước tối ưu hóa bẫy hình thái (morphological traps), giúp người học phân biệt các từ có vẻ ngoài giống nhau nhưng nghĩa khác nhau:

### Bước 1: Phân tích và Lọc Hình thái (Morphological Filtering)
Hệ thống phân tích **nội dung hiển thị của các lựa chọn (Choices)** để nhận diện "hình thái" đồng nhất:
- **K**: Kanji, **H**: Hiragana, **C**: Katakana.
- **W**: Word Count (Dành cho tiếng Việt/Anh - đếm số lượng từ).
- Ví dụ: `招待` (**KK**), `招く` (**KH**), `Đồng nghiệp` (**W2**).

**Nguyên tắc Ưu tiên tuyệt đối:** 
- Nếu tìm đủ số lượng đáp án nhiễu có **cùng cấu trúc hình thái** với đáp án đúng, hệ thống sẽ **CHỈ sử dụng** các từ này. 
- Điều này giúp loại bỏ các từ "trông quá khác biệt" (như ví dụ `招待` và `招く` sẽ không xuất hiện cùng nhau nếu có đủ các từ 2 Kanji khác).

### Bước 2: Lọc thô An toàn (Hard Filter)
Để đảm bảo tính logic, hệ thống loại bỏ các mục từ nếu:
- Mặt **Front** (Từ vựng) giống hệt nhau.
- Mặt **Back** (Nghĩa) giống hệt nhau.
- Chuỗi văn bản hiển thị (**Text**) của lựa chọn giống hệt nhau.
- **Mới**: Chuỗi văn bản hiển thị (**Text**) của lựa chọn giống hệt văn bản của **Câu hỏi**.

### Bước 3: Chấm điểm Bẫy Hình thái (Trickiness Scoring)
Hệ thống chấm điểm để chọn ra những "cái bẫy" chất lượng nhất. Các tiêu chí cộng điểm:
- **Cùng Pattern Hình thái (+100 điểm):** Đảm bảo các từ có cùng cấu trúc (như cùng 2 Kanji hoặc cùng số lượng từ tiếng Việt) luôn đứng đầu.
- **Dùng chung nội dung (Shared Tokens - +150 điểm/đơn vị):** 
    - Với tiếng Nhật: Thưởng theo số chữ Kanji trùng.
    - Với tiếng Việt/Anh: Thưởng theo số lượng **từ vựng** trùng nhau (ví dụ: "Đồng nghiệp" và "Đồng môn" chung từ "Đồng").
- **Tương đồng loại từ (+30 điểm):** Ưu tiên các từ có cùng từ loại (Danh từ, Động từ, v.v.) để tạo bẫy logic hơn.
- **Độ tương đồng chiều dài (+20 điểm):** Thưởng điểm nếu số lượng ký tự của đáp án sai bằng đáp án đúng.

### Bước 4: Lựa chọn Cuối cùng (Final Selection)
Hệ thống hỗ trợ số lượng đáp án linh hoạt để tạo sự đa dạng:
- **Cấu hình cố định**: Theo giá trị `num_choices` (ví dụ: 4 hoặc 6 đáp án).
- **Ngẫu nhiên (Random Dynamic)**: Nếu không có cấu hình cụ thể, hệ thống tự động chọn số lượng từ 3 đến 6 với trọng số ưu tiên 4 đáp án (60%) để tránh nhàm chán.
- Sau khi xác định số lượng, hệ thống xáo trộn ngẫu nhiên danh sách đã chấm điểm, sắp xếp giảm dần theo điểm số và cắt lấy đúng số lượng cần thiết.

## 3. Logic Kiểm tra Đáp án và Hệ thống Điểm số

Hệ thống tuân thủ nguyên tắc tách biệt trách nhiệm (Separation of Concerns) và triết lý thiết kế "Luyện tập không làm nhiễu dữ liệu học tập":

### Nguyên tắc "No SRS Integration"
- **Tách biệt hoàn toàn với FSRS**: Khác với chế độ Flashcard truyền thống, kết quả Đúng/Sai trong chế độ MCQ **KHÔNG** được gửi đến module FSRS. 
- **Không thay đổi trạng thái trí nhớ**: Các thông số như Độ ổn định (Stability), Độ khó (Difficulty) hay Lịch ôn tập (Retrievability) của thẻ sẽ không bị tác động bởi việc trả lời MCQ. Điều này đảm bảo tính chính xác của thuật toán lặp lại ngắt quãng, tránh các sai số do người dùng "đoán mò" đáp án trong trắc nghiệm.
- **Chế độ Luyện tập (Practice Mode)**: MCQ được định nghĩa là một hoạt động bổ trợ mang tính chất Gamification để tăng cường phản xạ và ghi nhớ hình thái từ vựng.

### Quy trình Xử lý Kết quả
1. **Kiểm tra Logic**: `MCQEngine` thực hiện so sánh `correct_index` và `user_answer_index` để xác định trạng thái `is_correct`.
2. **Uỷ quyền Tính điểm (Scoring Delegation)**: Nếu kết quả là Đúng, `MCQSessionManager` sẽ uỷ quyền cho module `scoring` thông qua `ScoringInterface` để thực hiện:
   - Cộng điểm thưởng cho người dùng (theo cấu hình `VOCAB_MCQ_CORRECT_BONUS`).
   - Cập nhật tổng điểm (Total Score) và gửi tín hiệu (signal) về hệ thống Gamification.
3. **Ghi chép Lịch sử (Activity Log)**: Hệ thống ghi lại lịch sử phiên học để người dùng theo dõi tiến độ luyện tập cá nhân, nhưng bản ghi này hoàn toàn độc lập với lịch sử ôn tập chuyên sâu của FSRS.
