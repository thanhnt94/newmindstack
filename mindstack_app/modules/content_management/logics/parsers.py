"""
Content Parsers - Pure functions for file parsing and data transformation.

This module contains ONLY pure Python logic.
NO database, NO Flask dependencies allowed.
Uses: pandas, openpyxl for file operations.
"""
import re
from typing import List, Dict, Any, Set, Optional, Tuple


# Action normalization aliases
ACTION_ALIASES = {
    'delete': {'delete', 'remove'},
    'skip': {'skip', 'keep', 'none', 'ignore', 'nochange', 'unchanged', 
             'giu nguyen', 'giu-nguyen', 'giu_nguyen'},
    'create': {'create', 'new', 'add', 'insert'},
    'update': {'update', 'upsert', 'edit', 'modify'},
}


# Field normalization aliases
COLUMN_ALIASES = {
    # Common
    'item_id': {'item_id', 'id', 'id câu hỏi', 'id item'},
    'order_in_container': {'order', 'stt', 'order_in_container', 'thứ tự', 'sắp xếp'},

    # Flashcard
    'front': {'front', 'mặt trước', 'mat truoc', 'term', 'từ vựng', 'tu vung', 'từ', 'text 1', 'question'}, # 'question' can be front in FC context
    'back': {'back', 'mặt sau', 'mat sau', 'definition', 'định nghĩa', 'dinh nghia', 'nghĩa', 'nghia', 'answer', 'text 2'}, # 'answer' can be back in FC context
    'front_img': {'front_img', 'ảnh mặt trước', 'anh mat truoc', 'front image', 'image 1'},
    'back_img': {'back_img', 'ảnh mặt sau', 'anh mat sau', 'back image', 'image 2'},
    'front_audio_url': {'front_audio_url', 'audio mặt trước', 'audio mat truoc', 'audio 1', 'audio front'},
    'back_audio_url': {'back_audio_url', 'audio mặt sau', 'audio mat sau', 'audio 2', 'audio back'},
    'front_audio_content': {'front_audio_content', 'văn bản audio mặt trước', 'front audio content'},
    'back_audio_content': {'back_audio_content', 'văn bản audio mặt sau', 'back audio content'},

    # Quiz
    'question': {'question', 'câu hỏi', 'cau hoi', 'nội dung câu hỏi', 'noidung', 'content', 'text 1', 'q'},
    'correct_answer': {'correct_answer', 'correct answer', 'đáp án đúng', 'dap an dung', 'đáp án', 'dap an', 'answer', 'ans', 'correct', 'key', 'result'},
    'explanation': {'explanation', 'giải thích', 'giai thich', 'lời giải', 'loi giai', 'explain', 'suggest', 'hint', 'gợi ý', 'goi y'},
    'option_a': {'option_a', 'option a', 'lựa chọn a', 'lua chon a', 'a', 'đáp án a', 'dap an a', 'choice a'},
    'option_b': {'option_b', 'option b', 'lựa chọn b', 'lua chon b', 'b', 'đáp án b', 'dap an b', 'choice b'},
    'option_c': {'option_c', 'option c', 'lựa chọn c', 'lua chon c', 'c', 'đáp án c', 'dap an c', 'choice c'},
    'option_d': {'option_d', 'option d', 'lựa chọn d', 'lua chon d', 'd', 'đáp án d', 'dap an d', 'choice d'},
    'pre_question_text': {'pre_question_text', 'pre question', 'đoạn văn trước', 'doan van truoc', 'context', 'bối cảnh'},
    
    # AI
    'ai_explanation': {'ai_explanation', 'ai giải thích', 'ai giai thich'},
    'ai_prompt': {'ai_prompt', 'ai prompt', 'prompt'}
}

def normalize_column_headers(columns: List[str]) -> Dict[str, str]:
    """
    Map raw column names to standardized field names based on aliases.
    Exclusively maps each standard name to at most one raw column.
    """
    mapping = {}
    used_standards = set()
    
    # Pass 1: Case-insensitive Exact Match (Priority)
    for col in columns:
        clean_col = str(col).strip().lower()
        if clean_col in COLUMN_ALIASES and clean_col not in used_standards:
            mapping[col] = clean_col
            used_standards.add(clean_col)
            
    # Pass 2: Alias Match for remaining columns
    for col in columns:
        if col in mapping:
            continue
            
        clean_col = str(col).strip().lower()
        for standard, aliases in COLUMN_ALIASES.items():
            if standard in used_standards:
                continue
            if clean_col in aliases:
                mapping[col] = standard
                used_standards.add(standard)
                break
                
    return mapping


def classify_columns(
    columns: List[str],
    standard_columns: Set[str],
    system_columns: Set[str],
    ai_columns: Set[str],
    required_columns: Optional[List[str]] = None
) -> Dict[str, List[str]]:
    """
    Classify DataFrame columns into categories.
    
    Args:
        columns: List of column names from DataFrame.
        standard_columns: Set of standard field names (front, back, etc.).
        system_columns: Set of system field names (item_id, action, etc.).
        ai_columns: Set of AI-related field names.
        required_columns: List of columns required to be present (default: ['front', 'back']).
    
    Returns:
        Dictionary with keys: standard, system, ai, custom, missing_required
        
    Examples:
        >>> columns = ['front', 'back', 'item_id', 'my_custom_field']
        >>> classify_columns(columns, {'front', 'back'}, {'item_id'}, {'ai_explanation'})
        {'standard': ['back', 'front'], 'custom': ['my_custom_field'], ...}
    """
    if required_columns is None:
        required_columns = ['front', 'back']
        
    columns_set = set(columns)
    all_known = standard_columns | system_columns | ai_columns
    
    return {
        'standard': sorted([c for c in columns if c in standard_columns]),
        'system': sorted([c for c in columns if c in system_columns]),
        'ai': sorted([c for c in columns if c in ai_columns]),
        'custom': sorted([c for c in columns if c not in all_known]),
        'missing_required': [c for c in required_columns if c not in columns_set],
        'all': sorted(list(columns))
    }


