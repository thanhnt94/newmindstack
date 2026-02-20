# Thống Kê & Phân Tích Kỹ Năng (Stats Module)

Module **Stats** (Thống kê) trong MindStack là "Mỏ vàng" dữ liệu. Hiện tại, ứng dụng đã có cơ sở hạ tầng tracking 100% mọi thao tác (click, time, rating), từ đó có thể sinh ra vô vàn dạng Biểu đồ phân tích (Analytics Charts) để tăng tính chuyên nghiệp cho nền tảng.

Tài liệu này tổng hợp "Hiện trạng thu thập Data" và "Những gì có thể hiển thị".

---

##  bản Data Đang Có (The Data Goldmine)

Sức mạnh của Stats Module đến từ sự đóng góp của 3 bảng dữ liệu cốt lõi:

1. **`study_logs` (Lịch Sử Tương Tác)**
   - *Ghi nhận:* Item ID, User ID, Chế độ học (Typing/MCQ), Start time, End time (Review duration), Rating, Đúng/Sai.
   - *Tính năng:* Nó giống như Logging Analytics của Google. Biết chính xác User gõ phím sai chữ gì vào lúc mấy giờ đêm.
2. **`item_memory_states` (Bảng FSRS)**
   - *Ghi nhận:* Stability (Trí nhớ), Difficulty (Độ khó FSRS), Repetitions (Số lần học), Lapses (Số lần quên).
   - *Tính năng:* Điểm cốt lõi nhất của Ứng dụng Học tập (Giúp User Review trí nhớ dài hạn).
3. **`score_logs` (Lịch Sử Điểm Số)**
   - *Ghi nhận:* Số điểm kiếm được trong ngày theo từng mốc thời gian.

---

## Các Chart Đang / Cần Hiển Thị (What we can visualize)

Với bộ Data trên, Module `Stats` CÓ THỂ query và truyền cho Frontend vẽ ra các biểu đồ (Dùng `Chart.js` hoặc `ECharts`):

### 1. Retention & Memory (Thống Kê Trí Nhớ FSRS)
- **Biểu đồ Cột (Review Forecast)**: Lấy `due_date`, vẽ biểu đồ xem 7 ngày tới mỗi ngày có bao nhiêu từ Đến Hạn phải ôn tập. Gíup User không bị sốc (Overload).
- **Biểu đồ Tròn (Memory States)**: `New` (Chưa học) vs `Learning` (Đang học ngắc ngứ) vs `Review` (Nhớ khá khá) vs `Relearning` (Quên).
- **Retention Curve (Đường Cong Quên Ebbinghaus)**: Sự phân bổ Stability hiện tại của toàn bộ não bộ của User (Xem mình nhớ được 90% file bao nhiêu thẻ).

### 2. Time & Effort (Thống Kê Công Sức Học)
- **Heatmap Dạng GitHub (Activity Punchcard)**: Mỗi ô vuông là 1 ngày trong năm, màu Xanh càng đậm thì ngày đó tương tác `study_logs` càng nhiều.
- **Biểu Phân Bố Thời Gian (Time Of Day)**: Trục hoành là 24 Giờ. Trục tung là Số Lượng lỗi sai. Cực kỳ thú vị: Chart này sẽ chỉ ra *User thường gõ sai từ vựng nhiều nhất vào lúc 2 giờ sáng*.

### 3. Accuracy & Weakness (Phân Tích Điểm Yếu)
- **Top X Từ Khó Nhất (Hardest Items)**: Query bảng `item_memory_states` sắp xếp theo `difficulty DESC` hoặc `lapses DESC` để liệt kê ra "Top 10 từ bạn luôn luôn bị quên".
- **Typo Word Cloud (Đám Mây Gõ Sai)**: Phân tích bảng `study_logs` (cột `user_answer`) khi học Typing để tổng hợp những cụm ký tự User gõ nhầm nhiều nhất. 

---

## Kiến Trúc Code Cho Tính Năng Mới
Khi bạn rảnh và muốn code thêm một số API để nạp cho các Widget Biểu đồ mới:
1. Tạo một thư mục `services/` trong module `stats/`.
2. Tạo các Queries SQLAlchemy hạng nặng trong các hàm như `def get_daily_activity_heatmap(user_id, num_days=365):...`
3. Cố gắng sử dụng `redis` để Cache kết quả API Thống Kê này lại khoảng 15-30 phút (vì Query đếm hàng nghìn dòng `study_logs` sẽ rất chậm nếu cứ ấn F5 liên tục).
