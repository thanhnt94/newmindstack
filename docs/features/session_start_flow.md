# Quy Trình Bắt Đầu Một Phiên Học (Session Start Flow)

Bài viết tập trung vào luồng Backend (API + Logic) xảy ra khi người dùng bấm phím "Bắt đầu học" từ giao diện thiết lập (Setup UI).

Module chịu trách nhiệm chính: `session` kết hợp với `vocabulary` (thông qua Factory).

---

## 1. Request Từ Phía Khách (Setup UI Submits)

Mọi session đều bắt đầu khi màn hình Setup UI gom toàn bộ tùy chọn (như số lượng câu hỏi, bật FSRS hay không, đảo ngữ hay xuôi ngữ) thành một Cấu trúc Dữ Liệu ngầm và POST lên Server đường dẫn chung.

 Ví dụ với Module Tư Vựng: `/vocab/start_session/<set_id>`
* Payload POST Form / JSON bao gồm:
  - `learning_mode`: (Bắt buộc) `flashcard`, `mcq`, `typing`...
  - `card_limit`: Số lượng.
  - Vị trí Text (Mặt trước hay sau).

## 2. Validation Với Schema Pydantic

Tầng Controller / Route đầu tiên nhận Request KHÔNG được phép xử lý dữ liệu thô. Thay vào đó, nó ném Data vào **`StartSessionSchema`** (được viết bằng thư viện `pydantic`).

- Bắt lỗi bảo mật: Đảm bảo limit không quá 200 câu. Đảm bảo mode nằm trong tập Enum hợp lệ.
- Nếu dữ liệu rác/Hack, ném Exception 400 Bad Request ngay lập tức. Database an toàn.

## 3. Khởi Tạo Session Manager bằng Factory Pattern

Đã có cấu hình hợp lệ, API gọi Trái tim của quá trình - Factory:
`manager = SessionManagerFactory.create(learning_mode, current_user.id, set_id)`

Factory này đọc chuỗi `learning_mode`, rẽ nhánh và gọi hàm khởi tạo (Constructor `__init__`) của đúng công cụ:
- Ví dụ nếu gọi MCQ: Factory khởi tạo `MCQSessionManager()`.
- Tại bước `__init__` này, Manager có thể chọc xuống DB lấy lên Toàn bộ thẻ từ vựng thuộc về Set ID đó để cache ngầm.

## 4. Hành Vi `manager.initialize_session(config)`

Mọi Manager đều bắt buộc có hàm `initialize_session` do chuẩn kế thừa Interface quy định.
Một hàm này thường làm 3 việc nặng nhọc nhất:
1. **Lược Chọn Dữ Liệu (Filtering - FSRS integration)**: Lọc ra thẻ tùy theo chế độ (Mode). 
    - `srs` (Mặc định): Lọc ưu tiên thẻ đến hạn (Due), sau đó là thẻ mới.
    - `new` (Chỉ học từ mới): Lọc riêng các thẻ chưa từng học, hiển thị theo trình tự.
    - `cram` (Ôn tập): Ôn tập ngẫu nhiên thẻ đã học.
2. **Khởi Tạo Cấu Trúc Nháp (Drafting)**: Tạo một object `SessionData` chứa List ID cần học.
3. **Ghi Database**: Gọi `db.session.add(session)` và lưu vào bảng `learning_sessions`. Server lấy ra được một ID vĩnh viễn: `session.session_id` (ví dụ `10542`).

## 5. Chuyển Hướng Giao Diện (The URL Redirect)

Thành quả của quá trình trên không trả về chuỗi JSON chứa 20 câu. Nó trả về một `redirect_url`. (Ví dụ `/vocab/mcq/10542`).

**Tại Sao Không Trả Thẳng Giao Diện Lên Luôn?**
- Tuân thủ chuẩn **PRG Pattern (Post-Redirect-Get)** của Web Engineering.
- Nếu trả thẳng trang Web sau Post, nhỡ người dùng ấn nút Refresh (F5) trên trình duyệt, trình duyệt sẽ báo Form Resubmission, đẩy DB lặp lại việc tạo ra Session ID `10543` rác vô nghĩa.
- Bằng cách Redirect qua GET Route (`/vocab/mcq/<id>`), User F5 cả 100 lần thì cũng chỉ load lại ID 10542 hiện tại. Rất an toàn, mượt mà.

---

### Tổng Kết
Luồng gọi một Session "Start" có thể được tóm lược:
1. `Client` -> POST Request -> Cửa ngõ `Route`.
2. `Route` nhờ `StartSessionSchema` chặn cửa kiểm tra vé. Vé xịn -> Dẫn vào.
3. `Route` đưa thông tin cho Công xưởng `SessionManagerFactory`.
4. Công xưởng rèn ra cho một `SessionManager` đồ tể hạng nặng.
5. Cấp cờ lệnh `manager.initialize_session()` -> Móc DB -> Chốt Record ID Nháp.
6. `Route` trả về mã Redirect `302 /vocab/<mode>/<session_id>`. Hết nhiệm vụ Khởi tạo.
