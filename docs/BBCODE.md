# BBCode Support Documentation

MindStack hỗ trợ BBCode để format nội dung trong nhiều hệ thống học tập.

---

## Hệ thống được hỗ trợ

| Module | Fields được render | Ghi chú |
|--------|-------------------|---------|
| **Course Lessons** | `bbcode_content` | Nội dung bài học khóa học |
| **Flashcard** | `front`, `back`, `front_audio_content`, `back_audio_content`, `ai_explanation` | Mặt trước/sau thẻ |
| **Quiz** | `question`, `options` (A/B/C/D), `explanation`, `pre_question_text`, `ai_explanation`, `note_content` | Câu hỏi và đáp án |
| **Vocab MCQ** | `question`, `choices`, `correct_answer` | Chế độ trắc nghiệm từ vựng |
| **Vocab Typing** | `prompt` | Phần câu hỏi hiển thị (answer giữ nguyên để validation) |
| **Vocab Listening** | `meaning` | Nghĩa của từ (answer giữ nguyên để validation) |

---

## Tags được hỗ trợ

### Tags chuẩn (Built-in)

| Tag | Cú pháp | Kết quả | Ví dụ |
|-----|---------|---------|-------|
| **Bold** | `[b]text[/b]` | **text** | `[b]từ quan trọng[/b]` |
| **Italic** | `[i]text[/i]` | *text* | `[i]ví dụ[/i]` |
| **Underline** | `[u]text[/u]` | <u>text</u> | `[u]gạch dưới[/u]` |
| **Strikethrough** | `[s]text[/s]` | ~~text~~ | `[s]đã xóa[/s]` |
| **Color** | `[color=red]text[/color]` | <span style="color:red">text</span> | `[color=#ff0000]màu đỏ[/color]` |
| **Size** | `[size=20]text[/size]` | Chữ to hơn | `[size=14]chữ nhỏ[/size]` |
| **Quote** | `[quote]text[/quote]` | Khối trích dẫn | `[quote]Câu nói hay[/quote]` |
| **Code** | `[code]text[/code]` | `monospace` | `[code]const x = 1[/code]` |
| **URL** | `[url=link]text[/url]` | Hyperlink | `[url=https://google.com]Google[/url]` |
| **List** | `[list][*]item[/list]` | Danh sách | `[list][*]Mục 1[*]Mục 2[/list]` |

### Tags tùy chỉnh (MindStack Custom)

| Tag | Cú pháp | Mô tả |
|-----|---------|-------|
| **YouTube** | `[youtube]URL hoặc ID[/youtube]` | Nhúng video YouTube responsive |
| **Image** | `[img]URL[/img]` | Hiển thị hình ảnh |

---

## Ví dụ sử dụng

### Flashcard

**Front:**
```
[b]Vocabulary[/b]: [i]Noun[/i]
```

**Back:**
```
[b]Từ vựng[/b]: [i]Danh từ[/i]

[youtube]https://youtube.com/watch?v=abc123[/youtube]
```

### Quiz Question

**Question:**
```
[b]Câu hỏi:[/b] Đâu là thủ đô của Việt Nam?

[color=blue]Gợi ý: Ở miền Bắc[/color]
```

**Explanation:**
```
Đáp án đúng là [b]Hà Nội[/b].

[youtube]dQw4w9WgXcQ[/youtube]
```

---

## Fields KHÔNG được render BBCode

Các field sau sẽ giữ nguyên, không xử lý BBCode:

- IDs: `item_id`, `container_id`, `group_id`, `user_id`
- URLs: `front_audio_url`, `back_audio_url`, `front_img`, `back_img`, `audio_url`
- Metadata: `correct_answer`, `order_in_container`, `item_type`
- Flags: `supports_pronunciation`, `supports_writing`, `can_edit`

---

## Lưu ý kỹ thuật

1. **An toàn HTML**: BBCode được chuyển sang HTML an toàn, không cho phép inject script
2. **YouTube URL formats**: Hỗ trợ nhiều format:
   - `https://youtube.com/watch?v=VIDEO_ID`
   - `https://youtu.be/VIDEO_ID`
   - `https://youtube.com/embed/VIDEO_ID`
   - `https://youtube.com/shorts/VIDEO_ID`
   - Hoặc chỉ `VIDEO_ID` (11 ký tự)
3. **Nested tags**: Có thể lồng tags: `[b][i]bold italic[/i][/b]`
4. **Answer Validation**: Khi so sánh đáp án (Typing, Listening), BBCode sẽ được tự động loại bỏ:
   - Đáp án lưu: `[b]hehe[/b]`
   - User nhập: `hehe`
   - Kết quả: ✅ Đúng (BBCode được strip trước khi so sánh)
