# Báo Cáo Tính Năng: Quiz Import Custom Columns

**Ngày:** 04/01/2026
**Trạng thái:** ✅ Đã hoàn thành (Code & Verify).

---

## 1. Giới thiệu

Tính năng này cho phép người dùng import các file Excel chứa các cột không nằm trong cấu trúc chuẩn của hệ thống (ví dụ: `explanation_extra`, `difficulty_level`, `source_book`, ...). Hệ thống sẽ tự động nhận diện và lưu trữ các cột này vào trường `custom_data`.

## 2. Cơ Chế Hoạt Động (Technical Detail)

Tôi đã cập nhật file xử lý import của module Quiz (`mindstack_app/modules/content_management/quizzes/routes.py`) với các thay đổi sau:

### A. Phân Loại Cột (Column Classification)
Hệ thống sử dụng whitelist để lọc các cột chuẩn, bao gồm:
*   **Thông tin cơ bản:** `item_id`, `question`, `pre_question_text`, `action`.
*   **Đáp án:** `option_a` -> `option_d`, `correct_answer_text`.
*   **Media:** `question_image_file`, `question_audio_file`.
*   **AI & Group:** `ai_prompt`, `ai_explanation`, `guidance`, `group_id`, `group_item_order`, `group_shared_components`.

Tất cả các cột **KHÔNG** thuộc danh sách trên sẽ được coi là **Custom Columns**.

### B. Xử Lý Lưu Trữ
1.  **Tự động gom nhóm:** Các giá trị từ custom columns sẽ được gom vào một dictionary.
2.  **Lưu vào Database:** Dictionary này được gán vào trường `custom_data` của đối tượng `LearningItem` trước khi lưu xuống cơ sở dữ liệu.
3.  **Hỗ trợ cả Thêm Mới & Cập Nhật:**
    *   **Thêm mới (New):** Tạo item mới kèm theo custom data.
    *   **Cập nhật (Existing):** Cập nhật custom data cho item đang có (overwrite hoặc thêm mới key).
    *   **Xuất File (Export):** Khi export quiz ra Excel, các cột này sẽ ĐƯỢC XUẤT RA (Round-trip) đầy đủ.

## 3. Cách Sử Dụng Cho Người Dùng

Bạn chỉ cần thêm cột vào file Excel như bình thường.
**Ví dụ:**
Trong file Excel import Quiz, bạn có thể thêm cột `Ghi Chú Admin`.
*   Hàng 1: "Câu này update ngày 1/1"
*   Hàng 2: "Cần check lại đáp án"

Khi import xong, dữ liệu này sẽ nằm trong `custom_data` của câu hỏi và sẵn sàng để lập trình viên hiển thị lên giao diện hoặc dùng cho các logic khác.

---
*Người thực hiện: Antigravity*
