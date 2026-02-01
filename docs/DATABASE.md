# 🗄️ MindStack Database Documentation

## Overview
MindStack sử dụng **SQLAlchemy ORM** với kiến trúc bảng được chia theo module. Hệ thống được thiết kế để hỗ trợ học tập đa phương thức (Flashcard, Quiz, Course) với một lõi theo dõi tiến độ (SRS) thống nhất.

---

## 🏗️ Core Schema (Lõi Hệ Thống)

### 1. User & Auth (`users`)
Lưu trữ thông tin người dùng và phiên đăng nhập.
- **`User`**: Thông tin định danh, vai trò (Admin/User), điểm thưởng, và cấu hình cá nhân.
- **`UserSession`**: Quản lý phiên làm việc của người dùng.

### 2. Learning Content (Nội dung học tập)
MindStack sử dụng cấu trúc **Container-Item** linh hoạt.
- **`LearningContainer`**: Đại diện cho một "Bộ thẻ" (Flashcard Set) hoặc "Bộ câu hỏi" (Quiz Set).
- **`LearningItem`**: Đơn vị học tập nhỏ nhất. Dữ liệu thực tế (câu hỏi, câu trả lời, định nghĩa) được lưu trong trường JSON `content` để linh hoạt thay đổi theo loại item (Flashcard/MCQ).
- **`LearningGroup`**: Cho phép nhóm các container lại với nhau (ví dụ: một khóa học lớn gồm nhiều bộ từ vựng).

### 3. Progress & SRS (Tiến độ học tập)
Đây là phần quan trọng nhất để vận hành thuật toán lặp lại ngắt quãng (FSRS).
- **`LearningProgress`**: Lưu trạng thái học tập của **một User đối với một Item**. 
    - Các trường quan trọng: `stability`, `difficulty`, `retention`, `mastery`, `last_review`.
- **`ReviewLog`**: Lưu lịch sử chi tiết từng lần trả lời của người dùng. Dùng để phân tích và tối ưu thuật toán SRS.
- **`UserContainerState`**: Lưu trạng thái của User đối với cả một bộ thẻ (đang học, đã lưu trữ, cấu hình riêng cho bộ thẻ đó).

### 4. Learning Sessions (Phiên học)
- **`LearningSession`**: Lưu trạng thái một phiên học đang diễn ra (Active Session). Thay thế cho việc lưu vào Cookie, giúp người dùng có thể học tiếp trên thiết bị khác.
    - Lưu danh sách `processed_item_ids` để tránh lặp lại câu hỏi đã trả lời.

---

## 🧩 Module-Specific Tables (Bảng theo tính năng)

### 🎮 Gamification
- **`Badge` & `UserBadge`**: Hệ thống huy hiệu và danh hiệu người dùng đạt được.
- **`ScoreLog`**: Nhật ký thay đổi điểm (Exp) của người dùng.
- **`Streak`**: Theo dõi chuỗi học tập hàng ngày.

### 🤖 AI Integration
- **`ApiKey`**: Quản lý các API Key (Gemini, HuggingFace) với cơ chế xoay vòng.
- **`AiTokenLog`**: Theo dõi lượng token tiêu thụ và chi phí.
- **`AiCache`**: Cache các câu trả lời của AI để tiết kiệm chi phí và tăng tốc độ.

### 🎯 Goals & Stats
- **`Goal` & `UserGoal`**: Hệ thống mục tiêu học tập do người dùng tự đặt.
- **`DailyStat`**: Thống kê tổng hợp theo ngày (số thẻ đã học, thời gian học).

### 🔔 Notifications & Feedback
- **`Notification`**: Thông báo hệ thống, nhắc nhở học tập.
- **`Feedback`**: Ý kiến phản hồi của người dùng về nội dung hoặc lỗi app.

---

## 📊 Quan hệ chính (Key Relationships)

1.  **User 1 : N LearningContainer**: Một người dùng có thể tạo nhiều bộ thẻ.
2.  **LearningContainer 1 : N LearningItem**: Một bộ thẻ chứa nhiều thẻ/câu hỏi.
3.  **User N : M LearningItem (qua LearningProgress)**: Theo dõi tiến độ riêng biệt của từng người dùng trên mỗi thẻ.
4.  **LearningSession 1 : N ReviewLog**: Một phiên học sinh ra nhiều nhật ký trả lời.

---

## 🛠️ Quy tắc khi làm việc với Database

1.  **JSON Fields**: Sử dụng trường JSON cho các dữ liệu không cố định (như `content` của item hoặc `settings` của session). Điều này tránh việc phải migration database quá thường xuyên.
2.  **Safe Deletion**: Ưu tiên sử dụng "Soft Delete" (đánh dấu `is_archived` hoặc `is_active`) thay vì xóa cứng dữ liệu để bảo toàn lịch sử học tập.
3.  **Migration**: Luôn sử dụng lệnh `flask db migrate` và `flask db upgrade` để thay đổi schema. Không sửa trực tiếp file SQLite.
4.  **Relationships**: Luôn định nghĩa `backref` hoặc `back_populates` để dễ dàng truy xuất dữ liệu hai chiều.
