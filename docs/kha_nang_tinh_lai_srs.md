# Khả Năng Tính Toán Lại SRS & Memory Power

Tài liệu này phân tích tính khả thi của việc tính lại (Recalculate/Replay) toàn bộ chỉ số SRS và Memory Power khi thuật toán thay đổi.

**Kết luận nhanh:** ✅ **HOÀN TOÀN CÓ THỂ**.

---

## 1. Tại sao có thể làm được?

Để tính toán lại trạng thái hiện tại (Current State) của một thẻ học, chúng ta chỉ cần 2 yếu tố:
1.  **Trạng thái khởi đầu:** Mặc định là 'new'.
2.  **Chuỗi sự kiện lịch sử (Event Logs):** Danh sách tất cả các lần học trong quá khứ.

Hệ thống hiện tại đã có bảng `review_logs` lưu trữ đầy đủ "Chuỗi sự kiện" này.

### Cấu trúc bảng `review_logs` hiện tại:
*   `item_id`: Xác định thẻ học.
*   `timestamp`: Thời gian học (quan trọng để tính khoảng cách giữa các lần học).
*   `rating`: Chất lượng câu trả lời (Raw Input).
*   `review_type`: Loại hình học (Flashcard/Quiz).

Khi bạn muốn thay đổi công thức SRS (ví dụ: đổi từ SM-2 sang FSRS), bạn chỉ cần viết một script thực hiện các bước sau:
1.  **Reset:** Đặt `learning_progress` của user về trạng thái gốc (`new`, `interval=0`, `ef=2.5`).
2.  **Replay:** Chạy vòng lặp qua từng dòng trong `review_logs` (xếp theo thời gian tăng dần).
3.  **Apply:** Với mỗi dòng log, áp dụng công thức MỚI để tính ra trạng thái tiếp theo.
4.  **Save:** Cập nhật kết quả cuối cùng vào `learning_progress`.

## 2. Ví dụ minh họa

Giả sử bạn có lịch sử học của thẻ "Hello":

| Thời gian | Hành động | Rating (Cũ) | Thuật toán Cũ (SM-2) | **Nếu đổi sang Thuật toán Mới (FSRS)** |
| :--- | :--- | :--- | :--- | :--- |
| 01/01 08:00 | Học lần 1 | Good (4) | Next: 1 ngày | (Tính lại) -> Next: 2 ngày |
| 02/01 08:00 | Học lần 2 | Hard (3) | Next: 3 ngày | (Tính lại dựa trên kết quả mới ở trên) -> Next: 4 ngày |

Vì `rating` (Chất lượng trả lời thực tế của người dùng) là bất biến, nên kết quả tính toán có thể thay đổi linh hoạt tùy theo công thức bạn áp dụng.

## 3. Lưu ý kỹ thuật

*   **Thời gian xử lý:** Nếu dữ liệu lớn (hàng triệu logs), việc chạy script replay có thể mất nhiều thời gian. Nên chạy offline (background job).
*   **Snapshot Fields:** Các trường như `mastery_snapshot` trong bảng `review_logs` chỉ có giá trị tham khảo tại thời điểm đó. Khi tính lại, các giá trị này sẽ không còn chính xác với công thức mới (nhưng không ảnh hưởng đến logic luồng).

---
*Phân tích dựa trên Schema ngày 04/01/2026.*
