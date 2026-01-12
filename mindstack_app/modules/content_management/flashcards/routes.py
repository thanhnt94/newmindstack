# File: newmindstack/mindstack_app/modules/content_management/flashcards/routes.py
# Phiên bản: 4.9
# MỤC ĐÍCH: Hỗ trợ sắp xếp lại thứ tự thẻ (flashcard) trong một bộ bằng trường order_in_container.
# ĐÃ SỬA: Sửa đổi route list_flashcard_items để sắp xếp theo order_in_container.
# ĐÃ SỬA: Bổ sung logic vào add_flashcard_item để chèn thẻ vào vị trí cụ thể.
# ĐÃ SỬA: Bổ sung logic vào edit_flashcard_item để thay đổi vị trí thẻ và cập nhật lại thứ tự các thẻ khác.

from typing import Optional

from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    url_for,
    flash,
    abort,
    jsonify,
    current_app,
    send_file,
)
from mindstack_app.utils.template_helpers import render_dynamic_template
from flask_login import login_required, current_user
from sqlalchemy import or_, func
from sqlalchemy.orm.attributes import flag_modified
from ..forms import FlashcardSetForm, FlashcardItemForm
from ....models import db, LearningContainer, LearningItem, ContainerContributor, User
from mindstack_app.utils.media_paths import (
    normalize_media_folder,
    normalize_media_value_for_storage,
    build_relative_media_path,
)
from mindstack_app.utils.db_session import safe_commit
from mindstack_app.utils.excel import extract_info_sheet_mapping, format_info_warnings
from ....config import Config
from ....services.config_service import get_runtime_config
import pandas as pd
import tempfile
import os
import asyncio
import zipfile
import shutil
import re
import io
import json
from mindstack_app.utils.pagination import get_pagination_data
from mindstack_app.utils.search import apply_search_filter
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.datavalidation import DataValidation
# THÊM MỚI: Import AudioService
from ...learning.sub_modules.flashcard.services import AudioService, ImageService
from .services import FlashcardExcelService
from ....core.error_handlers import error_response, success_response

flashcards_bp = Blueprint('content_management_flashcards', __name__,
                            template_folder='templates') # Đã cập nhật đường dẫn template

# Khởi tạo service
audio_service = AudioService()
image_service = ImageService()


def _ensure_container_media_folder(container: LearningContainer, media_type: str) -> str:
    """Trả về thư mục đã cấu hình cho loại media, tạo thư mục mặc định nếu thiếu."""

    attr_name = f"media_{media_type}_folder"
    existing = getattr(container, attr_name, None)
    if existing:
        return existing

    type_slug = (container.container_type or "").lower()
    if type_slug.endswith("_set"):
        type_slug = type_slug[:-4]
    type_slug = type_slug.replace("_", "-") or "container"

    default_folder = f"{type_slug}/{container.container_id}/{media_type}"
    setattr(container, attr_name, default_folder)
    db.session.add(container)
    try:
        safe_commit(db.session)
    except Exception:  # pragma: no cover - propagate commit failure
        db.session.rollback()
        raise

    return default_folder


def _extract_media_folders(settings_payload) -> dict[str, str]:
    """Trả về ánh xạ thư mục media đã được chuẩn hóa từ một payload cấu hình chung."""

    result: dict[str, str] = {}
    if not isinstance(settings_payload, dict):
        return result

    media_settings = settings_payload.get('media_folders')
    if isinstance(media_settings, dict):
        for media_type in ('image', 'audio'):
            normalized = normalize_media_folder(media_settings.get(media_type))
            if normalized:
                result[media_type] = normalized
    else:
        for media_type in ('image', 'audio'):
            fallback_key = f"{media_type}_base_folder"
            normalized = normalize_media_folder(settings_payload.get(fallback_key))
            if normalized:
                result[media_type] = normalized

    return result


CAPABILITY_FLAGS = (
    'supports_pronunciation',
    'supports_writing',
    'supports_quiz',
    'supports_essay',
    'supports_listening',
    'supports_speaking',
    'supports_flashcard',
    'supports_matching',
    'supports_speed',
)

MEDIA_URL_FIELDS = {'front_img', 'back_img', 'front_audio_url', 'back_audio_url'}

# [REFACTORED] Minimal standard columns matching import logic + Action
# Legacy 'supports_*' and 'ai_prompt' removed from defaults.
FLASHCARD_DATA_COLUMNS = [
    'item_id',
    'order_in_container',
    'front',
    'back',
    'front_audio_content',
    'back_audio_content',
    'front_audio_url',
    'back_audio_url',
    'front_img',
    'back_img',
    'ai_explanation',
    'action',
]

FLASHCARD_INFO_KEYS = [
    'title',
    'description',
    'cover_image',
    'tags',
    'is_public',
    *CAPABILITY_FLAGS,
    'image_base_folder',
    'audio_base_folder',
    'ai_prompt',
    # [NEW] Dynamic keys for mode-specific column mappings (Multiple Pairs)
    'mcq_pairs',
    'typing_pairs',
    'matching_pairs',
    'listening_pairs',
    'speaking_pairs',
]

ACTION_OPTIONS = ['None', 'Update', 'Create', 'Delete', 'Skip']


def _apply_action_dropdown(worksheet, data_columns):
    try:
        action_index = data_columns.index('action') + 1
    except ValueError:
        return

    action_letter = get_column_letter(action_index)
    validation = DataValidation(
        type='list',
        formula1=f'"{",".join(ACTION_OPTIONS)}"',
        allow_blank=True,
        showDropDown=False,
    )
    validation.errorTitle = 'Hành động không hợp lệ'
    validation.error = 'Vui lòng chọn một hành động hợp lệ hoặc để None nếu không thay đổi.'
    validation.promptTitle = 'Chọn hành động'
    validation.prompt = 'Chọn hành động bạn muốn áp dụng cho dòng này.'
    worksheet.add_data_validation(validation)
    validation.add(f"{action_letter}2:{action_letter}1048576")


def _create_flashcard_excel(info_rows, data_rows, columns=None, *, output_path: Optional[str] = None):
    """
    Tạo file Excel xuất khẩu.
    :param columns: Danh sách tên cột (chuẩn + custom). Nếu None sẽ dùng FLASHCARD_DATA_COLUMNS mặc định.
    """
    info_df = pd.DataFrame(info_rows, columns=['Key', 'Value'])
    if not info_df.empty:
        info_df['Value'] = info_df['Value'].apply(lambda value: '' if value is None else str(value))
    else:
        info_df = pd.DataFrame(columns=['Key', 'Value'])

    # Use provided columns or fallback to default
    final_columns = columns if columns else FLASHCARD_DATA_COLUMNS
    
    data_df = pd.DataFrame(data_rows, columns=final_columns)
    if data_df.empty:
        data_df = pd.DataFrame(columns=final_columns)
    else:
        data_df = data_df.fillna('')

    if 'action' in data_df.columns:
        data_df['action'] = data_df['action'].replace({None: 'None', '': 'None'})
    else:
        data_df['action'] = 'None'

    target = output_path or io.BytesIO()
    with pd.ExcelWriter(target, engine='openpyxl') as writer:
        info_df.to_excel(writer, sheet_name='Info', index=False)
        data_df.to_excel(writer, sheet_name='Data', index=False)
        data_sheet = writer.sheets.get('Data')
        if data_sheet is not None:
            _apply_action_dropdown(data_sheet, final_columns)

    if output_path:
        return output_path

    target.seek(0)
    return target


def _apply_is_public_restrictions(form):
    """Vô hiệu hóa chuyển đổi công khai cho người dùng miễn phí và đảm bảo giá trị là False."""
    if hasattr(form, 'is_public') and current_user.user_role == 'free':
        form.is_public.data = False
        existing_render_kw = dict(form.is_public.render_kw or {})
        existing_render_kw['disabled'] = True
        form.is_public.render_kw = existing_render_kw

def _normalize_capabilities(raw_capabilities):
    """Chuyển đổi các biểu diễn khác nhau của cờ khả năng thành một tập hợp chuỗi."""
    capabilities = set()
    if isinstance(raw_capabilities, (list, tuple, set)):
        for value in raw_capabilities:
            if isinstance(value, str) and value:
                capabilities.add(value)
    elif isinstance(raw_capabilities, dict):
        for key, enabled in raw_capabilities.items():
            if enabled and isinstance(key, str) and key:
                capabilities.add(key)
    elif isinstance(raw_capabilities, str) and raw_capabilities:
        capabilities.add(raw_capabilities)
    return capabilities


def _get_container_capabilities(container):
    """Trả về tập hợp các cờ khả năng học tập được kích hoạt trên một bộ flashcard."""
    if not container:
        return set()
    if hasattr(container, 'capability_flags'):
        return set(container.capability_flags())
    settings_payload = container.ai_settings if hasattr(container, 'ai_settings') else None
    if isinstance(settings_payload, dict):
        return _normalize_capabilities(settings_payload.get('capabilities'))
    return set()


def _get_media_folders_from_container(container) -> dict[str, str]:
    if not container:
        return {}
    folders = getattr(container, 'media_folders', {}) or {}
    if folders:
        return dict(folders)
    return {}


