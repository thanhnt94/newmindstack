# Hướng Dẫn Tạo Bộ Thẻ Flashcard

## Tổng quan

Bộ thẻ Flashcard được import từ file **Excel (.xlsx)** với 2 sheets:
- **Data** (bắt buộc): Chứa dữ liệu các thẻ
- **Info** (tùy chọn): Cấu hình bộ thẻ

---

## Sheet Data - Cấu trúc cột

### Cột bắt buộc

| Cột | Mô tả |
|-----|-------|
| `front` | Nội dung mặt trước thẻ |
| `back` | Nội dung mặt sau thẻ |

### Cột hệ thống (tùy chọn)

| Cột | Mô tả |
|-----|-------|
| `item_id` | ID thẻ (để cập nhật/xóa thẻ đã có) |
| `order_in_container` | Thứ tự thẻ trong bộ |
| `action` | Hành động: `update`, `create`, `delete`, `skip` |
| `ai_explanation` | Giải thích từ AI |

### Cột media chuẩn (tùy chọn)

| Cột | Mô tả |
|-----|-------|
| `front_img` | Đường dẫn ảnh mặt trước |
| `back_img` | Đường dẫn ảnh mặt sau |
| `front_audio_url` | Đường dẫn audio mặt trước |
| `back_audio_url` | Đường dẫn audio mặt sau |
| `front_audio_content` | Nội dung TTS mặt trước |
| `back_audio_content` | Nội dung TTS mặt sau |

### Cột tùy chỉnh (Custom)

Bạn có thể thêm **bất kỳ cột nào khác** và hệ thống sẽ tự động lưu vào `custom_data`:

```
example, notes, hint, kanji, romaji, pronunciation, sentence, v.v.
```

---

## Sheet Info - Cấu hình (tùy chọn)

| Key | Value | Mô tả |
|-----|-------|-------|
| `image_base_folder` | `set-name/images` | Thư mục chứa ảnh |
| `audio_base_folder` | `set-name/audio` | Thư mục chứa audio |
| `cover_image` | `cover.jpg` | Ảnh bìa bộ thẻ |

---

## Ví dụ file Excel

### Sheet Data

| front | back | front_audio_url | example | notes |
|-------|------|-----------------|---------|-------|
| Hello | Xin chào | audio/hello.mp3 | Hello world! | Lời chào phổ biến |
| Goodbye | Tạm biệt | audio/bye.mp3 | Goodbye friend | Lời chào tạm biệt |

### Sheet Info

| Key | Value |
|-----|-------|
| image_base_folder | english-vocab/images |
| audio_base_folder | english-vocab/audio |
| cover_image | cover.jpg |

---

## Kết quả trong Database

```json
{
  "content": {
    "front": "Hello",
    "back": "Xin chào",
    "front_audio_url": "english-vocab/audio/hello.mp3"
  },
  "custom_data": {
    "example": "Hello world!",
    "notes": "Lời chào phổ biến"
  }
}
```

---

## Giá trị Action

| Giá trị | Mô tả |
|---------|-------|
| `create`, `new`, `add` | Tạo thẻ mới |
| `update`, `edit`, `modify` | Cập nhật thẻ (cần có `item_id`) |
| `delete`, `remove` | Xóa thẻ (cần có `item_id`) |
| `skip`, `keep`, `ignore` | Giữ nguyên thẻ |

---

## Lưu ý quan trọng

1. **Đường dẫn media**: Chỉ cần ghi tên file nếu đã cấu hình `image_base_folder`/`audio_base_folder` trong sheet Info
2. **URL tuyệt đối**: Các đường dẫn `http://` hoặc `https://` sẽ được giữ nguyên
3. **Cột tùy chỉnh**: Mỗi bộ thẻ có thể có các cột khác nhau - hệ thống tự động nhận diện
4. **Thứ tự cột**: Không quan trọng, hệ thống nhận diện theo tên cột
