# Sổ Vàng Đóng Góp Ý Tưởng (Future Refactoring & Ideas Backlog)

Tài liệu này là không gian (Notepad) để lưu trữ những "Vụ Nổ Lớn" (Big Bang Ideas) hoặc các bất cập chưa có thời gian Fix trong MindStack. Bất kỳ lúc nào bạn có cảm hứng, hãy mở file này ra xem có dự án nào có thể code không!

---

## 1. Mảng Học Thuật & Chế Độ Mới (Game Modes)

- [ ] **Wordle Mode**: Cơ chế mini-game giống trò Wordle (đứng top 1 Trending thế giới). Dựa trên cột `front` là chữ một từ, người dùng có 6 lần đoán.
- [ ] **CrossWord Mode (Giải ô chữ)**: Hệ thống Backend chạy script đan xen (Intersect) các chữ cái từ vựng tạo ra 1 bảng Grid ô chữ, Front-End hiển thị ra để người dùng giải.
- [ ] **Listening Dictation Thật**: Hiện tại chế độ Typing là nhìn Flashcard rồi viết lại. Cần một chế độ "Giấu Front" (chỉ phát audio), sau đó tắt loa và yêu cầu người dùng gõ chuỗi. Nâng cao cực mạnh kỹ năng IELTS Listening Part 1.

## 2. Ý Tưởng System Architecture & Refactoring

- [ ] **Sử Dụng Message Broker (RQ/Celery + Redis)**: Hiện tại app vẫn đang dùng Web Thread để kích hoạt tác vụ Background. Tuy dễ cài đặt nhưng khi User tăng mạnh sẽ nghẽn App. Đề nghị chuyển toàn bộ Code Text-To-Speech (sinh MP3) và Gửi Email vô Queue của Celery.
- [ ] **Database Partitioning cho Study Logs**: Bảng `study_logs` lưu trữ mỗi một lần người dùng click chuột/giải xong 1 câu... Với 10K người dùng, mỗi người 200 click/ngày -> Data phình to khủng khiếp. Suy nghĩ tới phương án Parition (Cắt bảng theo tháng `study_logs_2026_01`) hoặc Archive sang dạng Time-Series.
- [ ] **WebSockets (Socket.IO)**: Cập nhật Cúp (Trophy) và Điểm số theo Real-time (Thời gian thực). Hiện tại có thể điểm nhảy lúc sang trang mới, nhưng nếu tích hợp WebSocket, khi User A (bạn thân) vừa được cúp Kim Cương, góc dưới màn hình User B sẽ nổ Toast Notif báo ngay lập tức.
- [ ] **Tách Rời Frontend Cà Khịa (Headless CMS)**: Tương lai muốn viết app iOS/Android native. MindStack cần tạo phiên bản Routing `Flask-Restful` trả về 100% JSON (Khác với `render_template` Jinja HTML hiện tại). Đóng gói API ngon lành.

## 3. Ý Tưởng Gamification & Xã Hội (Social)

- [ ] **Clan / Guild (Hội Nhóm Học Tập)**: Tổ chức người dùng thành các Clan 50 người. Tổng điểm `score_logs` mỗi tuần của các thành viên ghép lại cày Rank xếp hạng (Top 10 Server).
- [ ] **Hệ thống Cửa Hàng (Shop & Virtual Currency)**: Total Score không chỉ để nhìn mốc. Người dùng có thể ĐỔI Điểm lấy "Thẻ Đông Băng (Streak Freeze)", "Skin Giao Diện Mới", "Khung Viền Avatar". Update vào DB cột `gems` (Ruby).
- [ ] **Khóa Học Trẻ Em (Card Mascot)**: AI sinh kèm một nhân vật Hoạt hình nhỏ bên cạnh thẻ (dựa vào Gen-AI DALL-E) vỗ tay khi chọn đúng, khóc khi chọn sai.

## 4. UI/UX Tweaks (Kiểm Chí Chút Ít)
- [ ] Add Loading Skeleton (Giao diện khung xương tải trang) cho các Card UI ở Dashboard, thay vì màn hình trắng nhảy cụp 1 nhát.
- [ ] Thêm nút "Report Lỗi" vào từng Flashcard Box (vì có thể câu dịch bị sai do AI làm). Gắn lệnh Call gửi API sang Module `feedback` hoặc `admin`.

---
*Lưu ý: Tài liệu này được AI và Dev thêm vào dựa trên lộ trình dài hạn của một hệ sinh thái EdTech 1 Triệu User.*