def _get_media_folder_for_field(field_name: str, media_folders: dict[str, str]):
    if field_name in {'front_img', 'back_img'}:
        return media_folders.get('image')
    if field_name in {'front_audio_url', 'back_audio_url'}:
        return media_folders.get('audio')
    return None


def _build_ai_settings_from_form(form, existing_settings=None):
    """Tạo một ánh xạ cấu hình AI đã được chuẩn hóa dựa trên đầu vào form."""

    existing_payload = {}
    if isinstance(existing_settings, dict):
        extra_payload = existing_settings.get('extra')
        if isinstance(extra_payload, dict):
            existing_payload.update(extra_payload)

    ai_prompt_value = (getattr(form.ai_prompt, 'data', '') or '').strip()
    if ai_prompt_value:
        existing_payload['custom_prompt'] = ai_prompt_value
    else:
        existing_payload.pop('custom_prompt', None)

    capability_flags = [
        flag_name
        for flag_name in CAPABILITY_FLAGS
        if getattr(getattr(form, flag_name, None), 'data', False)
    ]
    if capability_flags:
        existing_payload['capabilities'] = capability_flags
    else:
        existing_payload.pop('capabilities', None)

    media_folders = {}
    image_folder_value = normalize_media_folder(getattr(getattr(form, 'image_base_folder', None), 'data', None))
    audio_folder_value = normalize_media_folder(getattr(getattr(form, 'audio_base_folder', None), 'data', None))
    if image_folder_value:
        media_folders['image'] = image_folder_value
    if audio_folder_value:
        media_folders['audio'] = audio_folder_value
    if media_folders:
        existing_payload['media_folders'] = media_folders
    else:
        existing_payload.pop('media_folders', None)

    return existing_payload or None

def _process_relative_url(url, media_folder=None):
    """Chuẩn hóa dữ liệu URL/đường dẫn trước khi lưu vào DB."""
    if url is None:
        return None

    normalized = str(url).strip()
    if not normalized:
        return ''

    if normalized.startswith(('http://', 'https://')):
        return normalized

    return normalize_media_value_for_storage(normalized, media_folder)


def _build_static_media_url(value, media_folder=None):
    relative_path = build_relative_media_path(value, media_folder)
    if not relative_path:
        return None

    if relative_path.startswith(('http://', 'https://')):
        return relative_path

    return url_for('static', filename=relative_path)


def _get_static_image_url(url, media_folder=None):
    return _build_static_media_url(url, media_folder)


def _get_static_audio_url(url, media_folder=None):
    return _build_static_media_url(url, media_folder)


def _slugify_filename(value: str) -> str:
    """Chuyển tiêu đề thành chuỗi thân thiện để đặt tên file zip."""
    value = (value or '').strip().lower()
    if not value:
        return 'flashcard-set'
    value = re.sub(r'[^a-z0-9\-]+', '-', value)
    value = re.sub(r'-{2,}', '-', value).strip('-')
    return value or 'flashcard-set'


def _resolve_local_media_path(path_value: str, *, media_folder: Optional[str] = None):
    """Trả về đường dẫn tuyệt đối tới file media nếu thuộc thư mục uploads/static."""
    if not path_value:
        return None

    normalized = str(path_value).strip()
    if not normalized:
        return None

    if normalized.startswith(('http://', 'https://')):
        return None

    normalized = normalized.lstrip('/')
    if normalized.startswith('uploads/'):
        normalized = normalized[len('uploads/'):]

    # Nếu đường dẫn bắt đầu bằng /static, thử map tới thư mục static
    base_static = os.path.join(current_app.root_path, 'static')
    candidates = []
    relative_candidates = [normalized]
    folder_normalized = normalize_media_folder(media_folder)
    if folder_normalized:
        if '/' not in normalized:
            relative_candidates.insert(0, f"{folder_normalized}/{normalized}")
        else:
            relative_candidates.insert(0, normalized)

    upload_folder = get_runtime_config('UPLOAD_FOLDER', Config.UPLOAD_FOLDER)
    for rel_path in relative_candidates:
        if upload_folder:
            candidates.append(os.path.join(upload_folder, rel_path))
        candidates.append(os.path.join(base_static, rel_path))

    for candidate in candidates:
        if candidate and os.path.isfile(candidate):
            return candidate

    return None


def _copy_media_into_package(
    original_path: str,
    media_dir: Optional[str],
    existing_map: dict,
    media_subdir: Optional[str] = None,
    media_folder: Optional[str] = None,
    export_mode: str = 'zip',
) -> str:
    """Chuẩn hoá đường dẫn media cho xuất Excel/ZIP và sao chép file nếu cần."""
    if original_path in (None, ''):
        return original_path

    if export_mode == 'excel':
        return original_path

    normalized = str(original_path).strip()
    if not normalized:
        return ''

    if normalized.startswith(('http://', 'https://')):
        return normalized

    local_path = _resolve_local_media_path(normalized, media_folder=media_folder)
    if not local_path and os.path.isabs(normalized) and os.path.isfile(normalized):
        local_path = normalized

    display_value = normalized
    if os.path.isabs(normalized):
        display_value = os.path.basename(normalized)

    if not local_path:
        return display_value

    cache_key = (
        local_path,
        media_folder,
        media_subdir,
        display_value,
    )
    if cache_key in existing_map:
        return display_value

    if not media_dir:
        existing_map[cache_key] = True
        return display_value

    folder_normalized = normalize_media_folder(media_folder)

    sanitized = normalized.replace('\\', '/').lstrip('/')
    segments = [segment for segment in sanitized.split('/') if segment and segment not in {'.', '..'}]

    while segments and segments[0].lower() == 'uploads':
        segments.pop(0)

    if folder_normalized:
        folder_segments = [seg for seg in folder_normalized.split('/') if seg]
        if segments[: len(folder_segments)] == folder_segments:
            segments = segments[len(folder_segments) :]

    if os.path.isabs(normalized):
        segments = [os.path.basename(local_path)]

    if not segments:
        segments = [os.path.basename(local_path)]

    base_segments: list[str] = []
    if folder_normalized:
        base_segments.extend(folder_normalized.split('/'))
    elif media_subdir:
        base_segments.append(media_subdir)

    destination_parts = base_segments + segments
    destination_full = os.path.join(media_dir, *destination_parts)
    destination_relative = '/'.join(['uploads'] + destination_parts)

    os.makedirs(os.path.dirname(destination_full), exist_ok=True)
    if not os.path.exists(destination_full):
        shutil.copy2(local_path, destination_full)

    existing_map[cache_key] = destination_relative
    return display_value


def _build_flashcard_export_payload(
    flashcard_set,
    items,
    *,
    export_mode: str,
    media_dir: Optional[str],
    media_cache: Optional[dict],
    image_folder: Optional[str],
    audio_folder: Optional[str],
):
    media_cache = media_cache or {}
    container_capabilities = _get_container_capabilities(flashcard_set)

    ai_settings_payload = flashcard_set.ai_settings if hasattr(flashcard_set, 'ai_settings') else None
    ai_prompt_value = getattr(flashcard_set, 'ai_prompt', None)
    if not ai_prompt_value and isinstance(ai_settings_payload, dict):
        ai_prompt_value = ai_settings_payload.get('custom_prompt')

    info_mapping = {
        'title': flashcard_set.title or '',
        'description': flashcard_set.description or '',
        'cover_image': flashcard_set.cover_image or '',
        'tags': flashcard_set.tags or '',
        'is_public': 'True' if flashcard_set.is_public else 'False',
        'image_base_folder': image_folder or '',
        'audio_base_folder': audio_folder or '',
        'ai_prompt': ai_prompt_value or '',
    }

    # [NEW] Export Column Mappings from Settings (Multiple Pairs)
    settings = flashcard_set.settings or {}
    check_modes = ['mcq', 'typing', 'matching', 'listening', 'speaking']
    for mode in check_modes:
        # DB key checks
        mode_config = settings.get(mode)

        if isinstance(mode_config, dict):
            # Prefer 'pairs' list, create string representation
            pairs = mode_config.get('pairs') or mode_config.get('custom_pairs') # Also check custom_pairs
            if pairs and isinstance(pairs, list):
                # Format: "q1:a1 | q2:a2"
                pair_strings = [f"{p.get('q', '')}:{p.get('a', '')}" for p in pairs if p.get('q') and p.get('a')]
                if pair_strings:
                    info_mapping[f"{mode}_pairs"] = ' | '.join(pair_strings)
            elif mode_config.get('question_column') and mode_config.get('answer_column'):
                 # Fallback for old single pair format
                 info_mapping[f"{mode}_pairs"] = f"{mode_config['question_column']}:{mode_config['answer_column']}"

    for capability_key in CAPABILITY_FLAGS:
        info_mapping[capability_key] = 'True' if capability_key in container_capabilities else 'False'

    info_rows = [
        {'Key': key, 'Value': info_mapping.get(key, '')}
        for key in FLASHCARD_INFO_KEYS
    ]

    # [NEW] Detect all unique custom keys across all items
    custom_keys = set()
    for item in items:
        if item.custom_data:
            custom_keys.update(item.custom_data.keys())
    sorted_custom_keys = sorted(list(custom_keys))

    # Define final columns order: Base | Custom | Action
    # Remove 'action' from base temporarily to place it at the end
    base_cols_no_action = [col for col in FLASHCARD_DATA_COLUMNS if col != 'action']
    final_columns = base_cols_no_action + sorted_custom_keys + ['action']

    data_rows = []
    for item in items:
        content = item.content or {}
        # Initialize row with all final columns empty
        row = {column: '' for column in final_columns}
        
        # --- Populate Standard Columns ---
        row['item_id'] = item.item_id
        row['order_in_container'] = item.order_in_container if item.order_in_container is not None else ''
        row['front'] = content.get('front') or ''
        row['back'] = content.get('back') or ''
        row['front_audio_content'] = content.get('front_audio_content') or ''
        row['back_audio_content'] = content.get('back_audio_content') or ''
        
        # --- Media Processing ---
        row['front_audio_url'] = _copy_media_into_package(
            content.get('front_audio_url'),
            media_dir,
            media_cache,
            media_subdir='audio',
            media_folder=audio_folder,
            export_mode=export_mode,
        ) or ''
        row['back_audio_url'] = _copy_media_into_package(
            content.get('back_audio_url'),
            media_dir,
            media_cache,
            media_subdir='audio',
            media_folder=audio_folder,
            export_mode=export_mode,
        ) or ''
        row['front_img'] = _copy_media_into_package(
            content.get('front_img'),
            media_dir,
            media_cache,
            media_subdir='images',
            media_folder=image_folder,
            export_mode=export_mode,
        ) or ''
        row['back_img'] = _copy_media_into_package(
            content.get('back_img'),
            media_dir,
            media_cache,
            media_subdir='images',
            media_folder=image_folder,
            export_mode=export_mode,
        ) or ''
        
        row['ai_explanation'] = item.ai_explanation or content.get('ai_explanation') or ''
        
        # --- [MOVED] Legacy Columns Removed ---
        # supports_* columns are no longer exported here.
        # ai_prompt is also skipped for items.

        # --- [NEW] Populate Custom Data ---
        custom_data = item.custom_data or {}
        for key in sorted_custom_keys:
            row[key] = custom_data.get(key, '')

        row['action'] = 'None'
        data_rows.append(row)

    return info_rows, data_rows, final_columns


