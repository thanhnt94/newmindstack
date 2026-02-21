# mindstack_app/modules/shared/utils/bbcode_parser.py
# Phiên bản: 2.2
# Mục đích: Cung cấp hàm để chuyển đổi BBCode sang HTML an toàn.
# THAY ĐỔI:
# - Giữ https cho iframe YouTube.
# - Mở rộng regex: hỗ trợ youtube.com, m.youtube.com, youtu.be, /embed/, /shorts, có tham số query (&t, &si...).
# - Trim input, cho phép nhập thuần video_id.
# - Gợi ý dùng |safe trong Jinja (xem chú thích cuối file).

import bbcode
import re

# --- Hàm render tùy chỉnh cho YouTube ---

def render_youtube(tag_name, value, options, parent, context):
    """
    Mô tả: Render thẻ BBCode [youtube]...[/youtube].
    - value: có thể là URL (đủ kiểu) hoặc chỉ video_id (11 ký tự).
    Trả về: HTML iframe nhúng video.
    """
    if not value:
        return '[Lỗi: Link YouTube trống]'

    raw = str(value).strip()

    # Nếu người dùng nhập thẳng ID 11 ký tự
    if re.fullmatch(r'[a-zA-Z0-9_-]{11}', raw):
        video_id = raw
    else:
        # Gom các mẫu URL phổ biến (có thể kèm tham số)
        patterns = [
            # https://www.youtube.com/watch?v=VIDEOID
            r'(?:https?:\/\/)?(?:www\.)?(?:m\.)?youtube\.com\/watch\?(?:[^#\s]*&)?v=([a-zA-Z0-9_-]{11})',
            # https://youtu.be/VIDEOID
            r'(?:https?:\/\/)?(?:www\.)?youtu\.be\/([a-zA-Z0-9_-]{11})(?:\?.*)?$',
            # https://www.youtube.com/embed/VIDEOID
            r'(?:https?:\/\/)?(?:www\.)?(?:m\.)?youtube\.com\/embed\/([a-zA-Z0-9_-]{11})(?:\?.*)?$',
            # https://www.youtube.com/shorts/VIDEOID
            r'(?:https?:\/\/)?(?:www\.)?(?:m\.)?youtube\.com\/shorts\/([a-zA-Z0-9_-]{11})(?:\?.*)?$',
        ]
        video_id = None
        for pat in patterns:
            m = re.search(pat, raw)
            if m:
                video_id = m.group(1)
                break

    if not video_id:
        return '[Lỗi: Link YouTube không hợp lệ]'

    # Dùng https để tránh mixed content
    embed_html = (
        '<div class="youtube-embed-container" '
        'style="position: relative; padding-bottom: 56.25%; height: 0; overflow: hidden; max-width: 100%;">'
        f'<iframe src="https://www.youtube.com/embed/{video_id}" '
        'title="YouTube video player" frameborder="0" '
        'allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share" '
        'referrerpolicy="strict-origin-when-cross-origin" allowfullscreen '
        'style="position: absolute; top: 0; left: 0; width: 100%; height: 100%;">'
        '</iframe></div>'
    )
    return embed_html

# --- Custom Img Renderer ---

def render_img(tag_name, value, options, parent, context):
    """
    Render [img]...[/img] with optional relative path resolution.
    Value should be a URL or a filename.
    """
    if not value:
        return ''
    
    src = str(value).strip()
    image_folder = context.get('image_folder')
    
    # Resolve relative path if not absolute and image_folder is provided
    if not src.startswith(('http://', 'https://', '/')) and image_folder:
        from .media_paths import build_relative_media_path
        rel = build_relative_media_path(src, image_folder)
        if rel:
            src = f"/media/{rel}"
            
    return f'<img src="{src}" class="parsed-content-img" alt="Hình ảnh bài học" />'

# --- Cấu hình Parser ---

parser = bbcode.Parser()
# [img]...[/img] - Use custom formatter for path resolution
parser.add_formatter('img', render_img, replace_links=False)

# [center]...[/center]
parser.add_simple_formatter('center', '<div style="text-align: center;">%(value)s</div>')
# [left]...[/left]
parser.add_simple_formatter('left', '<div style="text-align: left;">%(value)s</div>')
# [right]...[/right]
parser.add_simple_formatter('right', '<div style="text-align: right;">%(value)s</div>')
# [justify]...[/justify]
parser.add_simple_formatter('justify', '<div style="text-align: justify;">%(value)s</div>')

# [youtube]URL-hoặc-ID[/youtube]
# strip=True (mặc định) để bỏ \n thừa; replace_links=False để không tự động biến URL trong value thành <a>
parser.add_formatter('youtube', render_youtube, replace_links=False, strip=True)

# [color=red]...[/color]
def render_color(tag_name, value, options, parent, context):
    """Render [color=X]...[/color] with proper color option handling."""
    color = options.get('color', options.get(tag_name, 'inherit'))
    if color and value:
        return f'<span style="color:{color};">{value}</span>'
    return value or ''

parser.add_formatter('color', render_color)

# --- Hàm chuyển đổi chính ---

def bbcode_to_html(bbcode_text, **kwargs):
    """
    Mô tả: Chuyển chuỗi BBCode thành HTML.
    Args:
        bbcode_text (str): Chuỗi BBCode cần chuyển đổi.
        **kwargs: Tham số context (ví dụ image_folder, audio_folder).
    Returns:
        str: HTML đã được chuyển đổi.
    Lưu ý: Khi render trong Jinja2, nhớ dùng |safe để không bị escape HTML.
    """
    if not bbcode_text:
        return ""
    return parser.format(bbcode_text, **kwargs)
