# Tài liệu Logic Chế độ Vocab MCQ (Multiple Choice Question)

Tài liệu này giải thích chi tiết về logic hoạt động, quy trình tạo câu hỏi và thuật toán lựa chọn đáp án gây nhiễu trong chế độ học trắc nghiệm (MCQ) của hệ thống MindStack.

## 1. Tổng quan về Engine
Chế độ MCQ được vận hành bởi `MCQEngine`, một bộ máy xử lý logic thuần túy (pure logic). Engine này chịu trách nhiệm chuyển đổi dữ liệu thô từ cơ sở dữ liệu thành một gói câu hỏi hoàn chỉnh bao gồm: câu hỏi, các lựa chọn, đáp án đúng và các tài nguyên đi kèm (âm thanh, hình ảnh).

## 2. Quy trình Tạo Câu hỏi

Quy trình tạo một câu hỏi MCQ trải qua 7 bước chính:

### Bước 1: Xác định Chế độ (Mode)
Hệ thống hỗ trợ các chế độ hiển thị linh hoạt:
- **front_back**: Câu hỏi là mặt trước (thường là từ vựng), đáp án là mặt sau (nghĩa).
- **back_front**: Câu hỏi là mặt sau (nghĩa), đáp án là mặt trước (từ vựng).
- **mixed**: Trộn ngẫu nhiên giữa hai chế độ trên cho từng câu hỏi.
- **custom_pairs**: Sử dụng các cặp khóa tùy chỉnh được cấu hình riêng cho bộ thẻ.

### Bước 2: Trích xuất Nội dung
Dựa trên chế độ đã chọn, Engine sẽ lấy chuỗi văn bản cho câu hỏi và đáp án đúng từ dữ liệu của mục từ (item).

### Bước 3: Thu thập Danh sách Đáp án Gây nhiễu (Distractor Pool)
Hệ thống sẽ quét toàn bộ các mục từ khác trong cùng một bộ thẻ (set) để tìm các đáp án sai tiềm năng. 
- Giới hạn tối đa 2000 mục để đảm bảo hiệu năng.
- Loại bỏ ngay lập tức các mục có ID trùng với câu hỏi hiện tại hoặc có nội dung đáp án giống hệt đáp án đúng.

### Bước 4: Lọc Đối Xứng Tuyệt Đối (Absolute Symmetric Filtering)
Để giải quyết triệt để vấn đề từ đồng nghĩa (synonyms) xuất hiện trong đáp án gây nhiễu (đặc biệt ở chế độ Hỏi Nghĩa -> Chọn Từ), hệ thống áp dụng cơ chế lọc đối xứng:
- **Kiểm tra chéo hai mặt**: Bất kể đang học ở chế độ nào, hệ thống luôn so sánh cả mặt Từ vựng (Front) và mặt Nghĩa (Back) của đáp án nhiễu với đáp án đúng.
- **Loại bỏ đồng nghĩa**: Sử dụng hàm `_extract_intents` để tách các lớp nghĩa (phân cách bởi `;`, `/`, `|`, `,`). Nếu có **bất kỳ sự giao thoa nào** giữa tập hợp các nghĩa của đáp án đúng và đáp án nhiễu, đáp án nhiễu đó sẽ bị loại bỏ ngay lập tức.
- **Loại bỏ trùng từ**: Nếu mặt Từ vựng giống hệt nhau cũng sẽ bị loại.

### Bước 5: Chấm điểm "Bẫy hình thái" (Morphological Trickiness Scoring)
Sau khi đã loại bỏ các từ đồng nghĩa ở Bước 4, hệ thống tập trung tạo độ khó bằng các bẫy về thị giác và cấu trúc chữ (morphology) thay vì bẫy ý nghĩa:
- **Bẫy dùng chung Kanji (Shared Kanji Bonus - Trọng số cao nhất: +15 điểm/chữ)**: Ưu tiên cực cao cho các từ dùng chung ký tự Kanji với đáp án đúng (ví dụ: "学校" và "学生"). Điều này tạo ra những cái bẫy thị giác cực kỳ hiệu quả cho người học tiếng Nhật.
- **Bẫy độ dài (Length Similarity Bonus: +5 điểm)**: Cộng điểm nếu đáp án nhiễu có độ dài chuỗi ký tự bằng chính xác với đáp án đúng.
- **Bẫy âm tiết/Kana (Phonetic/Kana Similarity: +3 điểm/chữ)**: Thưởng điểm cho các từ dùng chung các ký tự Hiragana hoặc Katakana (đặc biệt là các hậu tố hoặc tiền tố giống nhau).

### Bước 6: Lựa chọn và Trộn (Final Selection)
Hệ thống chọn ra N đáp án có số điểm cao nhất (thường là 3 đáp án sai để tạo thành 4 lựa chọn), sau đó trộn ngẫu nhiên thứ tự của chúng với đáp án đúng.

### Bước 7: Xử lý Định dạng và Media
- **BBCode to HTML**: Chuyển đổi các định dạng đặc biệt (như ảnh, in đậm, màu sắc) trong văn bản sang HTML.
- **Audio Mapping**: Gán các URL âm thanh tương ứng cho câu hỏi và đáp án để hỗ trợ việc phát âm tự động.

## 3. Logic Kiểm tra Đáp án
Khi người dùng chọn một đáp án, hệ thống sẽ so sánh chỉ số (index) được chọn với `correct_index`.
- Nếu đúng: Cộng điểm thưởng (dựa trên cấu hình `VOCAB_MCQ_CORRECT_BONUS`) và trả về chất lượng (quality) là 5.
- Nếu sai: Không cộng điểm và trả về chất lượng là 0.

## 4. Tóm tắt các thuật toán chính
- **SmartDistractorSelector**: Lớp xử lý chính việc lọc và chấm điểm đáp án gây nhiễu.
- **JP Pattern Recognition**: Nhận diện cấu trúc ký tự tiếng Nhật (K-Kanji, H-Hiragana, C-Katakana).
- **Intent Splitting**: Tách nhỏ các tầng ý nghĩa để kiểm tra tính duy nhất của đáp án.
