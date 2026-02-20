# Tác Vụ Chạy Nền & Vận Hành (Background Tasks & Ops)

Song song với các Request HTTP thời gian thực trả về cho UI, hệ thống MindStack cần thực hiện hàng loạt các tác vụ mất thời gian (Long-running process) hoặc theo Lịch Trình (Cronjob/Scheduled).

Để đảm bảo hiệu suất, các tác vụ này được đưa ra khỏi Thread chính (Web Server gunicorn/waitress), giao lại cho hệ thống **Background Tasks**.

Mô hình này nằm ở sự kết hợp giữa module `ops` và thư viện xử lý tác vụ bất đồng bộ (như Celery, RQ, hoặc ThreadPool).

---

## 1. Phân Loại Background Tasks

### A. Tác Vụ Bất Đồng Bộ Dựa Theo Biến Cố (Asynchronous Event-Driven)
Xảy ra do người dùng kích hoạt, nhưng quá nặng để đợi.
- **Sinh Âm Thanh Hàng Loạt (Batch TTS)**: Khi người dùng Upload 100 từ vựng. Hệ thống không thể đợi AI gọi API 100 lần mới trả HTTP 200 JSon. Nó trả `202 Accepted` và ném Job sinh Audio vào Queues.
- **Sinh Câu Hỏi Tự Động bằng ChatGPT**: Quá trình sinh 10 câu hỏi Trắc nghiệm tốn từ 15-30 giây. Được ném vào Queue chạy ngầm. Giao diện Web sẽ dùng WebSocket hoặc Long-Polling để hỏi xem "Server làm xong chưa?".
- **Gửi Email (Password Reset, Notifs)**: Giao thức SMTP chậm chạp được xử lý ngầm.

### B. Tác Vụ Theo Lịch Trình Định Kỳ (Scheduled / Cron Jobs)
Hệ thống tự động kích hoạt vào một khung giờ nhất định (VD: 0:00 Nửa Đêm).
- **Tính toán Leaderboard**: Chạy Script tổng hợp điểm của toàn bộ User trong ngày để sắp xếp Bảng Xếp Hạng. 
- **Database Backup**: Dump CSDL ra file `.sql`, nén lại và Upload lên Cloud (S3/Drive) bảo vệ dữ liệu tự động.
- **Xóa Cache (Cache Invalidation)**: Dọn dẹp thư mục `__pycache__`, file Audio dư thừa, và làm rỗng bảng Session cũ.
- **Tính toán Streak (Reset)**: Xóa Combo Hiện tại của những ai hôm nay không chịu vào học bài.

---

## 2. Kiến Trúc Hàng Đợi (Message Queue Architecture)

*Lưu ý: Tuỳ thụt vào quy mô (Scale) của Máy Chủ, MindStack triển khai một trong hai tầng kiến trúc sau:*

1. **Lightweight (Dev / Single Server)**: Dùng `threading` hoặc `concurrent.futures`. Task được đẩy vào Background Thread của chính Process Python. Phù hợp cho cấu hình yếu nhưng rủi ro nếu Web Server bị Crash thì Task cũng bay màu.
2. **Production-Ready (Celery + Redis/RabbitMQ)**:
   - **Broker (Redis)**: Làm cái giỏ trung chuyển lưu giữ lệnh chờ thực thi.
   - **Worker Node**: Một Process chạy độc lập ngoài luồng (`celery -A start_mindstack_app.celery worker`). Các Worker này âm thầm bốc Lệnh từ Redis ra và cày. Rất an toàn, có thể đẻ thêm Worker nếu quá tải.

---

## 3. Module Ops (`mindstack_app/modules/ops`)

Thiết kế của module Command/Ops:
- Khác với các module tính năng có UI cho User, Module Ops chủ yếu expose API ẩn hoặc giao tiếp qua CLI Command (ví dụ lệnh Terminal `flask backup-db` hay `flask trigger-cron`).
- **Dashboard quản trị (Admin)**: Module Admin có thể gọi Interface của Ops để hiển thị thanh Tiến Độ (Progress Bar) cho một Backend Task (Ví dụ: Thanh hiển thị Đang sinh Audio 15/100).
- **Log Xử Lý**: Mọi Background Task bị Fail (Exception) đều sẽ được vớt và log vào bảng System Error hoặc gửi cảnh báo Telegram Bot cho quản trị viên (Admin).