def _has_editor_access(container_id):
    if current_user.user_role == User.ROLE_FREE:
        return False
    return ContainerContributor.query.filter_by(
        container_id=container_id,
        user_id=current_user.user_id,
        permission_level='editor'
    ).first() is not None


def _get_editable_flashcard_sets_query(*, exclude_id: Optional[int] = None):
    base_query = LearningContainer.query.filter_by(container_type='FLASHCARD_SET')

    if current_user.user_role == User.ROLE_ADMIN:
        query = base_query
    elif current_user.user_role == User.ROLE_FREE:
        query = base_query.filter_by(creator_user_id=current_user.user_id)
    else:
        contributor_ids = (
            ContainerContributor.query
            .filter_by(user_id=current_user.user_id, permission_level='editor')
            .with_entities(ContainerContributor.container_id)
        )
        query = base_query.filter(
            or_(
                LearningContainer.creator_user_id == current_user.user_id,
                LearningContainer.container_id.in_(contributor_ids)
            )
        )

    if exclude_id:
        query = query.filter(LearningContainer.container_id != exclude_id)

    return query


# [REFACTORED] Logic moved to FlashcardExcelService.
# Old code commented out below.


@flashcards_bp.route('/flashcards/process_excel_info', methods=['POST'])
@login_required
def process_excel_info():
    """
    Mô tả: Xử lý file Excel được tải lên để trích xuất thông tin từ sheet 'Info'.

    Hàm này đọc một file Excel, tìm kiếm sheet có tên 'Info',
    và trích xuất dữ liệu từ đó, trả về dưới dạng JSON.
    """
    if 'excel_file' not in request.files:
        return error_response('Không tìm thấy file.', 'BAD_REQUEST', 400)
    file = request.files['excel_file']
    if file.filename == '':
        return error_response('Chưa chọn file nào.', 'BAD_REQUEST', 400)
    if file and file.filename.endswith('.xlsx'):
        temp_filepath = None
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx') as tmp_file:
                file.save(tmp_file.name)
                temp_filepath = tmp_file.name

            info_data, info_warnings = extract_info_sheet_mapping(temp_filepath)
            
            # [NEW] Check for 'Data' sheet column structure
            column_analysis = FlashcardExcelService.analyze_column_structure(temp_filepath)
            
            if not info_data and info_warnings:
                message = format_info_warnings(info_warnings)
                return error_response(message, 'BAD_REQUEST', 400)

            # Normalize info_data keys and clean values
            normalized_data = {}
            for k, v in info_data.items():
                # Clean Key
                clean_key = str(k).strip().lower().replace(' ', '_')
                
                # Map Legacy Keys
                if clean_key == 'quiz_pairs':
                    clean_key = 'mcq_pairs'
                
                # Clean Value
                if isinstance(v, str):
                    clean_val = v.replace('_x000D_', '\n')
                else:
                    clean_val = v
                
                normalized_data[clean_key] = clean_val

            message = 'Đã đọc thông tin từ file Excel.'
            if info_warnings:
                message += ' ' + format_info_warnings(info_warnings)
                
            return success_response(message=message, data={
                'data': normalized_data, 
                'column_analysis': column_analysis
            })
        except Exception as e:
            # Xử lý các lỗi khác khi đọc file Excel
            current_app.logger.error(f"Lỗi khi xử lý sheet Info (Flashcard): {e}")
            return error_response(f'Lỗi đọc file Excel: {e}', 'SERVER_ERROR', 500)
        finally:
            # Đảm bảo xóa file tạm thời
            if temp_filepath and os.path.exists(temp_filepath):
                os.remove(temp_filepath)
    # Trả về lỗi nếu file không hợp lệ
    return error_response('File không hợp lệ. Vui lòng chọn file .xlsx', 'BAD_REQUEST', 400)

@flashcards_bp.route('/flashcards')
@login_required
def list_flashcard_sets():
    """
    Mô tả: Hiển thị danh sách các bộ Flashcard.

    Hàm này truy xuất các bộ Flashcard mà người dùng hiện tại đã tạo hoặc đóng góp,
    áp dụng bộ lọc tìm kiếm và phân trang, sau đó hiển thị chúng.
    """
    page = request.args.get('page', 1, type=int)
    search_query = request.args.get('q', '', type=str)
    search_field = request.args.get('search_field', 'all', type=str) # Lấy trường tìm kiếm từ request

    # Truy vấn cơ sở để lấy các bộ Flashcard
    base_query = LearningContainer.query.filter_by(container_type='FLASHCARD_SET')

    # Lọc theo quyền sở hữu/đóng góp nếu không phải admin
    if current_user.user_role == User.ROLE_ADMIN:
        pass
    elif current_user.user_role == User.ROLE_FREE:
        base_query = base_query.filter_by(creator_user_id=current_user.user_id)
    else:
        user_id = current_user.user_id
        created_sets_query = base_query.filter_by(creator_user_id=user_id)
        contributed_sets_query = base_query.join(ContainerContributor).filter(
            ContainerContributor.user_id == user_id,
            ContainerContributor.permission_level == 'editor'
        )
        base_query = created_sets_query.union(contributed_sets_query)

    # Ánh xạ các trường có thể tìm kiếm
    search_field_map = {
        'title': LearningContainer.title,
        'description': LearningContainer.description,
        'tags': LearningContainer.tags
    }
    
    # Áp dụng bộ lọc tìm kiếm
    base_query = apply_search_filter(base_query, search_query, search_field_map, search_field)

    # Lấy dữ liệu phân trang
    pagination = get_pagination_data(base_query.order_by(LearningContainer.created_at.desc()), page)
    flashcard_sets = pagination.items

    # Đếm số lượng thẻ trong mỗi bộ và chuẩn bị thông tin hiển thị bổ sung
    for set_item in flashcard_sets:
        set_item.item_count = db.session.query(LearningItem).filter_by(
            container_id=set_item.container_id,
            item_type='FLASHCARD'
        ).count()

        # Thông tin người tạo
        creator = getattr(set_item, 'creator', None)
        if creator:
            set_item.creator_display_name = creator.username
        else:
            set_item.creator_display_name = "Không xác định"

        # Danh sách những người có quyền chỉnh sửa
        editor_labels = []
        seen_user_ids = set()

        if creator:
            seen_user_ids.add(creator.user_id)
            editor_labels.append(creator.username)

        for contributor in getattr(set_item, 'contributors', []) or []:
            if contributor.permission_level != 'editor':
                continue
            contributor_user = getattr(contributor, 'user', None)
            if not contributor_user or contributor_user.user_id in seen_user_ids:
                continue

            editor_labels.append(contributor_user.username)
            seen_user_ids.add(contributor_user.user_id)

        if not editor_labels:
            editor_labels.append("Chưa có")

        set_item.editor_display_names = editor_labels

    # Các biến để truyền vào template
    template_vars = {
        'flashcard_sets': flashcard_sets, 
        'pagination': pagination, 
        'search_query': search_query,
        'search_field': search_field,
        'search_field_map': search_field_map # Truyền map để tạo dropdown cho template
    }

    # Trả về template phù hợp (ajax hoặc đầy đủ)
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return render_dynamic_template('pages/content_management/flashcards/sets/_flashcard_sets_list.html', **template_vars)
    else:
        return render_dynamic_template('pages/content_management/flashcards/sets/flashcard_sets.html', **template_vars)


