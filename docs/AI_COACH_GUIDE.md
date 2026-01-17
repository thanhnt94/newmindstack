# AI Coach - Hướng Dẫn Sử Dụng Chi Tiết

## Mục Lục
1. [Tổng quan](#tổng-quan)
2. [Kiến trúc hệ thống](#kiến-trúc-hệ-thống)
3. [Cách sử dụng AI Coach](#cách-sử-dụng-ai-coach)
4. [Hệ thống Prompt](#hệ-thống-prompt)
5. [Quản trị viên: Cấu hình AI Coach](#quản-trị-viên-cấu-hình-ai-coach)
6. [Viết Prompt hiệu quả](#viết-prompt-hiệu-quả)
7. [API Reference](#api-reference)

---

## Tổng quan

**AI Coach** là trợ lý học tập thông minh trong MindStack, sử dụng các mô hình ngôn ngữ lớn (LLM) như Google Gemini và HuggingFace để:

- 📝 **Giải thích từ vựng**: Phân tích ý nghĩa, cung cấp ví dụ thực tế
- 🎯 **Phân tích câu hỏi Quiz**: Giải thích đáp án đúng, tại sao các đáp án khác sai
- 💡 **Trả lời câu hỏi tùy chỉnh**: Dựa trên ngữ cảnh của học liệu
- 🔄 **Tự động tạo nội dung**: Batch generate AI explanations

---

## Kiến trúc hệ thống

```
┌─────────────────────────────────────────────────────────────────┐
│                        FRONTEND                                  │
├─────────────────────────────────────────────────────────────────┤
│  Flashcard Session  │  Quiz Session  │  Stats Modal  │  Admin   │
│  (modal AI)         │  (Hub AI tab)  │  (AI Coach)   │  Console │
└─────────────────────────┬───────────────────────────────────────┘
                          │ POST /ai/get-ai-response
                          ▼
┌─────────────────────────────────────────────────────────────────┐
│                        BACKEND                                   │
├─────────────────────────────────────────────────────────────────┤
│  routes.py          │  prompts.py        │  service_manager.py  │
│  (API endpoint)     │  (prompt builder)  │  (AI client factory) │
└─────────────────────────┬───────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────────┐
│                     AI PROVIDERS                                 │
├────────────────────────────┬────────────────────────────────────┤
│  Google Gemini (Primary)   │  HuggingFace (Secondary/Fallback)  │
│  gemini_client.py          │  huggingface_client.py             │
└────────────────────────────┴────────────────────────────────────┘
```

---

## Cách sử dụng AI Coach

### 1. Trong Flashcard Session (Mobile & Desktop)

**Cách truy cập:**
1. Vào phiên học Flashcard
2. Lật thẻ để xem mặt sau
3. Nhấn nút **🤖 AI** trên thanh công cụ

**Kết quả:**
- AI sẽ phân tích thuật ngữ dựa trên `front` và `back` của thẻ
- Cung cấp giải thích, ví dụ thực tế
- Kết quả được lưu cache, lần sau không cần gọi API lại

---

### 2. Trong Quiz Session

**Cách truy cập:**
1. Sau khi trả lời câu hỏi, nút **💡 Hub** sẽ xuất hiện
2. Mở Hub và chọn tab **🤖 AI Coach**
3. Nhấn **✨ Tạo mới** để gọi AI

**Kết quả:**
- AI phân tích câu hỏi, giải thích đáp án đúng
- Giải thích tại sao các đáp án khác sai
- Cung cấp mẹo hoặc kiến thức mở rộng

---

### 3. Trong trang Thống kê (Stats Modal)

**Cách truy cập:**
1. Mở modal thống kê của bất kỳ học liệu nào
2. Chọn tab **Nội dung** 
3. Chọn sub-tab **✨ AI Coach**
4. Nếu chưa có nội dung, nhấn **Tạo nội dung AI**

---

## Hệ thống Prompt

### Cấu trúc phân cấp (Priority)

AI Coach sử dụng hệ thống prompt **3 cấp độ ưu tiên**:

```
1. Item-level prompt    ← Ưu tiên cao nhất
   (item.content['ai_prompt'])
   
2. Container-level prompt
   (container.ai_settings['custom_prompt'])
   
3. Default prompt       ← Fallback cuối cùng
   (theo item_type: FLASHCARD hoặc QUIZ_MCQ)
```

### Default Prompts

#### Flashcard (Default)
```
Với vai trò là một trợ lý học tập, hãy giải thích ngắn gọn, 
rõ ràng và dễ hiểu về thuật ngữ sau. Tập trung vào ý nghĩa 
cốt lõi, cung cấp ví dụ thực tế về cách dùng.

**Thuật ngữ:** "{front}"
**Định nghĩa/Ngữ cảnh:** "{back}"

Hãy trình bày câu trả lời theo định dạng Markdown.
```

#### Quiz MCQ (Default)
```
Với vai trò là một trợ lý học tập, hãy giải thích cặn kẽ 
câu hỏi trắc nghiệm sau.

**Bối cảnh (nếu có):**
{pre_question_text}

**Câu hỏi:**
{question}
A. {option_a}
B. {option_b}
C. {option_c}
D. {option_d}

**Đáp án đúng:** {correct_answer}
**Hướng dẫn có sẵn:** {explanation}

**Yêu cầu:**
1. Phân tích tại sao đáp án '{correct_answer}' là đúng.
2. Giải thích ngắn gọn tại sao các đáp án còn lại là sai.
3. Cung cấp một mẹo hoặc kiến thức mở rộng hữu ích.

Hãy trình bày câu trả lời một cách logic, rõ ràng, sử dụng 
định dạng Markdown.
```

---

### Các biến placeholder có sẵn

> **Lưu ý:** Tất cả text values sẽ được **tự động loại bỏ BBCode** trước khi đưa vào prompt.  
> Ví dụ: `[b]Hello[/b]` → `Hello`

| Biến | Nguồn | Mô tả |
|------|-------|-------|
| `{front}` | item.content | Mặt trước flashcard |
| `{back}` | item.content | Mặt sau flashcard |
| `{question}` | item.content | Câu hỏi quiz |
| `{pre_question_text}` | item.content | Bối cảnh trước câu hỏi |
| `{option_a}` - `{option_d}` | item.content.options | Các đáp án A, B, C, D |
| `{correct_answer}` | item.content | Đáp án đúng |
| `{explanation}` | item.content | Giải thích có sẵn (nếu có) |
| `{set_title}` | container.title | Tên bộ flashcard/quiz |
| `{set_description}` | container.description | Mô tả bộ |
| `{set_tags}` | container.tags | Tags của bộ |
| `{item_id}` | item.item_id | ID của học liệu |
| `{item_type}` | item.item_type | Loại: FLASHCARD, QUIZ_MCQ |

#### Custom Data Columns (Mới!)

Nếu flashcard/quiz có **custom columns**, có thể sử dụng trong prompt:

| Format | Ví dụ | Mô tả |
|--------|-------|-------|
| `{custom_<tên_cột>}` | `{custom_word_type}` | Sử dụng prefix `custom_` |
| `{<tên_cột>}` | `{word_type}` | Shorthand (nếu không trùng built-in key) |

**Ví dụ:**  
Nếu flashcard có `custom_data = {"word_type": "noun", "topic": "Business"}`

```
Giải thích từ "{front}" 
- Loại từ: {custom_word_type} hoặc {word_type}
- Chủ đề: {custom_topic} hoặc {topic}
```

---

## Quản trị viên: Cấu hình AI Coach

### Truy cập Admin Console

**URL:** `/admin/api-keys`

### Tab 1: Cấu hình & API

#### Chọn Provider
- **Google Gemini** (Recommended): Nhanh, chất lượng cao, hỗ trợ tiếng Việt tốt
- **HuggingFace**: Open source, fallback khi Gemini gặp lỗi

#### Cấu hình Model Gemini
1. Nhấn **Tải/Cập nhật danh sách Model**
2. Tick chọn các model muốn sử dụng
3. Kéo thả để sắp xếp thứ tự ưu tiên (model đầu tiên = primary)
4. Nhấn **Lưu Cấu Hình**

**Recommended models:**
```
gemini-2.0-flash-lite-001    ← Nhanh, tiết kiệm quota
gemini-1.5-flash-001         ← Cân bằng tốc độ/chất lượng
gemini-1.5-pro-001           ← Chất lượng cao nhất
```

#### Quản lý API Keys
- **Thêm Key Mới**: Click "Thêm Key Mới"
- **Trạng thái**:
  - 🟢 Xanh: Hoạt động tốt
  - ⚪ Xám: Đã tắt
  - 🔴 Đỏ: Quota cạn kiệt

### Tab 2: Auto-Generate

Tự động tạo AI Explanation cho nhiều học liệu:

1. Chọn loại nội dung: **Quiz** hoặc **Flashcard**
2. Chọn bộ muốn generate
3. Cài đặt **API Delay** (khuyến nghị: 2 phút để tránh rate limit)
4. Cài đặt **Số lượng tối đa**
5. Nhấn **Bắt đầu tạo**

### Tab 3: Nhật ký Hoạt động

Xem thống kê và logs:
- Biểu đồ requests/tokens theo ngày
- Danh sách chi tiết các request
- Status, latency, error messages

---

## Viết Prompt hiệu quả

### Nguyên tắc cơ bản

1. **Rõ ràng và cụ thể**: Nêu rõ AI cần làm gì
2. **Sử dụng placeholders**: Tận dụng các biến có sẵn
3. **Định dạng output**: Yêu cầu Markdown để hiển thị đẹp
4. **Ngữ cảnh đầy đủ**: Cung cấp đủ thông tin cho AI

### Ví dụ Prompt Tùy Chỉnh

#### Cho bộ Flashcard tiếng Anh:
```
Bạn là giáo viên tiếng Anh. Hãy giải thích từ "{front}" như sau:

1. **Nghĩa**: {back}
2. **Phát âm**: IPA nếu biết
3. **Từ loại**: Noun/Verb/Adj/Adv
4. **Ví dụ thực tế**: 2-3 câu ví dụ
5. **Từ đồng nghĩa**: Liệt kê 2-3 từ
6. **Từ trái nghĩa**: Liệt kê nếu có
7. **Mẹo nhớ**: Cách nhớ dễ dàng

Trình bày theo Markdown.
```

#### Cho bộ Quiz Y học:
```
Đây là câu hỏi Y học từ bộ "{set_title}".

**Câu hỏi:** {question}
**Đáp án đúng:** {correct_answer}

Hãy phân tích như một giáo viên Y khoa:

1. **Giải thích đáp án đúng**: Cơ chế, nguyên lý
2. **Phân tích đáp án sai**: Tại sao không phải
3. **Kiến thức lâm sàng**: Áp dụng thực tế
4. **Tài liệu tham khảo**: Gợi ý sách/nguồn

Trình bày rõ ràng theo Markdown.
```

#### Cho bộ Flashcard Lập trình:
```
Giải thích khái niệm lập trình sau:

**Thuật ngữ:** {front}
**Định nghĩa:** {back}

Yêu cầu:
1. Giải thích đơn giản như cho người mới học
2. Ví dụ code minh họa (nếu có thể)
3. Use case thực tế
4. Các thuật ngữ liên quan
5. Lỗi thường gặp khi sử dụng

Format: Markdown với code blocks khi cần.
```

### Thiết lập Prompt cho Container

**Cách 1: Qua API**
```python
from mindstack_app.models import LearningContainer
from mindstack_app.db_instance import db

container = LearningContainer.query.get(container_id)
container.ai_settings = {
    'custom_prompt': 'Your custom prompt here...'
}
db.session.commit()
```

**Cách 2: Qua Content Editor**
*(Coming soon - trong phần cài đặt bộ học liệu)*

### Thiết lập Prompt cho Item riêng

```python
from mindstack_app.models import LearningItem
from mindstack_app.db_instance import db

item = LearningItem.query.get(item_id)
item.content['ai_prompt'] = 'Custom prompt for this specific item...'
db.session.commit()
```

---

## API Reference

### POST `/ai/get-ai-response`

**Request Body:**
```json
{
    "item_id": 123,
    "prompt_type": "explanation",  // "explanation" | "custom_question"
    "custom_question": "Từ này dùng trong trường hợp nào?",  // Optional
    "force_regenerate": false  // true để bỏ qua cache
}
```

**Response (Success):**
```json
{
    "success": true,
    "response": "<p>Nội dung AI đã render HTML...</p>"
}
```

**Response (Error):**
```json
{
    "success": false,
    "message": "Dịch vụ AI chưa được cấu hình (thiếu API key)."
}
```

### GET `/ai/models`

**Response:**
```json
{
    "success": true,
    "models": [
        {
            "id": "gemini-2.0-flash-lite-001",
            "display_name": "Gemini 2.0 Flash Lite",
            "description": "..."
        }
    ]
}
```

---

## Caching & Performance

### Cơ chế Cache

- Mỗi học liệu có trường `ai_explanation` lưu kết quả
- Lần đầu gọi AI → lưu vào `ai_explanation`
- Các lần sau → trả về từ cache (không gọi API)
- `force_regenerate: true` → bỏ qua cache, gọi API mới

### Rate Limiting

**Google Gemini Free Tier:**
- ~15 requests/minute
- ~1M tokens/day

**Khuyến nghị:**
- Khi Auto-Generate: delay 2 phút giữa các request
- Sử dụng multi-model với priority order
- Monitor logs để tránh quota exhaustion

---

## Troubleshooting

### Lỗi thường gặp

| Lỗi | Nguyên nhân | Giải pháp |
|-----|-------------|-----------|
| "Dịch vụ AI chưa được cấu hình" | Thiếu API key | Thêm key trong Admin |
| "ResourceExhausted (429)" | Quota limit | Chờ reset hoặc thêm key mới |
| "PermissionDenied" | Key không hợp lệ | Kiểm tra lại API key |
| Response trống | Prompt lỗi format | Kiểm tra placeholders |

### Debug Tips

1. **Xem logs**: `/admin/api-keys` → Tab "Nhật ký Hoạt động"
2. **Kiểm tra prompt**: Print `get_formatted_prompt(item)` 
3. **Test trực tiếp**: Dùng Postman gọi API endpoint
4. **Verify key**: Test API key trong Google AI Studio

---

## Best Practices

✅ **Nên làm:**
- Thiết lập prompt tùy chỉnh cho từng loại nội dung
- Sử dụng nhiều API keys và model fallback
- Monitor quota thường xuyên
- Cache hiệu quả với `force_regenerate` khi cần

❌ **Tránh:**
- Gọi API liên tục không delay
- Sử dụng 1 API key duy nhất
- Prompt quá dài hoặc mơ hồ
- Bỏ qua error handling

---

*Tài liệu được tạo bởi AI Coach Documentation System*  
*Phiên bản: 1.0 - Cập nhật: Tháng 1/2026*
