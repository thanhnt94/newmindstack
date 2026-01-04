# Báo Cáo Kiểm Tra Chức Năng Import Flashcard

**Ngày:** 04/01/2026
**Trạng thái:** ✅ Đã có chức năng **IMPORT và EXPORT** cột tùy chỉnh (Custom Columns).

---

## 1. Kết Quả Kiểm Tra

Sau khi kiểm tra mã nguồn tại `mindstack_app/modules/content_management/flashcards/services.py`, tôi xác nhận hệ thống **ĐÃ** có logic xử lý các cột dữ liệu không bắt buộc (Custom Columns).

### Cơ chế hoạt động:

1.  **Phân loại cột tự động:**
    Khi đọc file Excel, hệ thống sẽ phân loại các cột thành 4 nhóm:
    *   **Cột Hệ thống (System):** `item_id`, `order_in_container`, `action`.
    *   **Cột Tiêu chuẩn (Standard):** `front`, `back`, `front_audio_url`, `back_img`, v.v...
    *   **Cột AI (AI):** `ai_explanation`.
    *   **Cột Tùy chỉnh (Custom):** **Tất cả các cột còn lại** không thuộc 3 nhóm trên.

2.  **Lưu trữ:**
    *   Bất kỳ cột nào thuộc nhóm **Custom** (ví dụ: `MyNotes`, `ExampleSentence`, `Difficulty`) sẽ được gom vào một đối tượng JSON.
    *   Dữ liệu này được lưu vào trường `custom_data` trong bảng `learning_items`.

3.  **Xử lý Logic:**
    *   Nếu ô Excel có dữ liệu -> Lưu vào `custom_data`.
    *   Nếu ô Excel trống -> Bỏ qua hoặc xóa key đó khỏi `custom_data` (nếu đang update).

## 2. Mã Nguồn Minh Họa

Dưới đây là đoạn code thực tế đang chạy trong `FlashcardExcelService`:

```python
# 1. Phát hiện cột custom
all_known_columns = cls.SYSTEM_COLUMNS | cls.STANDARD_COLUMNS | cls.AI_COLUMNS
custom_columns = [col for col in df.columns if col not in all_known_columns]

# 2. Xử lý lưu trữ (Trong vòng lặp xử lý từng hàng)
custom_dict = {}
for col in custom_columns:
    cell_value = _get_cell(row, col)
    if cell_value:
        custom_dict[col] = cell_value

# 3. Lưu vào Database
new_item = LearningItem(
    ...,
    custom_data=custom_dict if custom_dict else None,
    ...
)
```

## 3. Kết Luận

## 4. Tính năng Export

Khi bạn **Export (Xuất file)** bộ Flashcard, các cột tùy chỉnh này **SẼ** được xuất ra file Excel. Dữ liệu được bảo toàn trọn vẹn (Round-trip).