@flashcards_bp.route('/flashcards/<int:set_id>/export', methods=['GET'])
@login_required
def export_flashcard_set(set_id):
    """Xuất bộ flashcard thành gói zip gồm Excel và media."""
    flashcard_set = LearningContainer.query.get_or_404(set_id)

    if current_user.user_role not in {User.ROLE_ADMIN} and flashcard_set.creator_user_id != current_user.user_id:
        if current_user.user_role == User.ROLE_FREE or not _has_editor_access(set_id):
            abort(403)

    items = (
        LearningItem.query.filter_by(container_id=set_id, item_type='FLASHCARD')
        .order_by(LearningItem.order_in_container, LearningItem.item_id)
        .all()
    )

    media_folders = _get_media_folders_from_container(flashcard_set)
    image_folder = media_folders.get('image')
    audio_folder = media_folders.get('audio')

    with tempfile.TemporaryDirectory() as tmp_dir:
        media_dir = os.path.join(tmp_dir, 'uploads')
        os.makedirs(media_dir, exist_ok=True)
        media_cache = {}

        info_rows, data_rows, columns = _build_flashcard_export_payload(
            flashcard_set,
            items,
            export_mode='zip',
            media_dir=media_dir,
            media_cache=media_cache,
            image_folder=image_folder,
            audio_folder=audio_folder,
        )

        excel_path = os.path.join(tmp_dir, 'flashcards.xlsx')
        _create_flashcard_excel(info_rows, data_rows, columns=columns, output_path=excel_path)

        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zipf:
            zipf.write(excel_path, arcname='flashcards.xlsx')
            if os.path.isdir(media_dir):
                for root_dir, _, files in os.walk(media_dir):
                    for filename in files:
                        file_path = os.path.join(root_dir, filename)
                        arcname = os.path.relpath(file_path, tmp_dir)
                        zipf.write(file_path, arcname)

        zip_buffer.seek(0)
        download_name = f"{_slugify_filename(flashcard_set.title)}.zip"
        return send_file(zip_buffer, as_attachment=True, download_name=download_name, mimetype='application/zip')


@flashcards_bp.route('/flashcards/<int:set_id>/export-excel', methods=['GET'])
@login_required
def export_flashcard_set_excel(set_id):
    """Xuất bộ flashcard ra file Excel duy nhất, giữ nguyên đường dẫn media."""
    flashcard_set = LearningContainer.query.get_or_404(set_id)

    if current_user.user_role not in {User.ROLE_ADMIN} and flashcard_set.creator_user_id != current_user.user_id:
        if current_user.user_role == User.ROLE_FREE or not _has_editor_access(set_id):
            abort(403)

    items = (
        LearningItem.query.filter_by(container_id=set_id, item_type='FLASHCARD')
        .order_by(LearningItem.order_in_container, LearningItem.item_id)
        .all()
    )

    media_folders = _get_media_folders_from_container(flashcard_set)
    image_folder = media_folders.get('image')
    audio_folder = media_folders.get('audio')

    info_rows, data_rows = _build_flashcard_export_payload(
        flashcard_set,
        items,
        export_mode='excel',
        media_dir=None,
        media_cache={},
        image_folder=image_folder,
        audio_folder=audio_folder,
    )

    excel_buffer = _create_flashcard_excel(info_rows, data_rows)
    download_name = f"{_slugify_filename(flashcard_set.title)}.xlsx"
    return send_file(
        excel_buffer,
        as_attachment=True,
        download_name=download_name,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    )


@flashcards_bp.route('/flashcards/excel-template', methods=['GET'])
@login_required
def download_flashcard_excel_template():
    """Cung cấp file Excel mẫu để quản trị viên chuẩn bị dữ liệu flashcard."""
    info_rows = [
        {'Key': 'title', 'Value': 'Tiêu đề bộ thẻ (tuỳ chọn)'},
        {'Key': 'description', 'Value': 'Mô tả ngắn gọn về bộ thẻ'},
        {'Key': 'cover_image', 'Value': 'Đường dẫn ảnh cover (URL hoặc uploads/...)'},
        {'Key': 'tags', 'Value': 'Từ khoá phân tách bằng dấu phẩy'},
        {'Key': 'is_public', 'Value': 'true/false - trạng thái công khai'},
        {'Key': 'supports_*', 'Value': 'true/false - bật từng chế độ học cho toàn bộ bộ thẻ'},
        {'Key': 'image_base_folder', 'Value': 'Thư mục ảnh trong uploads, ví dụ: flashcard/n5/images'},
        {'Key': 'audio_base_folder', 'Value': 'Thư mục audio trong uploads, ví dụ: flashcard/n5/audio'},
    ]

    data_columns = [
        'item_id',
        'order_in_container',
        'front',
        'back',
        'front_audio_content',
        'back_audio_content',
        'front_audio_url',
        'back_audio_url',
        'front_img',
        'back_img',
        'ai_explanation',
        'ai_prompt',
        'supports_pronunciation',
        'supports_writing',
        'supports_quiz',
        'supports_essay',
        'supports_listening',
        'supports_speaking',
        'action',
    ]

    sample_row = {
        'item_id': '',
        'order_in_container': 1,
        'front': 'Hello',
        'back': 'Xin chào',
        'front_audio_content': 'Hello',
        'back_audio_content': 'Xin chào',
        'front_audio_url': '',
        'back_audio_url': '',
        'front_img': '',
        'back_img': '',
        'ai_explanation': '',
        'ai_prompt': '',
        'supports_pronunciation': 'TRUE',
        'supports_writing': 'TRUE',
        'supports_quiz': 'TRUE',
        'supports_essay': 'FALSE',
        'supports_listening': 'TRUE',
        'supports_speaking': 'TRUE',
        'action': 'None',
    }

    excel_buffer = _create_flashcard_excel(info_rows, [sample_row])
    return send_file(
        excel_buffer,
        as_attachment=True,
        download_name='flashcard_template.xlsx',
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )


@flashcards_bp.route('/flashcards/<int:set_id>/manage-excel', methods=['GET', 'POST'])
@login_required
def manage_flashcard_excel(set_id):
    """Trang quản lý import/export Excel cho bộ flashcard."""
    flashcard_set = LearningContainer.query.get_or_404(set_id)

    if flashcard_set.creator_user_id != current_user.user_id:
        if current_user.user_role == User.ROLE_FREE:
            abort(403)
        if current_user.user_role != User.ROLE_ADMIN and not _has_editor_access(set_id):
            abort(403)

    if request.method == 'POST':
        uploaded_file = request.files.get('excel_file')
        if not uploaded_file or uploaded_file.filename == '':
            flash('Vui lòng chọn file Excel (.xlsx) để nhập.', 'danger')
            return redirect(url_for('content_management.content_management_flashcards.manage_flashcard_excel', set_id=set_id))
        if not uploaded_file.filename.lower().endswith('.xlsx'):
            flash('Định dạng file không hợp lệ. Vui lòng chọn file .xlsx.', 'danger')
            return redirect(url_for('content_management.content_management_flashcards.manage_flashcard_excel', set_id=set_id))

        try:
            message = FlashcardExcelService.process_import(set_id, uploaded_file)
            db.session.commit()
            flash(message, 'success')
        except Exception as exc:  # pylint: disable=broad-except
            db.session.rollback()
            flash(f'Lỗi khi xử lý: {exc}', 'danger')

        return redirect(url_for('content_management.content_management_flashcards.manage_flashcard_excel', set_id=set_id))

    export_excel_url = url_for('content_management.content_management_flashcards.export_flashcard_set_excel', set_id=set_id)
    export_zip_url = url_for('content_management.content_management_flashcards.export_flashcard_set', set_id=set_id)
    template_url = url_for('content_management.content_management_flashcards.download_flashcard_excel_template')
    item_count = LearningItem.query.filter_by(container_id=set_id, item_type='FLASHCARD').count()
    return render_dynamic_template('pages/content_management/flashcards/excel/manage_flashcard_excel.html',
        flashcard_set=flashcard_set,
        export_excel_url=export_excel_url,
        export_zip_url=export_zip_url,
        template_url=template_url,
        item_count=item_count,
    )


