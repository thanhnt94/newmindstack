# Thuật Toán Sinh Chướng Ngại Vật (Smart MCQ Distractors Logic)

Đằng sau một câu Trắc Nghệm (Multiple Choice Question) 4 lựa chọn không chỉ có A, B, C, D ngẫu nhiên.
Nếu hệ thống tự tung tung lấy bừa Đáp Án Sai (Distractors), người dùng sẽ học "Mẹo" rất nhanh (bằng cách nhìn độ dài ngắn, loại trừ) mà không học kiến thức. Hơn nữa, những từ vựng có nhiều nghĩa đồng nghĩa nếu lọt vào sẽ tạo ra 2 câu trả lời đúng, gây ức chế.

Kiến trúc MindStack giải quyết bài toán này bằng một **Smart Pipeline 4 Bước** ngự trị trong `mcq_engine.py` và `selector.py`.

---

## 1. Nguồn Dữ Liệu & Ưu Tiên Custom Pairs

Khi sinh ra 3 Đáp Án Sai để lừa người dùng, dữ liệu phải "Hợp Logic Ngữ Cảnh". MindStack truy xuất bằng cách **Query Distractors chỉ từ cùng một Container (Flashcard Set / Quiz Set) hiện tại.**
- Hơn nữa, **MCQ phải nhận diện được `custom_pairs`** (Từ config `reading_key = 'front'`, `meaning_key = 'back'`) do user thiết lập để lấy đúng cột ý nghĩa mong muốn.

## 2. Đường Ống Kỹ Thuật (The 4-Step Smart Pipeline)

Quá trình "Đúc Câu Hỏi Trắc Nghiệm thông minh" đi qua 4 màng lọc sau:

### Bước 1: Lấy Mẫu Ngẫu Nhiên Tuyệt Đối (True Random Fetching)
Trước kia, việc lặp qua Database thường lấy N item đầu tiên, khiến đáp án bị trùng lặp ở những thẻ đầu danh sách.
- **Biện pháp**: Tại `MCQEngine`, list `all_items_data` được Copy và chạy hàm `random.shuffle()` trong Ram (Memory Level) trước khi duyệt.
- Trích xuất tối đa **2000 item** có `item_id` khác biệt để quăng vào bồn chứa (Candidate Pool). Việc quét được limit tối đa con số 2000 nhằm kiểm soát RAM rớt nhịp đối với siêu dự án từ điển, tuy nhiên 2000 records này vẫn là "một đại dương data" khổng lồ, giúp thuật toán Điểm Lừa Đảo dư sức tra cứu (điển hình như bài toán gài Từ đồng âm Kanji).

### Bước 2: Sàng Lọc Sát Nghĩa (Absolute Filtering / Sanitization)
Từ Pool 20 từ, chuyển quyền điều phối cho `SmartDistractorSelector`.
1. **Tách Ý (Split Meaning)**: Băm đáp án gốc và cả 20 đáp án nhiễu thành các `Set` nhỏ bằng các dấu ngắt câu như `,`, `;`, `/`, `|`.
   - VD: `"Quả Cam / Màu cam"` -> `{"quả cam", "màu cam"}`.
2. **Luật Vứt Bỏ (Intersection Rule)**: Chỉ cần Tập (Set) ý nghĩa của Tín hiệu Nhiễu có **BẤT KỲ** một phần tử nào giao cắt (`intersection`) với Đáp Án Đúng -> Lập tức vứt bỏ. Điều này triệt tiêu hoàn toàn tỷ lệ sinh 2 câu đúng.
3. Không quên loại bỏ luôn những Tín hiệu Dị thường (Trùng 100% Text).

### Bước 3: Chấm Điểm Lừa Đảo (Trickiness Scoring)
Đây là "hạt nhân" của sự hắc búa. Những thẻ qua được Bước 2 sẽ bị mang diễn điểm (Scoring) xem "Chiếc nào giống với hàng thật nhất".
1. **Length Similarity (Độ dài Ký tự)**: Điểm cộng tối đa 10đ cho candidate có độ dài Ký tự `(len)` bằng với độ dài đáp án đúng.
2. **Word Count Similarity (Độ dài Số từ)**: Điểm cộng tối đa 10đ cho candidate có số Từ (Words) tương đồng. (Tránh tình trạng 1 cái đáp án dài 3 dòng, 3 cái kia ngắn củn 1 chữ -> User nhìn phát ăn ngay).
3. **Keyword Trap (Bẫy từ vựng)**: Nếu candidate và Đáp án gốc có **cùng một từ khóa cốt lõi** (Bỏ qua Stopwords như `the, a, cái, sự`) -> **Được cộng 30 Điểm cực Đậm (Massive Bonus)**.
   - *Tác dụng*: Câu hỏi là "To Eat" (Ăn). Hệ thống bới thấy có chữ "To Drink" ở dưới, nó sẽ vớt chữ này lên để ghép vào lừa vì đều có chữ "To ...".
4. **Japanese Orthography Heuristics (Heuristic Hình thái Tiếng Nhật)**: Chuyên biệt cho bộ môn Tiếng Nhật. Nếu Input phát hiện ra bộ gõ Hán Tự, Hiragana, hoặc Katakana `\u3040-\u30ff`:
   - *Rule 1 (Khớp Khung Xương)*: Nếu Thẻ thật có dạng 2 Kanji (`KK`), Thẻ nhiễu cũng là 2 Kanji (`KK`), Thẻ nhiễu được ban cho **+50 Điểm**.
   - *Rule 2 (Trao đổi Kanji - Ultimate Trap)*: Nếu 2 Thẻ mượn chung 1 ký tự Hán tự (VD: **Học** Hiệu 学校 vs **Học** Sinh 学生 chia sẻ chữ Học). App tặng mức điểm Lừa tối đa: **+100 Điểm Gài bẫy / Mỗi 1 Kanji trùng lặp**. Đây là công thức giúp MindStack không thua kém bất kỳ App Edtech Hàng đầu nào.

### Bước 4: Chốt Sổ & Trộn Đề (Final Selection & Shuffling)
1. Các món hàng đã dán điểm ở Bước 3 được Sort giảm dần (Descending).
2. Tóm lấy 3 anh tài Điểm Cao Nhất (Top N - 1).
3. Gom cùng đáp án Thật sự. 
4. Chạy hàm `random.shuffle(Array List)` của Python để Trộn đáp án lên các vị trí A, B, C, D ngẫu nhiên. Nếu bỏ qua hàm này, đáp án đúng sẽ luôn nằm ở nút A đầu tiên!
5. Trả Payload JSON về Giao diện.

---

### Edge Cases (Ngoại Lệ App)
- **Thiếu thẻ**: Nếu Set Card chỉ có 3 từ. Pipeline lọc quá gắt không tìm được Tín Hiệu Nhiễu? Câu lệnh `min(3, total_vocab_count - 1)` sẽ phát huy tác dụng. Nếu bới không ra 3 đáp án sai, hệ thống tự động giáng cấp xuống câu hỏi chỉ có 2 Option (Đúng và 1 Sai). Rất linh động mà không báo lỗi sập Backend.
