# mindstack_app/utils/content_renderer.py
# Phiên bản: 1.1
# Mục đích: Centralized BBCode rendering for learning content fields.
# Tự động render BBCode → HTML cho các text fields, skip IDs/URLs/metadata.
# NEW: strip_bbcode() để loại bỏ BBCode khi so sánh đáp án.

import re
from .bbcode_parser import bbcode_to_html

# Regex pattern để loại bỏ tất cả BBCode tags
BBCODE_PATTERN = re.compile(r'\[/?(?:b|i|u|s|color|size|url|quote|code|img|youtube|list|\*)(?:=[^\]]+)?\]', re.IGNORECASE)


def strip_bbcode(text):
    """
    Loại bỏ tất cả BBCode tags từ text.
    Dùng để so sánh đáp án: user nhập 'hehe' phải match với '[b]hehe[/b]'.
    
    Args:
        text: Text có thể chứa BBCode
        
    Returns:
        str: Text đã loại bỏ BBCode tags
    """
    if not text or not isinstance(text, str):
        return text or ''
    return BBCODE_PATTERN.sub('', text).strip()

# Fields to skip (không render BBCode)
SKIP_FIELDS = {
    # IDs
    'item_id', 'container_id', 'group_id', 'user_id', 'external_id', 'log_id',
    'session_id', 'progress_id', 'set_id',
    
    # URLs và paths
    'front_audio_url', 'back_audio_url', 'front_img', 'back_img',
    'audio_url', 'image_url', 'question_audio_file', 'question_image_file',
    'memrise_audio_url', 'video_url',
    
    # Metadata numbers
    'order_in_container', 'item_type', 'correct_answer', 'correct_index',
    'display_number', 'main_number', 'sub_index',
    
    # Booleans và flags
    'supports_pronunciation', 'supports_writing', 'supports_quiz',
    'supports_essay', 'supports_listening', 'supports_speaking',
    'can_edit', 'is_correct', 'has_data',
    
    # Keys cho options (A, B, C, D là keys, values sẽ được render)
    # Không skip 'A', 'B', 'C', 'D' vì ta muốn render values của chúng
}


def render_text_field(value, field_name=None, audio_folder=None, image_folder=None):
    """
    Render BBCode trong một text field đơn lẻ.
    
    Args:
        value: Giá trị cần render
        field_name: Tên field (để check skip list)
        audio_folder: Thư mục chứa audio (cho BBCode)
        image_folder: Thư mục chứa ảnh (cho BBCode)
        
    Returns:
        str: HTML đã render hoặc value gốc nếu không phải string
    """
    if field_name and field_name.lower() in SKIP_FIELDS:
        return value
    if not isinstance(value, str):
        return value
    if not value.strip():
        return value
    return bbcode_to_html(value, audio_folder=audio_folder, image_folder=image_folder)


def render_content_dict(content_dict, parent_key=None, audio_folder=None, image_folder=None):
    """
    Render BBCode trong tất cả text fields của một content dict.
    Hỗ trợ nested dicts (như 'options': {'A': '...', 'B': '...'}).
    
    Args:
        content_dict: Dict chứa content cần render
        parent_key: Key của parent dict (để xử lý nested)
        audio_folder: Thư mục chứa audio (cho BBCode)
        image_folder: Thư mục chứa ảnh (cho BBCode)
        
    Returns:
        dict: Content đã được render BBCode
    """
    if not isinstance(content_dict, dict):
        return content_dict
    
    result = {}
    for key, value in content_dict.items():
        key_lower = key.lower() if isinstance(key, str) else key
        
        # Skip fields trong skip list
        if key_lower in SKIP_FIELDS:
            result[key] = value
            continue
            
        if isinstance(value, dict):
            # Recursive cho nested dicts (như options, shared_values)
            result[key] = render_content_dict(value, parent_key=key, audio_folder=audio_folder, image_folder=image_folder)
        elif isinstance(value, list):
            # Handle lists (render each string item)
            result[key] = [
                bbcode_to_html(item, audio_folder=audio_folder, image_folder=image_folder) if isinstance(item, str) else item
                for item in value
            ]
        elif isinstance(value, str) and value.strip():
            # Render text fields
            result[key] = bbcode_to_html(value, audio_folder=audio_folder, image_folder=image_folder)
        else:
            # Keep as-is (numbers, booleans, None, empty strings)
            result[key] = value
            
    return result


def render_item_content(item_dict, audio_folder=None, image_folder=None):
    """
    Render BBCode cho toàn bộ item dict (flashcard hoặc quiz item).
    Áp dụng cho item_dict['content'] và các text fields ở top level.
    
    Args:
        item_dict: Dict chứa item data
        audio_folder: Thư mục chứa audio (cho BBCode)
        image_folder: Thư mục chứa ảnh (cho BBCode)
        
    Returns:
        dict: Item dict đã được render
    """
    if not isinstance(item_dict, dict):
        return item_dict
        
    result = dict(item_dict)  # Shallow copy
    
    # Render content dict nếu có
    if 'content' in result and isinstance(result['content'], dict):
        result['content'] = render_content_dict(result['content'], audio_folder=audio_folder, image_folder=image_folder)
    
    # Render các text fields ở top level
    for field in ['ai_explanation', 'note_content', 'explanation']:
        if field in result and isinstance(result[field], str):
            result[field] = bbcode_to_html(result[field], audio_folder=audio_folder, image_folder=image_folder)
    
    return result