@flashcards_bp.route('/flashcards/add', methods=['GET', 'POST'])
@login_required
def add_flashcard_set():
    """
    Mô tả: Thêm một bộ Flashcard mới.

    Hàm này xử lý việc tạo bộ Flashcard, bao gồm cả việc nhập dữ liệu từ file Excel
    và thêm các thẻ Flashcard liên quan.
    """
    form = FlashcardSetForm()
    template_url = url_for('content_management.content_management_flashcards.download_flashcard_excel_template')
    _apply_is_public_restrictions(form)
    if form.validate_on_submit():
        flash_message = ''
        flash_category = ''
        temp_filepath = None
        try:
            ai_settings_payload = _build_ai_settings_from_form(form)
            selected_capabilities = _normalize_capabilities(
                (ai_settings_payload or {}).get('capabilities')
            )
            media_folders = _extract_media_folders(ai_settings_payload)
            image_folder = media_folders.get('image')
            audio_folder = media_folders.get('audio')
            cover_image_value = _process_relative_url(form.cover_image.data, image_folder)
            
            # Parse settings
            settings_data = None
            if form.settings.data:
                try:
                    import json
                    settings_data = json.loads(form.settings.data)
                except:
                    pass

            # Tạo bộ Flashcard mới
            new_set = LearningContainer(
                creator_user_id=current_user.user_id,
                container_type='FLASHCARD_SET',
                title=form.title.data,
                description=form.description.data,
                cover_image=cover_image_value,
                tags=form.tags.data,
                is_public=False if current_user.user_role == 'free' else form.is_public.data,
                ai_settings=ai_settings_payload,
                settings=settings_data
            )
            if media_folders:
                new_set.set_media_folders(media_folders)
            db.session.add(new_set)
            db.session.flush() # Lưu tạm thời để có container_id

            # Xử lý file Excel nếu có
            if form.excel_file.data and form.excel_file.data.filename != '':
                # Gọi Service xử lý trọn gói (bao gồm Info sheet + Data sheet)
                # Service expect 'excel_file' as a FileStorage object (or object with .save())
                # FlashcardExcelService.process_import(container_id, excel_file)
                import_summary = FlashcardExcelService.process_import(
                    container_id=new_set.container_id,
                    excel_file=form.excel_file.data
                )
                flash_message = f'Bộ thẻ mới đã được tạo. {import_summary}'
                flash_category = 'success'
            else:
                flash_message = 'Bộ thẻ mới đã được tạo thành công!'
                flash_category = 'success'
            db.session.commit() # Lưu các thay đổi vào DB
        except Exception as e:
            db.session.rollback() # Hoàn tác nếu có lỗi
            flash_message = f'Lỗi khi xử lý: {str(e)}'
            flash_category = 'danger'
        finally:
            # Xóa file tạm thời
            if temp_filepath and os.path.exists(temp_filepath):
                os.remove(temp_filepath)
        
        # Trả về phản hồi JSON hoặc chuyển hướng tùy theo yêu cầu
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return success_response(message=flash_message)
        else:
            flash(flash_message, flash_category)
            return redirect(url_for('content_management.content_dashboard', tab='flashcards'))
    
    # Xử lý lỗi form validation cho AJAX
    if (request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.args.get('is_modal') == 'true') and request.method == 'POST':
        return error_response('Dữ liệu không hợp lệ', 'VALIDATION_ERROR', 400, details=form.errors)
    
    # Render template cho modal hoặc trang đầy đủ
    if request.method == 'GET' and request.args.get('is_modal') == 'true':
        return render_dynamic_template('pages/content_management/flashcards/sets/_add_edit_flashcard_set_bare.html', form=form, title='Thêm Bộ thẻ ghi nhớ', template_url=template_url)
    return render_dynamic_template('pages/content_management/flashcards/sets/add_edit_flashcard_set.html', form=form, title='Thêm Bộ thẻ ghi nhớ', template_url=template_url)

@flashcards_bp.route('/flashcards/edit/<int:set_id>', methods=['GET', 'POST'])
@login_required
def edit_flashcard_set(set_id):
    """
    Mô tả: Chỉnh sửa một bộ Flashcard hiện có.

    Hàm này cho phép chỉnh sửa thông tin của bộ Flashcard và cập nhật/thêm các thẻ
    từ file Excel.
    """
    flashcard_set = LearningContainer.query.get_or_404(set_id)
    # Kiểm tra quyền chỉnh sửa
    if flashcard_set.creator_user_id != current_user.user_id:
        if current_user.user_role == User.ROLE_FREE:
            abort(403)
        if current_user.user_role != User.ROLE_ADMIN and not _has_editor_access(set_id):
            abort(403)  # Không có quyền
    
    form = FlashcardSetForm(obj=flashcard_set)
    _apply_is_public_restrictions(form)

    # Determine available keys by scanning all items
    items = LearningItem.query.filter_by(container_id=set_id, item_type='FLASHCARD').all()
    all_keys = set(['front', 'back'])
    
    for item in items:
        if item.content:
            all_keys.update(item.content.keys())
        if item.custom_data:
            all_keys.update(item.custom_data.keys())
            
    # Sort: front, back first, then others alphabetically
    available_keys = []
    if 'front' in all_keys: available_keys.append('front')
    if 'back' in all_keys: available_keys.append('back')
    
    # Add remainder sorted
    others = sorted([k for k in all_keys if k not in ('front', 'back')])
    available_keys.extend(others)

    if request.method == 'GET':
        ai_prompt_value = getattr(flashcard_set, 'ai_prompt', None)
        ai_settings_payload = flashcard_set.ai_settings if hasattr(flashcard_set, 'ai_settings') else None
        if not ai_prompt_value and isinstance(ai_settings_payload, dict):
            ai_prompt_value = ai_settings_payload.get('custom_prompt', '')
        form.ai_prompt.data = ai_prompt_value or ''

        # Populate settings JSON to form
        if flashcard_set.settings:
            try:
                form.settings.data = json.dumps(flashcard_set.settings)
            except:
                form.settings.data = '{}'

        media_folders = _get_media_folders_from_container(flashcard_set)
        form.image_base_folder.data = media_folders.get('image')
        form.audio_base_folder.data = media_folders.get('audio')
        container_capabilities = _get_container_capabilities(flashcard_set)
        form.supports_pronunciation.data = 'supports_pronunciation' in container_capabilities
        form.supports_writing.data = 'supports_writing' in container_capabilities
        form.supports_quiz.data = 'supports_quiz' in container_capabilities
        form.supports_essay.data = 'supports_essay' in container_capabilities
        form.supports_listening.data = 'supports_listening' in container_capabilities
        form.supports_speaking.data = 'supports_speaking' in container_capabilities
        form.supports_flashcard.data = 'supports_flashcard' in container_capabilities
        form.supports_matching.data = 'supports_matching' in container_capabilities
        form.supports_speed.data = 'supports_speed' in container_capabilities

    editable_set_ids = [
        cid
        for (cid,) in (
            _get_editable_flashcard_sets_query()
            .order_by(LearningContainer.container_id.asc())
            .with_entities(LearningContainer.container_id)
            .all()
        )
    ]

    previous_set_id = None
    next_set_id = None
    if set_id in editable_set_ids:
        current_index = editable_set_ids.index(set_id)
        if current_index > 0:
            previous_set_id = editable_set_ids[current_index - 1]
        if current_index < len(editable_set_ids) - 1:
            next_set_id = editable_set_ids[current_index + 1]
    if form.validate_on_submit():
        flash_message = ''
        flash_category = ''
        try:
            media_folders = _get_media_folders_from_container(flashcard_set)
            image_folder = media_folders.get('image')
            # Cập nhật thông tin bộ Flashcard
            flashcard_set.title = form.title.data
            flashcard_set.description = form.description.data
            flashcard_set.cover_image = _process_relative_url(form.cover_image.data, image_folder)
            flashcard_set.tags = form.tags.data
            flashcard_set.is_public = False if current_user.user_role == 'free' else form.is_public.data
            flashcard_set.ai_settings = _build_ai_settings_from_form(form, flashcard_set.ai_settings)
            
            # Save settings
            if form.settings.data:
                try:
                    flashcard_set.settings = json.loads(form.settings.data)
                except Exception as e:
                    current_app.logger.error(f"Error parsing settings JSON: {e}")
            
            safe_commit(db.session)
            
            # Xử lý file Excel nếu có (import/update/delete thẻ từ Data sheet)
            excel_summary = ''
            if form.excel_file.data and form.excel_file.data.filename != '':
                try:
                    excel_summary = FlashcardExcelService.process_import(
                        container_id=set_id,
                        excel_file=form.excel_file.data
                    )
                    db.session.commit()
                except Exception as excel_error:
                    db.session.rollback()
                    current_app.logger.error(f"Error importing Excel: {excel_error}")
                    excel_summary = f'Lỗi import Excel: {str(excel_error)}'
            
            if excel_summary:
                flash_message = f'Đã cập nhật bộ thẻ. {excel_summary}'
            else:
                flash_message = 'Đã cập nhật bộ thẻ thành công!'
            flash_category = 'success'
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error updating flashcard set: {e}")
            flash_message = f'Có lỗi xảy ra: {str(e)}'
            flash_category = 'danger'

        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            if flash_message:
                 flash(flash_message, flash_category)
            if flash_category == 'success':
                return success_response(message=flash_message)
            else:
                return error_response(flash_message)
            
        return redirect(url_for('content_management.flashcards.sets.list_flashcard_sets'))

    return render_dynamic_template('pages/content_management/flashcards/sets/_add_edit_flashcard_set_bare.html',
        form=form,
        is_edit=True,
        flashcard_set=flashcard_set,
        available_keys=available_keys,
        set_id=set_id,
        previous_set_id=previous_set_id,
        next_set_id=next_set_id
    )

