---
description: AI Guidelines - Quy tắc bắt buộc khi AI làm việc với MindStack project
---

# 🚀 Refactoring Protocol (Giao thức Tái cấu trúc)

Khi hệ thống nhận yêu cầu **"refactor"**, **"review code"**, hoặc **"cấu trúc lại module"**, AI **BẮT BUỘC** phải thực hiện các bước sau theo thứ tự nghiêm ngặt:

---

### 1. 🔍 Retrieve Context (Truy xuất ngữ cảnh)
Trước khi đưa ra bất kỳ đề xuất sửa đổi nào, AI cần:
* **Đọc file:** `docs/MODULE_STRUCTURE.md` để nắm vững kiến trúc Hexagonal và các quy tắc phụ thuộc.
* **Đọc file:** `docs/MODULE_REFACTOR_CHECKLIST_V3_REVISED.md` để lấy danh sách kiểm tra (checklist) nghiệm thu.

### 2. 🛡️ Strict Compliance Check (Kiểm tra tuân thủ)
Thực hiện đối soát mã nguồn hiện tại:
* So sánh code thực tế với cấu trúc chuẩn trong `MODULE_STRUCTURE.md`.
* **Báo lỗi ngay lập tức** nếu phát hiện vi phạm các quy tắc cốt lõi:
    * **Engine Isolation:** Engine import DB hoặc Framework.
    * **Service Orchestration:** Service xử lý logic nghiệp vụ thuần túy thay vì gọi Engine.

### 3. 🛠️ Refactor Execution (Thực thi)
Khi thực hiện viết code mới hoặc tái cấu trúc:
* Phải tuân thủ nghiêm ngặt bảng phân loại trong `MODULE_REFACTOR_CHECKLIST_V3_REVISED.md` (**Mục 2 - Bảng Quyết định**).
* **Nguyên tắc "Pay as you go":** * *Ví dụ:* Nếu là module CRUD đơn giản, **KHÔNG ĐƯỢC** tạo file `engine/core.py` để tránh dư thừa mã nguồn.

### 4. 📝 Final Output (Đầu ra)
Kết quả phản hồi phải đảm bảo:
* Luôn trích dẫn quy tắc cụ thể nào đang được áp dụng từ hệ thống tài liệu `docs/`.
* Liệt kê các thay đổi dưới dạng checklist tương ứng với các bước trong `REFACTOR_CHECKLIST` để người dùng dễ dàng theo dõi và nghiệm thu.

---
*Giao thức này đảm bảo mọi module trong MindStack v2.0 luôn đồng nhất về kiến trúc và chất lượng.*
