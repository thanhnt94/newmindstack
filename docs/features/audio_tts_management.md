# Quản Lý File Âm Thanh & Text-to-Speech (Audio TTS Management)

Trong hệ sinh thái học ngoại ngữ của MindStack, âm thanh (Audio Phát m Bảnh Xứ) đóng vai trò sống còn. Việc quản lý âm thanh phải giải quyết bài toán lớn: Làm thế nào để Sinh, Lưu trữ, và Tải xuống Âm thanh sao cho mượt mà, không giật lag (No Buffering), không lỗi (No 404).

Module chịu trách nhiệm chính: `audio`.

---

## 1. Cơ Chế Sinh Tiếng Nói (AI Text-to-Speech)

Hệ thống cung cấp file Audio cho mỗi Flashcard hoặc Câu MCQ thông qua một quá trình tĩnh (Static Caching):
- **Phát Sinh Lần Đầu**: Khi quản trị viên / giảng viên tạo Flashcard "Apple" bằng Module Content Management. Hệ thống Gửi "Apple" tới AI Interface (VD: OpenAI TTS, Google Cloud TTS) để Sinh ra file MP3.
- **Quy Ước Đặt Tên Bất Biến**: File Audio sinh ra luôn được băm (Hash) tên theo từ vựng hoặc mang ID quy chuẩn để tránh trùng lặp.
- **Tiết Kiệm Chi Phí**: MindStack **KHÔNG BAO GIỜ** thiết kế tính năng dịch chữ thành tiếng (TTS) On-The-Fly (Realtime) mỗi khi User bấm nút Nghe. Điều này sẽ tốn vô vàn Server Cost và chênh lệch Delay lớn. Một từ vựng nếu có MP3 trên Server thì hàng Triệu User xài chung 1 File đó mãi mãi.

## 2. Đường Dẫn Tuyệt Đối (Audio Proxy Serving)

Vì Frontend có thể xuất hiện từ nhiều Router (/flashcard, /dashboard, /mcq), việc truy vấn file MP3 sẽ theo đường dẫn quy chuẩn API chung để tránh xung đột thư mục nhạy cảm:
- Thay vì `src="/static/media/audio/apple.mp3"`.
- MindStack chạy qua File Server `src="/api/audio/<item_id>.mp3"`.
- Module Audio sẽ `send_file()` an toàn từ Storage (thư mục gốc Local hoặc Cloud AWS S3) để phân phối trực tiếp bằng Nginx / Reverse Proxy mà không làm nặng gánh CPU Flask Cốt Lõi.

---

## 3. Hệ Thống "Tải Trước" Âm Thanh (Audio Pre-Fetching Queue)

**Bài toán rắc rối của Javascript**: Nếu để tới lúc người dùng Bấm Thẻ Flashcard hiện mặt Lưng rồi mới chạy Ajax download `.mp3`, thì sẽ có một độ trễ 1-2 Tích Tắc. User sẽ cảm giác độ ỳ (Lag) trầm trọng, làm hửng hụt trải nghiệm.
- Hơn nữa, trên Mobile iOS / Safari, trình duyệt Cấm Autoplay quá khắt khe, nếu không phát âm thanh NGAY trong cùng 1 Call-Stack Click chuột, âm thanh sẽ bị Block.

**Giải Pháp `audio_manager.js` Queue:**
1. Khi Frontend vừa vào màn hình Session 20 Thẻ Từ. Trình duyệt chưa lật thẻ nào!
2. JS ngầm chạy Background một luồng (Worker) dùng `fetch()` tải ngay 3 file MP3 của Câu #1, Câu #2, Câu #3 về nhét vào mảng Blob Buffer Memory (`window.AudioQueue`).
3. Khi người dùng đánh giá Câu #1 -> Chuyển sang Câu #2 mới. Câu #2 đã nằm sẵn trong RAM Trình duyệt. Javascript lấy Node `<audio src=Blob...>` và gõ `.play()` ngay Lập Tức, delay chưa tới 50ms. Rất mượt.
4. Ngay lúc đó, JS phát tín hiệu Load tiếp Audio Của Câu #4 #5 bỏ bổ sung vào đằng đuôi (Telling Tail) của Queue.

---

## 4. Cơ Chế Báo Cáo Xử Lý Lỗi (Auto Regeneration)

Sẽ có tỉ lệ File Storage bị xóa nhầm, ổ đĩa hỏng, hoặc ban đầu AI tạo TTS bị lỗi.
Khi JS ở Frontend tải xuống Audio bị Lỗi `HTTP 404 / 500`:
- JS sẽ kích hoạt quá trình `handleAudioError()`. Nó gửi 1 lệnh **Post Request ngầm** lên API `POST /api/audio/regenerate/<item_id>`.
- Module Backend nhận Lệnh, kích hoạt AI Service sinh lại File ngay lập tức `(Re-generation)` và lưu vào ổ cứng.
- JS Frontend chờ 1-2 giây rồi thử Tải Lại. Khi thành công, File sẽ phát cho User. User không hề biết Server vừa mất file và mới được phục hồi khẩn cấp. Mọi thứ trong suốt.