@flashcards_bp.route('/flashcards/set/<int:set_id>/settings/update', methods=['POST'])
@login_required
def update_flashcard_set_settings(set_id):
    """
    API endpoint để cập nhật riêng phần settings (cấu hình mặc định) cho bộ thẻ.
    Dùng nút 'Lưu Cấu hình' riêng biệt.
    """
    flashcard_set = db.session.get(LearningContainer, set_id)
    if not flashcard_set:
        return error_response('Không tìm thấy bộ thẻ.', 'NOT_FOUND', 404)
        
    # Check permission (contributor or admin)
    if flashcard_set.creator_user_id != current_user.user_id and current_user.user_role not in ['admin', 'manager']:
         # check contributor
         is_contrib = ContainerContributor.query.filter_by(
            container_id=set_id, 
            user_id=current_user.user_id
         ).first() is not None
         if not is_contrib:
            return error_response('Bạn không có quyền sửa bộ thẻ này.', 'FORBIDDEN', 403)

    try:
        data = request.get_json()
        if not data or 'settings' not in data:
            return error_response('Dữ liệu không hợp lệ.', 'BAD_REQUEST', 400)
            
        new_settings = data['settings']
        
        # Merge or replace? 
        # Replace is safer to match UI state exactly.
        # But we should preserve other keys if they exist? 
        # The UI sends 'mcq', 'typing', 'listening'. 
        # If there are other hidden settings in DB, we might overwrite them.
        # Let's inspect current settings.
        current_settings = flashcard_set.settings or {}
        
        # Merge specific keys from payload
        for mode in ['mcq', 'typing', 'listening']:
            if mode in new_settings:
                current_settings[mode] = new_settings[mode]
            elif mode in current_settings:
                 # If UI sends nothing for a mode but it exists in DB, should we keep it?
                 # The UI sends empty list if cleared. So we trust the UI payload.
                 pass

        flashcard_set.settings = current_settings
        flag_modified(flashcard_set, "settings") # Validates for JSON updates
        
        safe_commit(db.session)
        
        return success_response(message='Đã lưu cấu hình mặc định thành công!')
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error updating flashcard set settings: {e}")
        return error_response(f'Lỗi server: {str(e)}', 'SERVER_ERROR', 500)

@flashcards_bp.route('/flashcards/delete/<int:set_id>', methods=['POST'])
@login_required
def delete_flashcard_set(set_id):
    """
    Mô tả: Xóa một bộ Flashcard.

    Hàm này cho phép xóa một bộ Flashcard và các thẻ liên quan.
    Chỉ người tạo hoặc admin mới có quyền xóa.
    """
    flashcard_set = LearningContainer.query.get_or_404(set_id)
    # Kiểm tra quyền xóa
    if current_user.user_role != 'admin' and flashcard_set.creator_user_id != current_user.user_id:
        abort(403) # Không có quyền
    
    db.session.delete(flashcard_set)
    db.session.commit() # Lưu thay đổi
    
    flash('Bộ thẻ đã được xóa thành công!', 'success')
    return redirect(url_for('content_management.content_dashboard', tab='flashcards'))

@flashcards_bp.route('/flashcards/<int:set_id>/items')
@login_required
def list_flashcard_items(set_id):
    """
    Mô tả: Hiển thị danh sách các thẻ Flashcard trong một bộ cụ thể.

    Hàm này truy xuất các thẻ Flashcard của một bộ, áp dụng bộ lọc tìm kiếm
    trên nội dung thẻ và phân trang, sau đó hiển thị chúng.
    """
    flashcard_set = LearningContainer.query.get_or_404(set_id)
    # Kiểm tra quyền xem
    if not flashcard_set.is_public and flashcard_set.creator_user_id != current_user.user_id:
        if current_user.user_role == User.ROLE_ADMIN:
            pass
        elif current_user.user_role == User.ROLE_FREE or not _has_editor_access(set_id):
            abort(403)  # Không có quyền

    page = request.args.get('page', 1, type=int)
    search_query = request.args.get('q', '', type=str)
    search_field = request.args.get('search_field', 'all', type=str) # Lấy trường tìm kiếm từ request

    base_query = LearningItem.query.filter_by(
        container_id=flashcard_set.container_id,
        item_type='FLASHCARD'
    )

    # Ánh xạ các trường có thể tìm kiếm cho Flashcard Item
    # LearningItem.content là kiểu JSON, truy cập các khóa bằng cú pháp []
    item_search_field_map = {
        'front': LearningItem.content['front'],
        'back': LearningItem.content['back'],
        'front_audio_content': LearningItem.content['front_audio_content'],
        'back_audio_content': LearningItem.content['back_audio_content'],
        'front_img': LearningItem.content['front_img'],
        'back_img': LearningItem.content['back_img'],
        'ai_prompt': LearningItem.content['ai_prompt']
    }
    
    # Áp dụng bộ lọc tìm kiếm với search_field_map đúng định dạng
    base_query = apply_search_filter(base_query, search_query, item_search_field_map, search_field)
    
    # Lấy dữ liệu phân trang
    # ĐÃ SỬA: Sắp xếp theo `order_in_container` thay vì ID
    pagination = get_pagination_data(base_query.order_by(LearningItem.order_in_container), page)
    flashcard_items = pagination.items

    # Kiểm tra quyền chỉnh sửa
    can_edit = (
        current_user.user_role == User.ROLE_ADMIN or
        flashcard_set.creator_user_id == current_user.user_id or
        _has_editor_access(set_id)
    )
    
    return render_dynamic_template('pages/content_management/flashcards/items/flashcard_items.html',
                           flashcard_set=flashcard_set,
                           flashcard_items=flashcard_items,
                           can_edit=can_edit,
                           pagination=pagination,
                           search_query=search_query,
                           search_field=search_field, # Truyền trường tìm kiếm hiện tại
                           search_field_map=item_search_field_map # Truyền map để tạo dropdown cho template
                           )

@flashcards_bp.route('/flashcards/<int:set_id>/items/reorder', methods=['POST'])
@login_required
def reorder_flashcard_items(set_id):
    flashcard_set = LearningContainer.query.get_or_404(set_id)
    if flashcard_set.creator_user_id != current_user.user_id:
        if current_user.user_role == User.ROLE_FREE:
            abort(403)
        if current_user.user_role != User.ROLE_ADMIN and not _has_editor_access(set_id):
            abort(403)

    payload = request.get_json(silent=True) or {}
    order_payload = payload.get('order')
    if not isinstance(order_payload, list) or not order_payload:
        return error_response('Dữ liệu sắp xếp không hợp lệ.', 'BAD_REQUEST', 400)

    order_map = {}
    try:
        for entry in order_payload:
            item_id = int(entry['item_id'])
            order_value = int(entry['order'])
            order_map[item_id] = order_value
    except (KeyError, TypeError, ValueError):
        return error_response('Định dạng dữ liệu không hợp lệ.', 'BAD_REQUEST', 400)

    if len(order_map) != len(set(order_map.values())):
        return error_response('Thứ tự mới không hợp lệ.', 'BAD_REQUEST', 400)

    items = LearningItem.query.filter(
        LearningItem.container_id == set_id,
        LearningItem.item_type == 'FLASHCARD',
        LearningItem.item_id.in_(order_map.keys())
    ).all()

    if len(items) != len(order_map):
        return error_response('Không tìm thấy một số thẻ cần sắp xếp.', 'NOT_FOUND', 404)

    for item in items:
        new_position = order_map.get(item.item_id)
        if new_position is not None:
            item.order_in_container = new_position

    db.session.commit()
    db.session.commit()
    return success_response(message='Thứ tự thẻ đã được cập nhật.')


@flashcards_bp.route('/flashcards/<int:set_id>/items/<int:item_id>/search-image', methods=['POST'])
@login_required
def search_flashcard_image(set_id, item_id):
    flashcard_set = LearningContainer.query.get_or_404(set_id)

    if flashcard_set.container_type != 'FLASHCARD_SET':
        abort(404)

    if not (
        current_user.user_role == User.ROLE_ADMIN
        or flashcard_set.creator_user_id == current_user.user_id
        or _has_editor_access(set_id)
    ):
        return error_response('Bạn không có quyền thực hiện thao tác này.', 'FORBIDDEN', 403)

    if item_id:
        flashcard_item = LearningItem.query.filter_by(
            item_id=item_id,
            container_id=set_id,
            item_type='FLASHCARD'
        ).first()

        if not flashcard_item:
            return error_response('Không tìm thấy thẻ phù hợp.', 'NOT_FOUND', 404)

    payload = request.get_json(silent=True) or {}
    side = (payload.get('side') or 'front').lower()
    query = (payload.get('query') or '').strip()

    if side not in {'front', 'back'}:
        return error_response('Mặt thẻ không hợp lệ.', 'BAD_REQUEST', 400)

    if not query:
        return error_response('Vui lòng nhập nội dung để tìm kiếm ảnh.', 'BAD_REQUEST', 400)

    try:
        absolute_path, success, message = image_service.get_cached_or_download_image(query)
        if not success or not absolute_path:
            return error_response(message or 'Không tìm thấy ảnh phù hợp.', 'NOT_FOUND', 404)

        image_folder = _get_media_folders_from_container(flashcard_set).get('image')
        if not image_folder:
            image_folder = _ensure_container_media_folder(flashcard_set, 'image')

        try:
            os.makedirs(os.path.join(current_app.static_folder, image_folder), exist_ok=True)
        except OSError as folder_exc:
            current_app.logger.error(
                "Không thể tạo thư mục ảnh %s: %s", image_folder, folder_exc, exc_info=True
            )
            return error_response('Không thể chuẩn bị thư mục lưu ảnh.', 'SERVER_ERROR', 500)

        filename = os.path.basename(absolute_path)
        destination = os.path.join(current_app.static_folder, image_folder, filename)

        try:
            if os.path.abspath(absolute_path) != os.path.abspath(destination):
                if os.path.exists(destination):
                    os.remove(destination)
                shutil.move(absolute_path, destination)
        except Exception as move_exc:  # pylint: disable=broad-except
            current_app.logger.error(
                "Lỗi khi di chuyển ảnh vào thư mục %s: %s", image_folder, move_exc, exc_info=True
            )
            return error_response('Không thể lưu file ảnh.', 'SERVER_ERROR', 500)

        stored_value = normalize_media_value_for_storage(filename, image_folder)
        relative_path = build_relative_media_path(stored_value, image_folder)

        if not relative_path:
            return error_response('Không thể xử lý đường dẫn ảnh.', 'SERVER_ERROR', 500)

        image_url = url_for('static', filename=relative_path)
        return success_response(message='Đã tìm thấy ảnh minh họa.', data={
            'relative_path': relative_path,
            'stored_value': stored_value,
            'image_url': image_url
        })
    except Exception as exc:  # pylint: disable=broad-except
        current_app.logger.error(
            "Lỗi khi tìm ảnh minh họa cho bộ thẻ %s: %s", set_id, exc, exc_info=True
        )
        return error_response('Đã xảy ra lỗi khi tìm kiếm ảnh.', 'SERVER_ERROR', 500)

