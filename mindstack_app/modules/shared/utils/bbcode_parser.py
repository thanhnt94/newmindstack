# mindstack_app/modules/shared/utils/bbcode_parser.py
# Phiên bản: 2.1
# Mục đích: Cung cấp hàm để chuyển đổi BBCode sang HTML an toàn.
# ĐÃ SỬA: Khắc phục lỗi nhúng video bằng cách sử dụng đúng giao thức https cho URL iframe.

import bbcode
import re

# --- Hàm render tùy chỉnh cho YouTube ---

def render_youtube(tag_name, value, options, parent, context):
    """
    Mô tả: Hàm render tùy chỉnh cho thẻ BBCode [youtube].
    Hàm này sẽ tự động trích xuất ID video từ các định dạng URL phổ biến của YouTube
    và tạo ra mã HTML iframe để nhúng video.
    """
    # Các mẫu Regex để tìm ID video trong nhiều loại link YouTube
    youtube_regex_patterns = [
        r'(?:https?:\/\/)?(?:www\.)?youtube\.com\/watch\?v=([a-zA-Z0-9_-]{11})',
        r'(?:https?:\/\/)?(?:www\.)?youtu\.be\/([a-zA-Z0-9_-]{11})',
        r'(?:https?:\/\/)?(?:www\.)?youtube\.com\/embed\/([a-zA-Z0-9_-]{11})',
    ]

    video_id = None
    # Lặp qua các mẫu regex để tìm ID
    for pattern in youtube_regex_patterns:
        match = re.search(pattern, value)
        if match:
            video_id = match.group(1)
            break
            
    # Nếu không tìm thấy ID nào khớp, có thể người dùng chỉ nhập ID
    if not video_id:
        if re.match(r'^[a-zA-Z0-9_-]{11}$', value):
            video_id = value

    if video_id:
        # ĐÃ SỬA: Thay đổi http thành https để đảm bảo video được tải đúng chuẩn bảo mật.
        embed_html = (
            '<div class="youtube-embed-container" style="position: relative; padding-bottom: 56.25%%; height: 0; overflow: hidden; max-width: 100%%;">'
            '<iframe src="https://www.youtube.com/embed/{video_id}" '
            'title="YouTube video player" frameborder="0" '
            'allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share" '
            'referrerpolicy="strict-origin-when-cross-origin" allowfullscreen '
            'style="position: absolute; top: 0; left: 0; width: 100%%; height: 100%%;">'
            '</iframe></div>'
        ).format(video_id=video_id)
        return embed_html
    else:
        # Trả về thông báo lỗi nếu không trích xuất được ID
        return '[Lỗi: Link YouTube không hợp lệ]'

# --- Cấu hình Parser ---

# 1. Tạo một parser mới
parser = bbcode.Parser()

# 2. Định nghĩa cách thẻ [img] sẽ được chuyển đổi sang HTML
parser.add_simple_formatter('img', '<img src="%(value)s" class="parsed-content-img" alt="Hình ảnh bài học" />', replace_links=False)

# 3. Đăng ký hàm render tùy chỉnh cho thẻ [youtube]
parser.add_formatter('youtube', render_youtube)


# --- Hàm chuyển đổi chính ---

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