# Tài liệu Logic Chế độ Vocab MCQ (Multiple Choice Question)

Tài liệu này giải thích chi tiết về logic hoạt động, quy trình tạo câu hỏi và thuật toán lựa chọn đáp án gây nhiễu trong chế độ học trắc nghiệm (MCQ).

## 1. Tổng quan về Engine
Chế độ MCQ sử dụng `MCQEngine` để tạo câu hỏi. Đây là lớp xử lý logic thuần túy (pure logic), không truy vấn trực tiếp cơ sở dữ liệu.

## 2. Quy trình Lựa chọn Đáp án Gây nhiễu (SmartDistractorSelector)

Hệ thống sử dụng một quy trình 4 bước để đảm bảo tính an toàn, hiệu quả và tạo ra các câu hỏi có độ khó cao:

### Bước 1: Lọc thô An toàn (Pre-filtering)
Để tránh các trường hợp đáp án sai nhưng lại giống hệt đáp án đúng (do đồng âm hoặc đồng nghĩa tuyệt đối), hệ thống thực hiện loại bỏ các mục từ trong `candidate_pool` nếu:
- Mặt **Front** (Từ vựng) giống hệt nhau.
- Mặt **Back** (Nghĩa) giống hệt nhau.
- Chuỗi văn bản hiển thị (**Text**) của lựa chọn giống hệt nhau.
*(Lưu ý: Tất cả so sánh đều được thực hiện sau khi `.strip().lower()`)*

### Bước 2: Cơ chế Chốt chặn (Fallback Mechanism)
Để đảm bảo câu hỏi MCQ luôn có đủ số lượng đáp án (thường là 4 lựa chọn), nếu sau Bước 1 số lượng ứng viên còn lại không đủ, hệ thống sẽ tự động nới lỏng điều kiện lọc:
- Lấy lại danh sách ban đầu.
- Chỉ lọc duy nhất một điều kiện: Văn bản hiển thị của lựa chọn phải khác với văn bản hiển thị của đáp án đúng.

### Bước 3: Chấm điểm Bẫy Hình thái (Trickiness Scoring)
Hệ thống chấm điểm cho từng ứng viên để chọn ra những "cái bẫy" chất lượng nhất dựa trên các tiêu chí:
- **Dùng chung Kanji (Shared Kanji):** Trọng số cao nhất (+50 điểm). Nếu từ vựng có chứa các ký tự Kanji giống với đáp án đúng (ví dụ: "学校" và "学生").
- **Độ tương đồng chiều dài (Length Similarity):** Thưởng điểm nếu số lượng ký tự của đáp án sai bằng hoặc xấp xỉ đáp án đúng (+10 điểm cho bằng tuyệt đối, +5 điểm cho sai lệch ít).
- **Mẫu tự tiếng Nhật (Japanese Pattern):** Thưởng điểm nếu cấu trúc Kanji/Hiragana/Katakana giống nhau hoàn toàn (+20 điểm).

### Bước 4: Lựa chọn Cuối cùng (Final Selection)
- Hệ thống xáo trộn ngẫu nhiên danh sách đã chấm điểm (để các đáp án bằng điểm không bị cố định vị trí).
- Sắp xếp giảm dần theo điểm số.
- Cắt lấy đúng số lượng đáp án nhiễu cần thiết.

## 3. Logic Kiểm tra Đáp án
- **Đúng**: Trả về `quality: 5` và cộng điểm thưởng theo cấu hình.
- **Sai**: Trả về `quality: 0` và không cộng điểm.
- Hệ thống ghi lại lịch sử câu trả lời để phục vụ thuật toán SRS (Spaced Repetition System).