@flashcards_bp.route('/flashcards/<int:set_id>/items/add', methods=['GET', 'POST'])
@login_required
def add_flashcard_item(set_id):
    """
    Mô tả: Thêm một thẻ Flashcard mới vào một bộ cụ thể.

    Hàm này xử lý việc thêm một thẻ Flashcard mới vào một bộ Flashcard hiện có.
    """
    flashcard_set = LearningContainer.query.get_or_404(set_id)
    # Kiểm tra quyền thêm thẻ
    if flashcard_set.creator_user_id != current_user.user_id:
        if current_user.user_role == User.ROLE_FREE:
            abort(403)
        if current_user.user_role != User.ROLE_ADMIN and not _has_editor_access(set_id):
            abort(403)  # Không có quyền
    
    form = FlashcardItemForm()
    media_folders = _get_media_folders_from_container(flashcard_set)
    image_folder = media_folders.get('image')
    audio_folder = media_folders.get('audio')
    container_capabilities = _get_container_capabilities(flashcard_set)
    container_capabilities = _get_container_capabilities(flashcard_set)
    # Capabilities are for the container, not the item form.
    # Logic to populate item form fields based on capabilities should be done if fields exist, but they don't here.
    # Removing correct assignments.
    if form.validate_on_submit():
        # THÊM MỚI: Xử lý logic chèn thẻ
        new_order = form.order_in_container.data
        
        if new_order is not None:
            # Cập nhật lại thứ tự của các thẻ cũ
            db.session.query(LearningItem).filter(
                LearningItem.container_id == set_id,
                LearningItem.item_type == 'FLASHCARD',
                LearningItem.order_in_container >= new_order
            ).update({
                LearningItem.order_in_container: LearningItem.order_in_container + 1
            })
        else:
            # Nếu không có thứ tự cụ thể, thêm vào cuối
            max_order = db.session.query(db.func.max(LearningItem.order_in_container)).filter_by(
                container_id=set_id,
                item_type='FLASHCARD'
            ).scalar()
            new_order = (max_order or 0) + 1
        
        # Tạo thẻ Flashcard mới
        content_dict = {
            'front': form.front.data, 'back': form.back.data,
            'front_audio_content': form.front_audio_content.data,
            'front_audio_url': _process_relative_url(form.front_audio_url.data, audio_folder),
            'back_audio_content': form.back_audio_content.data,
            'back_audio_url': _process_relative_url(form.back_audio_url.data, audio_folder),
            'front_img': _process_relative_url(form.front_img.data, image_folder),
            'back_img': _process_relative_url(form.back_img.data, image_folder),
        }
        if form.ai_prompt.data:
            content_dict['ai_prompt'] = form.ai_prompt.data
        if form.memrise_prompt.data:
            content_dict['memrise_prompt'] = form.memrise_prompt.data
        if form.memrise_answers.data:
            content_dict['memrise_answers'] = form.memrise_answers.data

        new_item = LearningItem(
            container_id=set_id,
            item_type='FLASHCARD',
            content=content_dict,
            order_in_container=new_order,
            ai_explanation=form.ai_explanation.data
        )
        db.session.add(new_item)
        db.session.commit() # Lưu thay đổi
        
        # Trả về phản hồi JSON hoặc chuyển hướng tùy theo yêu cầu
        # Trả về phản hồi JSON hoặc chuyển hướng tùy theo yêu cầu
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return success_response(message='Thẻ mới đã được thêm!', data={'item_id': new_item.item_id})
        else:
            flash('Thẻ mới đã được thêm!', 'success')
            return redirect(url_for('.list_flashcard_items', set_id=set_id))
    
    # Xử lý lỗi form validation cho AJAX
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest' and request.method == 'POST':
        return error_response('Dữ liệu không hợp lệ', 'VALIDATION_ERROR', 400, details=form.errors)
    
    context = {
        'form': form,
        'flashcard_set': flashcard_set,
        'flashcard_item': None,
        'title': 'Thêm Thẻ',
        'front_image_url': _get_static_image_url(form.front_img.data, image_folder),
        'back_image_url': _get_static_image_url(form.back_img.data, image_folder),
        'front_audio_url_resolved': _get_static_audio_url(form.front_audio_url.data, audio_folder),
        'back_audio_url_resolved': _get_static_audio_url(form.back_audio_url.data, audio_folder),
        'image_search_url': url_for('.search_flashcard_image', set_id=set_id, item_id=0),
        'regenerate_audio_url': url_for('learning.flashcard_learning.regenerate_audio_from_content'),
        'image_base_folder': image_folder,
        'audio_base_folder': audio_folder,
        'move_targets': [],
        'previous_item_id': None,
        'next_item_id': None,
        'is_modal_view': request.args.get('is_modal') == 'true',
    }

    # Render template cho modal hoặc trang đầy đủ
    if request.method == 'GET' and request.args.get('is_modal') == 'true':
        return render_dynamic_template('pages/content_management/flashcards/items/_add_edit_flashcard_item_bare.html', **context)
    return render_dynamic_template('pages/content_management/flashcards/items/add_edit_flashcard_item.html', **context)

