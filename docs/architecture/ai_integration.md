# Kiến Trúc Tích Hợp AI (AI Integration)

Hệ thống Trí tuệ Nhân tạo (AI) là một "First-Class Citizen" trong MindStack, hỗ trợ đắc lực từ việc dịch thuật, sinh Flashcard tự động, giải thích ngữ pháp đến trò chuyện (Chatbot/Coach).

Tài liệu này giải thích cấu trúc Module AI và luồng giao tiếp dữ liệu.

---

## 1. Cấu Trúc Module AI
Module AI nằm tại `mindstack_app/modules/AI/`. Thiết kế của nó tuân thủ **Adapter Pattern** để hỗ trợ nhiều mô hình ngôn ngữ (LLM) khác nhau (Ví dụ: OpenAI, Google Gemini, Anthropic) mà không ảnh hưởng đến Logic cốt lõi.

### A. Core Components
- **`interface.py`**: Điểm tiếp xúc duy nhất. Mọi module khác (ví dụ: `content_generator`, `chat`) muốn dùng AI đều phải gọi qua `AIInterface`.
- **`services/ai_service.py`**: Service điều hướng chính. Nhận request từ `interface`, quyết định dùng Provider nào, gọi API, và lưu Cache/Token.
- **`providers/`**: Các adapter giao tiếp với bên ngoài. Cấu trúc chuẩn hóa đầu vào (Prompt) và đầu ra (JSON/Text).
  - `gemini_provider.py`
  - `openai_provider.py`

### B. Cơ Chế Lựa Chọn Provider (Fallback mechanism)
Hệ thống lấy thông tin API từ bảng cấu hình hoặc `api_keys` trong CSDL.
1. Nếu Provider A (Gemini) bị lỗi Rate Limit hoặc hết Token, hệ thống tự động Fallback sang Provider B (OpenAI) ngay trong Runtime để đảm bảo luồng học tập của người dùng không bị gián đoạn.

---

## 2. Quản Lý Chi Phí & Token (`ai_token_logs`)
Mọi Request AI đều đi kèm chi phí. Do đó, hệ thống trang bị hệ thống Tracking Token nghiêm ngặt.
- Bảng `ai_token_logs` lưu thông tin:
  - `user_id`: Ai đã gọi Request này.
  - `model_name`: Tên Model (VD: `gemini-1.5-pro`).
  - `input_tokens` / `output_tokens`: Kích thước truy vấn.
  - `feature`: Tính năng gọi AI (Ví dụ: `"Generate Quiz"`, `"Grammar Explanation"`).
- Việc log token này có thể dùng để giới hạn (Rate Limit) user miễn phí và tính tiền user trả phí.

---

## 3. Hệ Thống Bộ Nhớ Đệm (AI Cache)
Để tối ưu chi phí và tăng tốc độ phản hồi (từ 5s -> 0.1s), AI Service chạy qua một lớp Proxy Cache bằng bảng `ai_cache`:
1. Trước khi gửi Prompt lên Cloud, hệ thống tính toán **Mã Băm (Hash)** của Prompt.
2. Query bảng `ai_cache` xem có bản ghi nào trùng Hash không.
3. Nếu có **(Cache Hit)**: Trả về `response_text` ngay lập tức. Tính phí Token = 0.
4. Nếu không **(Cache Miss)**: Gửi lên Gemini/OpenAI. Lấy kết quả lưu vào `ai_cache` đồng thời trả về cho người dùng.
- *Lưu ý*: Với tính năng trò chuyện theo thời gian thực (Chatbot), cơ chế Cache có thể được Bypass qua tham số `use_cache=False`.

---

## 4. Tương Tác Giữa Content Generator và AI
Sự kết hợp thường xuyên nhất của AI là với module `content_generator`. Bảng lưu trữ nội dung AI được thiết kế dạng EAV/Polymorphic (`ai_contents`):
- Khi AI sinh ra một "Giải Thích Từ Vựng", đoạn Text/Markdown rẽ nhánh được lưu vào bảng `ai_contents` và liên kết bằng khóa ngoại `item_id` tới Flashcard tương ứng.
- **Lợi ích**: Điều này giữ cho bảng Core Learning Items (`flashcards`) nhẹ nhàng, trong khi cho phép một Flashcard có vô số dạng Content AI (Dịch nghĩa Tiếng Việt, Ví dụ bằng Tiếng Anh, Sơ đồ tư duy, Mnemonic).

---

### Tổng Kết (Luồng Dữ Liệu)
`Client` -> `Module A (VD: Quiz)` -> `AIInterface.generate(...)` -> `AIService` -> Kiểm tra `ai_cache` -> Gọi `gemini_provider` -> Lưu `ai_token_logs` -> Trả kết quả JSON về `Module A`.
