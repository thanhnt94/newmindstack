# mindstack_app/modules/shared/utils/bbcode_parser.py
# Phiên bản: 1.2
# Mục đích: Cung cấp hàm để chuyển đổi BBCode sang HTML an toàn.
# ĐÃ SỬA: Kích hoạt trình xử lý (formatter) cho thẻ [youtube] để nhúng video.

import bbcode

# --- Cấu hình Parser ---

# 1. Tạo một parser mới
parser = bbcode.Parser()

# 2. Định nghĩa cách thẻ [img] sẽ được chuyển đổi sang HTML
#    - 'img': Tên thẻ BBCode.
#    - '<img src="%(value)s" ... />': Mẫu HTML đầu ra. %(value)s sẽ là URL bên trong thẻ.
#    - replace_links=False: Rất quan trọng, để parser không cố gắng biến URL thành thẻ <a>.
#    - Thêm class và alt để dễ dàng tạo kiểu và cải thiện khả năng truy cập.
parser.add_simple_formatter('img', '<img src="%(value)s" class="parsed-content-img" alt="Hình ảnh bài học" />', replace_links=False)

# 3. Kích hoạt trình xử lý cho thẻ [youtube]
#    - 'youtube': Tên thẻ BBCode.
#    - '%(value)s' sẽ là ID của video YouTube.
parser.add_simple_formatter('youtube', '<iframe width="560" height="315" src="https://www.youtube.com/embed/%(value)s" frameborder="0" allowfullscreen></iframe>', replace_links=False)


# --- Hàm chuyển đổi ---

def bbcode_to_html(bbcode_text):
    """
    Mô tả: Chuyển đổi một chuỗi BBCode thành HTML sử dụng parser đã được cấu hình.
    Args:
        bbcode_text (str): Chuỗi BBCode cần chuyển đổi.
    Returns:
        str: Chuỗi HTML đã được chuyển đổi.
    """
    if not bbcode_text:
        return ""
    return parser.format(bbcode_text)