@flashcards_bp.route('/flashcards/edit/<int:set_id>/items/edit/<int:item_id>', methods=['GET', 'POST'])
@login_required
def edit_flashcard_item(set_id, item_id):
    """
    Mô tả: Chỉnh sửa một thẻ Flashcard hiện có trong một bộ cụ thể.

    Hàm này xử lý việc cập nhật nội dung của một thẻ Flashcard.
    """
    flashcard_set = LearningContainer.query.get_or_404(set_id)
    flashcard_item = LearningItem.query.filter_by(item_id=item_id, container_id=set_id).first_or_404()
    # Kiểm tra quyền chỉnh sửa
    if flashcard_set.creator_user_id != current_user.user_id:
        if current_user.user_role == User.ROLE_FREE:
            abort(403)
        if current_user.user_role != User.ROLE_ADMIN and not _has_editor_access(set_id):
            abort(403)  # Không có quyền
    
    # Khởi tạo form với dữ liệu hiện có
    form = FlashcardItemForm(obj=flashcard_item.content)
    media_folders = _get_media_folders_from_container(flashcard_set)
    image_folder = media_folders.get('image')
    audio_folder = media_folders.get('audio')
    container_capabilities = _get_container_capabilities(flashcard_set)
    move_targets = (
        _get_editable_flashcard_sets_query(exclude_id=set_id)
        .order_by(LearningContainer.title)
        .all()
    )

    current_order = flashcard_item.order_in_container if flashcard_item.order_in_container is not None else -1
    previous_item = (
        LearningItem.query.filter(
            LearningItem.container_id == set_id,
            LearningItem.item_type == 'FLASHCARD',
            LearningItem.order_in_container < current_order,
        )
        .order_by(LearningItem.order_in_container.desc())
        .first()
    )
    next_item = (
        LearningItem.query.filter(
            LearningItem.container_id == set_id,
            LearningItem.item_type == 'FLASHCARD',
            LearningItem.order_in_container > current_order,
        )
        .order_by(LearningItem.order_in_container.asc())
        .first()
    )
    if form.validate_on_submit():
        # Lấy thứ tự cũ và mới
        old_order = flashcard_item.order_in_container
        new_order = form.order_in_container.data
        
        # Nếu thứ tự thay đổi, cập nhật lại các thẻ khác
        if new_order is not None and new_order != old_order:
            if new_order > old_order:
                db.session.query(LearningItem).filter(
                    LearningItem.container_id == set_id,
                    LearningItem.item_type == 'FLASHCARD',
                    LearningItem.order_in_container > old_order,
                    LearningItem.order_in_container <= new_order
                ).update({
                    LearningItem.order_in_container: LearningItem.order_in_container - 1
                })
            else: # new_order < old_order
                db.session.query(LearningItem).filter(
                    LearningItem.container_id == set_id,
                    LearningItem.item_type == 'FLASHCARD',
                    LearningItem.order_in_container >= new_order,
                    LearningItem.order_in_container < old_order
                ).update({
                    LearningItem.order_in_container: LearningItem.order_in_container + 1
                })
            flashcard_item.order_in_container = new_order
        
        # Cập nhật nội dung thẻ
        flashcard_item.content['front'] = form.front.data
        flashcard_item.content['back'] = form.back.data
        flashcard_item.content['front_audio_content'] = form.front_audio_content.data
        flashcard_item.content['front_audio_url'] = _process_relative_url(form.front_audio_url.data, audio_folder)
        flashcard_item.content['back_audio_content'] = form.back_audio_content.data
        flashcard_item.content['back_audio_url'] = _process_relative_url(form.back_audio_url.data, audio_folder)
        flashcard_item.content['front_img'] = _process_relative_url(form.front_img.data, image_folder)
        flashcard_item.content['back_img'] = _process_relative_url(form.back_img.data, image_folder)
        flashcard_item.ai_explanation = form.ai_explanation.data
        
        # Handle Dynamic Custom Data (Key-Value Pairs)
        custom_keys = request.form.getlist('custom_keys[]')
        custom_values = request.form.getlist('custom_values[]')
        
        # Filter out empty keys and pairs where both key and value are empty
        new_custom_data = {}
        if custom_keys and custom_values:
            for k, v in zip(custom_keys, custom_values):
                clean_k = k.strip()
                if clean_k: # Key must not be empty
                    new_custom_data[clean_k] = v.strip()
        
        flashcard_item.custom_data = new_custom_data if new_custom_data else None

        
        if form.ai_prompt.data:
            flashcard_item.content['ai_prompt'] = form.ai_prompt.data
        elif 'ai_prompt' in flashcard_item.content:
            del flashcard_item.content['ai_prompt']

        # Memrise fields
        if form.memrise_prompt.data:
            flashcard_item.content['memrise_prompt'] = form.memrise_prompt.data
        elif 'memrise_prompt' in flashcard_item.content:
            del flashcard_item.content['memrise_prompt']
        if form.memrise_answers.data:
            flashcard_item.content['memrise_answers'] = form.memrise_answers.data
        elif 'memrise_answers' in flashcard_item.content:
            del flashcard_item.content['memrise_answers']

        # Đánh dấu trường JSON đã thay đổi để SQLAlchemy lưu lại
        flag_modified(flashcard_item, "content")
        db.session.commit() # Lưu thay đổi
        
        # Trả về phản hồi JSON hoặc chuyển hướng tùy theo yêu cầu
        # Trả về phản hồi JSON hoặc chuyển hướng tùy theo yêu cầu
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return success_response(message='Thẻ đã được cập nhật!', data={'item_id': flashcard_item.item_id})
        else:
            flash('Thẻ đã được cập nhật!', 'success')
            return redirect(url_for('.list_flashcard_items', set_id=set_id))
    
    # Nếu là GET request, populate form với dữ liệu hiện có
    if request.method == 'GET':
        form.front.data = flashcard_item.content.get('front')
        form.back.data = flashcard_item.content.get('back')
        form.front_audio_content.data = flashcard_item.content.get('front_audio_content')
        form.front_audio_url.data = flashcard_item.content.get('front_audio_url')
        form.back_audio_content.data = flashcard_item.content.get('back_audio_content')
        form.back_audio_url.data = flashcard_item.content.get('back_audio_url')
        form.front_img.data = flashcard_item.content.get('front_img')
        form.back_img.data = flashcard_item.content.get('back_img')
        form.ai_prompt.data = flashcard_item.content.get('ai_prompt')
        def _resolve_flag(flag_name):
            if flag_name in flashcard_item.content:
                return bool(flashcard_item.content.get(flag_name))
            return flag_name in container_capabilities


        # Gán giá trị `order_in_container` vào form
        form.order_in_container.data = flashcard_item.order_in_container
        form.ai_explanation.data = flashcard_item.ai_explanation
        
        # Prepare custom data for Key-Value UI
        # We don't use form field anymore

        # Memrise fields
        form.memrise_prompt.data = flashcard_item.content.get('memrise_prompt', '')
        form.memrise_answers.data = flashcard_item.content.get('memrise_answers', '')
    
    context = {
        'form': form,
        'flashcard_set': flashcard_set,
        'flashcard_item': flashcard_item,
        'title': 'Sửa Thẻ',
        'front_image_url': _get_static_image_url(form.front_img.data, image_folder),
        'back_image_url': _get_static_image_url(form.back_img.data, image_folder),
        'front_audio_url_resolved': _get_static_audio_url(form.front_audio_url.data, audio_folder),
        'back_audio_url_resolved': _get_static_audio_url(form.back_audio_url.data, audio_folder),
        'image_search_url': url_for('.search_flashcard_image', set_id=set_id, item_id=item_id),
        'regenerate_audio_url': url_for('learning.flashcard_learning.regenerate_audio_from_content'),
        'image_base_folder': image_folder,
        'audio_base_folder': audio_folder,
        'move_targets': move_targets,
        'previous_item_id': previous_item.item_id if previous_item else None,
        'next_item_id': next_item.item_id if next_item else None,
        'is_modal_view': request.args.get('is_modal') == 'true',
    }

    # Render template cho modal hoặc trang đầy đủ
    if request.method == 'GET' and request.args.get('is_modal') == 'true':
        return render_dynamic_template('pages/content_management/flashcards/items/_add_edit_flashcard_item_bare.html', **context)
    return render_dynamic_template('pages/content_management/flashcards/items/add_edit_flashcard_item.html', **context)


@flashcards_bp.route('/flashcards/edit/<int:set_id>/items/<int:item_id>/move', methods=['POST'])
@login_required
def move_flashcard_item(set_id, item_id):
    flashcard_set = LearningContainer.query.get_or_404(set_id)
    flashcard_item = LearningItem.query.filter_by(item_id=item_id, container_id=set_id, item_type='FLASHCARD').first_or_404()

    if current_user.user_role not in {User.ROLE_ADMIN} and flashcard_set.creator_user_id != current_user.user_id:
        if current_user.user_role == User.ROLE_FREE or not _has_editor_access(set_id):
            abort(403)

    target_set_id = request.form.get('target_set_id', type=int)
    if not target_set_id:
        flash('Vui lòng chọn bộ thẻ đích để di chuyển.', 'warning')
        return redirect(url_for('.edit_flashcard_item', set_id=set_id, item_id=item_id))

    target_set = LearningContainer.query.filter_by(container_id=target_set_id, container_type='FLASHCARD_SET').first()
    if not target_set:
        flash('Không tìm thấy bộ thẻ đích.', 'danger')
        return redirect(url_for('.edit_flashcard_item', set_id=set_id, item_id=item_id))

    if current_user.user_role not in {User.ROLE_ADMIN} and target_set.creator_user_id != current_user.user_id:
        if current_user.user_role == User.ROLE_FREE or not _has_editor_access(target_set.container_id):
            abort(403)

    if target_set.container_id == set_id:
        flash('Thẻ đã nằm trong bộ này.', 'info')
        return redirect(url_for('.edit_flashcard_item', set_id=set_id, item_id=item_id))

    db.session.query(LearningItem).filter(
        LearningItem.container_id == set_id,
        LearningItem.item_type == 'FLASHCARD',
        LearningItem.order_in_container > flashcard_item.order_in_container
    ).update({LearningItem.order_in_container: LearningItem.order_in_container - 1})

    max_order = db.session.query(func.max(LearningItem.order_in_container)).filter_by(
        container_id=target_set.container_id,
        item_type='FLASHCARD'
    ).scalar() or 0

    flashcard_item.container_id = target_set.container_id
    flashcard_item.order_in_container = max_order + 1

    db.session.commit()

    flash(f"Đã di chuyển thẻ sang bộ '{target_set.title}'.", 'success')
    return redirect(url_for('.list_flashcard_items', set_id=target_set.container_id))

@flashcards_bp.route('/flashcards/delete/<int:set_id>/items/delete/<int:item_id>', methods=['POST'])
@login_required
def delete_flashcard_item(set_id, item_id):
    """
    Mô tả: Xóa một thẻ Flashcard khỏi một bộ cụ thể.

    Hàm này xử lý việc xóa một thẻ Flashcard.
    """
    flashcard_set = LearningContainer.query.get_or_404(set_id)
    flashcard_item = LearningItem.query.filter_by(item_id=item_id, container_id=set_id).first_or_404()
    if flashcard_set.creator_user_id != current_user.user_id:
        if current_user.user_role == User.ROLE_FREE:
            abort(403)
        if current_user.user_role != User.ROLE_ADMIN and not _has_editor_access(set_id):
            abort(403)  # Không có quyền
    
    db.session.delete(flashcard_item)
    db.session.commit() # Lưu thay đổi
    
    # Trả về phản hồi JSON hoặc chuyển hướng tùy theo yêu cầu
    # Trả về phản hồi JSON hoặc chuyển hướng tùy theo yêu cầu
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return success_response(message='Thẻ đã được xóa.')
    else:
        flash('Thẻ đã được xóa.', 'success')
        return redirect(url_for('.list_flashcard_items', set_id=set_id))