def normalize_action(
    raw_action: Optional[str],
    has_item_id: bool
) -> str:
    """
    Normalize action string to standard values.
    
    Args:
        raw_action: Raw action value from Excel (can be None or various aliases).
        has_item_id: Whether the row has an item_id (existing item).
    
    Returns:
        Normalized action: 'create', 'update', 'delete', or 'skip'
        
    Logic:
        - If action matches delete/skip aliases -> return that action
        - If 'create' but has_item_id -> return 'update'
        - If 'update' but no item_id -> return 'create'
        - Default: 'update' if has_item_id else 'create'
    """
    value = (raw_action or '').strip().lower()
    
    if value:
        for normalized, alias_values in ACTION_ALIASES.items():
            if value in alias_values:
                # Smart conversion based on item_id presence
                if normalized == 'create' and has_item_id:
                    return 'update'
                if normalized == 'update' and not has_item_id:
                    return 'create'
                return normalized
    
    # Default based on item_id presence
    return 'update' if has_item_id else 'create'


def normalize_media_path(
    url: Optional[str],
    base_folder: Optional[str] = None
) -> Optional[str]:
    """
    Normalize a media URL/path for storage.
    
    Args:
        url: Raw URL or relative path.
        base_folder: Base folder to prepend for relative paths.
    
    Returns:
        Normalized path string, or None/empty if input is empty.
        
    Logic:
        - None/empty -> None
        - Absolute URLs (http://, https://) -> return as-is
        - Relative paths -> prepend base_folder if provided
    """
    if url is None:
        return None
    
    normalized = str(url).strip()
    if not normalized:
        return ''
    
    # Keep absolute URLs unchanged
    if normalized.startswith(('http://', 'https://')):
        return normalized
    
    # For relative paths, prepend base folder
    if base_folder:
        # Ensure base_folder ends without slash, path starts without slash
        base = base_folder.rstrip('/')
        path = normalized.lstrip('/')
        return f"{base}/{path}"
    
    return normalized


def get_cell_value(
    row_data: Dict[str, Any],
    column_name: str,
    columns: List[str]
) -> Optional[str]:
    """
    Safely get a cell value from row data.
    
    Args:
        row_data: Dictionary or pandas Series representing a row.
        column_name: Name of the column to get.
        columns: List of available columns.
    
    Returns:
        Stripped string value, or None if column doesn't exist or value is NaN.
    """
    import pandas as pd
    
    if column_name not in columns:
        return None
    
    value = row_data.get(column_name) if isinstance(row_data, dict) else row_data[column_name]
    
    if pd.isna(value):
        return None
    
    return str(value).strip()


def build_content_dict(
    row_data: Dict[str, Any],
    columns: List[str],
    standard_columns: Set[str],
    url_fields: Set[str],
    image_folder: str = 'images',
    audio_folder: str = 'audio',
    exclude_fields: Set[str] = None
) -> Dict[str, Any]:
    """
    Build a content dictionary from a row of data.
    
    Args:
        row_data: Row data (dict or pandas Series).
        columns: Available column names.
        standard_columns: Set of standard field names to include.
        url_fields: Set of fields that contain URLs/paths.
        image_folder: Base folder for image fields.
        audio_folder: Base folder for audio fields.
        exclude_fields: Fields to skip (e.g., already handled).
    
    Returns:
        Content dictionary with normalized values.
    """
    exclude = exclude_fields or set()
    content = {}
    
    for field in standard_columns:
        if field in exclude:
            continue
        
        value = get_cell_value(row_data, field, columns)
        if not value:
            continue
        
        # Normalize URL fields
        if field in url_fields:
            if field in {'front_img', 'back_img'}:
                value = normalize_media_path(value, image_folder)
            else:
                value = normalize_media_path(value, audio_folder)
        
        content[field] = value
    
    return content


def build_custom_data_dict(
    row_data: Dict[str, Any],
    columns: List[str],
    custom_columns: List[str]
) -> Optional[Dict[str, Any]]:
    """
    Build a custom_data dictionary from custom columns.
    
    Args:
        row_data: Row data.
        columns: Available column names.
        custom_columns: List of custom column names.
    
    Returns:
        Custom data dict, or None if empty.
    """
    custom_data = {}
    
    for col in custom_columns:
        value = get_cell_value(row_data, col, columns)
        if value:
            custom_data[col] = value
    
    return custom_data if custom_data else None


def parse_column_pairs(pairs_string: str) -> List[Dict[str, str]]:
    """
    Parse column pair configuration string.
    
    Format: "question_col:answer_col | question_col2:answer_col2"
    
    Args:
        pairs_string: Raw string with pipe-separated pairs.
    
    Returns:
        List of dicts with 'q' and 'a' keys.
        
    Examples:
        >>> parse_column_pairs("front:back | term:definition")
        [{'q': 'front', 'a': 'back'}, {'q': 'term', 'a': 'definition'}]
    """
    if not pairs_string:
        return []
    
    pairs_list = []
    raw_pairs = str(pairs_string).split('|')
    
    for raw_pair in raw_pairs:
        parts = raw_pair.split(':')
        if len(parts) == 2:
            q_col = parts[0].strip()
            a_col = parts[1].strip()
            if q_col and a_col:
                pairs_list.append({'q': q_col, 'a': a_col})
    
    return pairs_list
