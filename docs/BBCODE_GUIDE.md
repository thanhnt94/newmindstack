# Hướng dẫn sử dụng BBCode trong MindStack

BBCode (Bulletin Board Code) là một tập hợp các thẻ định dạng văn bản đơn giản được sử dụng trong hệ thống MindStack để làm cho nội dung bài học, thẻ flashcard và câu hỏi trở nên sinh động hơn.

## 1. Định dạng Văn bản Cơ bản

| BBCode | Kết quả | Ghi chú |
| :--- | :--- | :--- |
| `[b]Văn bản đậm[/b]` | **Văn bản đậm** | Dùng để nhấn mạnh |
| `[i]Văn bản nghiêng[/i]` | *Văn bản nghiêng* | Dùng cho chú thích, từ mượn |
| `[u]Văn bản gạch chân[/u]` | <u>Văn bản gạch chân</u> | Tránh dùng quá nhiều |
| `[s]Văn bản gạch ngang[/s]` | ~~Văn bản gạch ngang~~ | Dùng để chỉ nội dung cũ/sai |

## 2. Màu sắc và Kích thước

### Màu sắc (`[color]`)
Hệ thống sử dụng thuộc tính CSS `color`, do đó bạn có thể sử dụng bất kỳ giá trị màu hợp lệ nào của HTML/CSS:

*   **Tên màu tiếng Anh**: `[color=red]Đỏ[/color]`, `[color=blue]Xanh dương[/color]`, `[color=green]Xanh lá[/color]`, `[color=orange]Cam[/color]`, `[color=purple]Tím[/color]`, `[color=pink]Hồng[/color]`, `[color=gray]Xám[/color]`, `[color=brown]Nâu[/color]`, `[color=black]Đen[/color]`, `[color=white]Trắng[/color]`.
*   **Mã màu Hex (Khuyên dùng)**: `[color=#FF5733]Mã Hex[/color]` (Dùng để lấy chính xác tông màu mong muốn).
*   **Mã màu RGB/HSL**: `[color=rgb(255,0,0)]Mã RGB[/color]` hoặc `[color=hsl(0,100%,50%)]Mã HSL[/color]`.

### Kích thước (`[size]`)
Sử dụng đơn vị `px` hoặc các đơn vị đo lường CSS khác:
*   `[size=18px]Chữ lớn hơn[/size]`
*   `[size=0.8rem]Chữ nhỏ hơn[/size]`

## 3. Căn lề

Bạn có thể căn chỉnh đoạn văn bằng các thẻ sau:
*   `[left]Căn trái[/left]` (Mặc định)
*   `[center]Căn giữa[/center]`
*   `[right]Căn phải[/right]`
*   `[justify]Căn đều hai bên[/justify]`

## 4. Danh sách (List)

Để tạo danh sách liệt kê:
```bbcode
[list]
[*] Mục thứ nhất
[*] Mục thứ hai
[*] Mục thứ ba
[/list]
```

## 5. Liên kết và Hình ảnh

*   **Liên kết:** `[url=https://mindstack.vn]Truy cập MindStack[/url]` hoặc `[url]https://mindstack.vn[/url]`.
*   **Hình ảnh:** `[img]https://example.com/image.png[/img]`.

## 6. Đa phương tiện (YouTube)

MindStack hỗ trợ nhúng video YouTube cực kỳ linh hoạt. Bạn có thể dán toàn bộ link hoặc chỉ ID video:
*   `[youtube]https://www.youtube.com/watch?v=dQw4w9WgXcQ[/youtube]`
*   `[youtube]dQw4w9WgXcQ[/youtube]`

## 7. Khối nội dung đặc biệt

*   **Trích dẫn:** `[quote]Nội dung trích dẫn bài viết...[/quote]`
*   **Mã nguồn:** `[code]print("Hello World")[/code]`

---
> [!TIP]
> **Lưu ý cho Lập trình viên:**
> Khi hiển thị nội dung chứa BBCode trong template Jinja2, hãy luôn sử dụng filter `|safe` để đảm bảo HTML được render đúng cách:
> `{{ content | bbcode | safe }}`
