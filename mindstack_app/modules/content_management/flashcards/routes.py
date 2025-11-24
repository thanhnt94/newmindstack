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
from flask_login import login_required, current_user
from sqlalchemy import or_, func
from sqlalchemy.orm.attributes import flag_modified
from ..forms import FlashcardSetForm, FlashcardItemForm
from ....models import db, LearningContainer, LearningItem, ContainerContributor, User
from mindstack_app.modules.shared.utils.media_paths import (
    normalize_media_folder,
    normalize_media_value_for_storage,
    build_relative_media_path,
)
from ....modules.shared.utils.db_session import safe_commit
from ....modules.shared.utils.excel import extract_info_sheet_mapping, format_info_warnings
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
from ....modules.shared.utils.pagination import get_pagination_data
from ....modules.shared.utils.search import apply_search_filter
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.datavalidation import DataValidation
# THÊM MỚI: Import AudioService
from ...learning.flashcard.individual.audio_service import AudioService
from ...learning.flashcard.individual.image_service import ImageService

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
)

MEDIA_URL_FIELDS = {'front_img', 'back_img', 'front_audio_url', 'back_audio_url'}

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
    'ai_prompt',
    'supports_pronunciation',
    'supports_writing',
    'supports_quiz',
    'supports_essay',
    'supports_listening',
    'supports_speaking',
    'action',
]

FLASHCARD_INFO_KEYS = [
    'title',
    'description',
    'tags',
    'is_public',
    *CAPABILITY_FLAGS,
    'image_base_folder',
    'audio_base_folder',
    'ai_prompt',
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


def _create_flashcard_excel(info_rows, data_rows, *, output_path: Optional[str] = None):
    info_df = pd.DataFrame(info_rows, columns=['Key', 'Value'])
    if not info_df.empty:
        info_df['Value'] = info_df['Value'].apply(lambda value: '' if value is None else str(value))
    else:
        info_df = pd.DataFrame(columns=['Key', 'Value'])

    data_df = pd.DataFrame(data_rows, columns=FLASHCARD_DATA_COLUMNS)
    if data_df.empty:
        data_df = pd.DataFrame(columns=FLASHCARD_DATA_COLUMNS)
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
            _apply_action_dropdown(data_sheet, FLASHCARD_DATA_COLUMNS)

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
        'tags': flashcard_set.tags or '',
        'is_public': 'True' if flashcard_set.is_public else 'False',
        'image_base_folder': image_folder or '',
        'audio_base_folder': audio_folder or '',
        'ai_prompt': ai_prompt_value or '',
    }

    for capability_key in CAPABILITY_FLAGS:
        info_mapping[capability_key] = 'True' if capability_key in container_capabilities else 'False'

    info_rows = [
        {'Key': key, 'Value': info_mapping.get(key, '')}
        for key in FLASHCARD_INFO_KEYS
    ]

    data_rows = []
    for item in items:
        content = item.content or {}
        row = {column: '' for column in FLASHCARD_DATA_COLUMNS}
        row['item_id'] = item.item_id
        row['order_in_container'] = item.order_in_container if item.order_in_container is not None else ''
        row['front'] = content.get('front') or ''
        row['back'] = content.get('back') or ''
        row['front_audio_content'] = content.get('front_audio_content') or ''
        row['back_audio_content'] = content.get('back_audio_content') or ''
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
        row['ai_prompt'] = content.get('ai_prompt') or ''

        for capability_key in CAPABILITY_FLAGS:
            value = content.get(capability_key)
            if value is None:
                row[capability_key] = ''
            else:
                row[capability_key] = 'true' if bool(value) else 'false'

        row['action'] = 'None'
        data_rows.append(row)

    return info_rows, data_rows


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


def _update_flashcards_from_excel_file(container_id: int, excel_file) -> str:
    """Cập nhật dữ liệu flashcard từ file Excel được tải lên."""
    temp_filepath = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx') as tmp_file:
            excel_file.save(tmp_file.name)
            temp_filepath = tmp_file.name

        df = pd.read_excel(temp_filepath, sheet_name='Data')
        required_cols = ['front', 'back']
        if not all(col in df.columns for col in required_cols):
            raise ValueError(
                f"File Excel (sheet 'Data') phải có các cột bắt buộc: {', '.join(required_cols)}."
            )

        flashcard_set = LearningContainer.query.get(container_id)

        info_notices: list[str] = []
        media_overrides: dict[str, str] = {}
        info_mapping, info_warnings = extract_info_sheet_mapping(temp_filepath)
        if info_mapping:
            image_folder_override = normalize_media_folder(info_mapping.get('image_base_folder'))
            audio_folder_override = normalize_media_folder(info_mapping.get('audio_base_folder'))
            if image_folder_override:
                media_overrides['image'] = image_folder_override
            if audio_folder_override:
                media_overrides['audio'] = audio_folder_override
        if info_warnings:
            info_notices.extend(info_warnings)

        if media_overrides:
            flashcard_set.set_media_folders(media_overrides)

        media_folders = _get_media_folders_from_container(flashcard_set)
        image_folder = media_folders.get('image')
        audio_folder = media_folders.get('audio')

        existing_items = (
            LearningItem.query.filter_by(container_id=container_id, item_type='FLASHCARD')
            .order_by(LearningItem.order_in_container, LearningItem.item_id)
            .all()
        )
        existing_map = {item.item_id: item for item in existing_items}
        processed_ids = set()
        delete_ids = set()
        ordered_entries = []

        optional_fields = [
            'front_audio_content',
            'back_audio_content',
            'front_img',
            'back_img',
            'front_audio_url',
            'back_audio_url',
            'ai_prompt',
            'supports_pronunciation',
            'supports_writing',
            'supports_quiz',
            'supports_essay',
            'supports_listening',
            'supports_speaking',
        ]
        url_fields = {'front_img', 'back_img', 'front_audio_url', 'back_audio_url'}
        capability_fields = set(CAPABILITY_FLAGS)
        container_capabilities = _get_container_capabilities(flashcard_set)

        stats = {
            'updated': 0,
            'created': 0,
            'deleted': 0,
            'skipped': 0,
            'reordered': 0,
        }

        action_aliases = {
            'delete': {'delete', 'remove'},
            'skip': {'skip', 'keep', 'none', 'ignore', 'nochange', 'unchanged', 'giu nguyen', 'giu-nguyen', 'giu_nguyen'},
            'create': {'create', 'new', 'add', 'insert'},
            'update': {'update', 'upsert', 'edit', 'modify'},
        }

        def _normalize_action(raw_action: str | None, *, has_item_id: bool) -> str:
            value = (raw_action or '').strip().lower()
            if value:
                for normalized, alias_values in action_aliases.items():
                    if value in alias_values:
                        if normalized == 'create' and has_item_id:
                            return 'update'
                        if normalized == 'update' and not has_item_id:
                            return 'create'
                        return normalized
            return 'update' if has_item_id else 'create'

        def _get_cell(row_data, column_name):
            if column_name not in df.columns:
                return None
            value = row_data[column_name]
            if pd.isna(value):
                return None
            return str(value).strip()

        for index, row in df.iterrows():
            item_id_value = _get_cell(row, 'item_id')
            order_value = _get_cell(row, 'order_in_container')
            order_number = None
            if order_value:
                try:
                    order_number = int(float(order_value))
                    stats['reordered'] += 1
                except (TypeError, ValueError):
                    raise ValueError(
                        f"Hàng {index + 2}: order_in_container '{order_value}' không hợp lệ."
                    )

            front_content = _get_cell(row, 'front')
            back_content = _get_cell(row, 'back')

            item_id = None
            if item_id_value:
                try:
                    item_id = int(float(item_id_value))
                except (TypeError, ValueError):
                    raise ValueError(
                        f"Hàng {index + 2}: item_id '{item_id_value}' không hợp lệ."
                    )

            action_value = _normalize_action(_get_cell(row, 'action'), has_item_id=bool(item_id))

            if item_id:
                item = existing_map.get(item_id)
                if not item:
                    raise ValueError(f"Hàng {index + 2}: Không tìm thấy thẻ với ID {item_id}.")

                if action_value == 'delete':
                    delete_ids.add(item_id)
                    stats['deleted'] += 1
                    continue

                if action_value == 'skip':
                    ordered_entries.append({
                        'type': 'existing',
                        'item': item,
                        'order': order_number if order_number is not None else (item.order_in_container or 0),
                        'sequence': index,
                    })
                    processed_ids.add(item_id)
                    stats['skipped'] += 1
                    continue

                if not front_content or not back_content:
                    raise ValueError(
                        f"Hàng {index + 2}: Thẻ với ID {item_id} thiếu dữ liệu front/back."
                    )

                content_dict = item.content or {}
                content_dict['front'] = front_content
                content_dict['back'] = back_content
                ai_explanation_value = _get_cell(row, 'ai_explanation')
                content_dict.pop('ai_explanation', None)
                for field in optional_fields:
                    cell_value = _get_cell(row, field)
                    if cell_value:
                        if field in url_fields:
                            base_folder = image_folder if field in {'front_img', 'back_img'} else audio_folder
                            content_dict[field] = _process_relative_url(cell_value, base_folder)
                        elif field in capability_fields:
                            content_dict[field] = cell_value.lower() in {'true', '1', 'yes', 'y', 'on'}
                        else:
                            content_dict[field] = cell_value
                    else:
                        if field in capability_fields:
                            content_dict[field] = False
                        else:
                            content_dict.pop(field, None)
                for capability_flag in container_capabilities:
                    content_dict.setdefault(capability_flag, True)
                item.content = content_dict
                flag_modified(item, 'content')
                item.ai_explanation = ai_explanation_value or None
                ordered_entries.append({
                    'type': 'existing',
                    'item': item,
                    'order': order_number if order_number is not None else (item.order_in_container or 0),
                    'sequence': index,
                })
                processed_ids.add(item_id)
                stats['updated'] += 1
            else:
                if action_value == 'delete' or action_value == 'skip':
                    stats['skipped'] += 1
                    continue
                if not front_content or not back_content:
                    # Bỏ qua dòng rỗng
                    stats['skipped'] += 1
                    continue

                content_dict = {'front': front_content, 'back': back_content}
                ai_explanation_value = _get_cell(row, 'ai_explanation')
                for field in optional_fields:
                    cell_value = _get_cell(row, field)
                    if cell_value:
                        if field in url_fields:
                            base_folder = image_folder if field in {'front_img', 'back_img'} else audio_folder
                            content_dict[field] = _process_relative_url(cell_value, base_folder)
                        elif field in capability_fields:
                            content_dict[field] = cell_value.lower() in {'true', '1', 'yes', 'y', 'on'}
                        else:
                            content_dict[field] = cell_value
                    else:
                        if field in capability_fields:
                            content_dict[field] = False
                        else:
                            content_dict.pop(field, None)
                for capability_flag in container_capabilities:
                    content_dict.setdefault(capability_flag, True)
                ordered_entries.append({
                    'type': 'new',
                    'data': content_dict,
                    'ai_explanation': ai_explanation_value or None,
                    'order': order_number,
                    'sequence': index,
                })
                stats['created'] += 1

        untouched_items = [
            item for item in existing_items
            if item.item_id not in processed_ids and item.item_id not in delete_ids
        ]
        for offset, item in enumerate(untouched_items, start=len(df) + 1):
            ordered_entries.append({
                'type': 'existing',
                'item': item,
                'order': item.order_in_container or 0,
                'sequence': offset,
            })

        for delete_id in delete_ids:
            if delete_id in existing_map:
                db.session.delete(existing_map[delete_id])

        ordered_entries.sort(
            key=lambda entry: (
                entry['order'] if entry['order'] is not None else float('inf'),
                entry['sequence'],
            )
        )

        next_order = 1
        for entry in ordered_entries:
            if entry['type'] == 'existing':
                entry['item'].order_in_container = next_order
            else:
                new_item = LearningItem(
                    container_id=container_id,
                    item_type='FLASHCARD',
                    content=entry['data'],
                    ai_explanation=entry.get('ai_explanation'),
                    order_in_container=next_order,
                )
                db.session.add(new_item)
            next_order += 1

        summary_parts = [
            f"{stats['updated']} cập nhật",
            f"{stats['created']} thêm mới",
            f"{stats['deleted']} xoá",
            f"{stats['skipped']} giữ nguyên",
        ]
        if stats['reordered']:
            summary_parts.append(f"{stats['reordered']} dòng có sắp xếp lại")
        summary_text = ', '.join(summary_parts)
        if info_notices:
            summary_text += ' Lưu ý: ' + format_info_warnings(info_notices)
        return f'Bộ thẻ đã được xử lý: {summary_text}.'
    finally:
        if temp_filepath and os.path.exists(temp_filepath):
            os.remove(temp_filepath)

@flashcards_bp.route('/flashcards/process_excel_info', methods=['POST'])
@login_required
def process_excel_info():
    """
    Mô tả: Xử lý file Excel được tải lên để trích xuất thông tin từ sheet 'Info'.

    Hàm này đọc một file Excel, tìm kiếm sheet có tên 'Info',
    và trích xuất dữ liệu từ đó, trả về dưới dạng JSON.
    """
    if 'excel_file' not in request.files:
        return jsonify({'success': False, 'message': 'Không tìm thấy file.'}), 400
    file = request.files['excel_file']
    if file.filename == '':
        return jsonify({'success': False, 'message': 'Chưa chọn file nào.'}), 400
    if file and file.filename.endswith('.xlsx'):
        temp_filepath = None
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx') as tmp_file:
                file.save(tmp_file.name)
                temp_filepath = tmp_file.name

            info_data, info_warnings = extract_info_sheet_mapping(temp_filepath)
            if not info_data and info_warnings:
                message = format_info_warnings(info_warnings)
                return jsonify({'success': False, 'message': message}), 400

            message = 'Đã đọc thông tin từ sheet Info.'
            if info_warnings:
                message += ' ' + format_info_warnings(info_warnings)
            return jsonify({'success': True, 'data': info_data, 'message': message})
        except Exception as e:
            # Xử lý các lỗi khác khi đọc file Excel
            current_app.logger.error(f"Lỗi khi xử lý sheet Info (Flashcard): {e}")
            return jsonify({'success': False, 'message': f'Lỗi đọc file Excel: {e}'}), 500
        finally:
            # Đảm bảo xóa file tạm thời
            if temp_filepath and os.path.exists(temp_filepath):
                os.remove(temp_filepath)
    # Trả về lỗi nếu file không hợp lệ
    return jsonify({'success': False, 'message': 'File không hợp lệ. Vui lòng chọn file .xlsx'}), 400

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
        return render_template('_flashcard_sets_list.html', **template_vars)
    else:
        return render_template('flashcard_sets.html', **template_vars)


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

        info_rows, data_rows = _build_flashcard_export_payload(
            flashcard_set,
            items,
            export_mode='zip',
            media_dir=media_dir,
            media_cache=media_cache,
            image_folder=image_folder,
            audio_folder=audio_folder,
        )

        excel_path = os.path.join(tmp_dir, 'flashcards.xlsx')
        _create_flashcard_excel(info_rows, data_rows, output_path=excel_path)

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
            message = _update_flashcards_from_excel_file(set_id, uploaded_file)
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
    return render_template(
        'manage_flashcard_excel.html',
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
            # Tạo bộ Flashcard mới
            new_set = LearningContainer(
                creator_user_id=current_user.user_id,
                container_type='FLASHCARD_SET',
                title=form.title.data,
                description=form.description.data,
                tags=form.tags.data,
                is_public=False if current_user.user_role == 'free' else form.is_public.data,
                ai_settings=ai_settings_payload
            )
            if media_folders:
                new_set.set_media_folders(media_folders)
            db.session.add(new_set)
            db.session.flush() # Lưu tạm thời để có container_id

            # Xử lý file Excel nếu có
            if form.excel_file.data and form.excel_file.data.filename != '':
                excel_file = form.excel_file.data
                with tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx') as tmp_file:
                    excel_file.save(tmp_file.name)
                    temp_filepath = tmp_file.name
                
                # --- THÊM MỚI LOGIC XỬ LÝ SHEET INFO ---
                info_notices: list[str] = []
                media_overrides = {}
                info_mapping, info_warnings = extract_info_sheet_mapping(temp_filepath)
                if info_mapping:
                    image_folder_override = normalize_media_folder(info_mapping.get('image_base_folder'))
                    audio_folder_override = normalize_media_folder(info_mapping.get('audio_base_folder'))
                    if image_folder_override:
                        media_overrides['image'] = image_folder_override
                    if audio_folder_override:
                        media_overrides['audio'] = audio_folder_override
                if info_warnings:
                    info_notices.extend(info_warnings)

                if media_overrides:
                    # Áp dụng media overrides và cập nhật local folders
                    new_set.set_media_folders(media_overrides)
                    image_folder = media_overrides.get('image') or image_folder
                    audio_folder = media_overrides.get('audio') or audio_folder
                # --- KẾT THÚC THÊM MỚI ---

                df = pd.read_excel(temp_filepath, sheet_name='Data')
                required_cols = ['front', 'back']
                # Kiểm tra các cột bắt buộc
                if not all(col in df.columns for col in required_cols):
                    raise ValueError(f"File Excel (sheet 'Data') phải có các cột bắt buộc: {', '.join(required_cols)}.")
                items_added_count = 0
                for index, row in df.iterrows():
                    front_content = str(row['front']) if pd.notna(row['front']) else ''
                    back_content = str(row['back']) if pd.notna(row['back']) else ''
                    if front_content and back_content:
                        item_content = {'front': front_content, 'back': back_content}
                        optional_cols = [
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
                        ]
                        for col in optional_cols:
                            if col in df.columns and pd.notna(row[col]):
                                if col in CAPABILITY_FLAGS:
                                    item_content[col] = str(row[col]).strip().lower() in {'true', '1', 'yes', 'y', 'on'}
                                elif col in MEDIA_URL_FIELDS:
                                    base_folder = image_folder if col in {'front_img', 'back_img'} else audio_folder
                                    item_content[col] = _process_relative_url(str(row[col]), base_folder)
                                else:
                                    item_content[col] = str(row[col])
                        for capability_flag in selected_capabilities:
                            item_content.setdefault(capability_flag, True)
                        # Tạo thẻ Flashcard mới
                        new_item = LearningItem(
                            container_id=new_set.container_id,
                            item_type='FLASHCARD',
                            content=item_content,
                            order_in_container=index + 1
                        )
                        db.session.add(new_item)
                        items_added_count += 1
                flash_message = f'Bộ thẻ và {items_added_count} thẻ từ Excel đã được tạo thành công!'
                if info_notices:
                    flash_message += ' Lưu ý: ' + format_info_warnings(info_notices)
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
            return jsonify({'success': flash_category == 'success', 'message': flash_message})
        else:
            flash(flash_message, flash_category)
            return redirect(url_for('content_management.content_dashboard', tab='flashcards'))
    
    # Xử lý lỗi form validation cho AJAX
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest' and request.method == 'POST':
        return jsonify({'success': False, 'errors': form.errors}), 400
    
    # Render template cho modal hoặc trang đầy đủ
    if request.method == 'GET' and request.args.get('is_modal') == 'true':
        return render_template('_add_edit_flashcard_set_bare.html', form=form, title='Thêm Bộ thẻ ghi nhớ', template_url=template_url)
    return render_template('add_edit_flashcard_set.html', form=form, title='Thêm Bộ thẻ ghi nhớ', template_url=template_url)

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
    if request.method == 'GET':
        ai_prompt_value = getattr(flashcard_set, 'ai_prompt', None)
        ai_settings_payload = flashcard_set.ai_settings if hasattr(flashcard_set, 'ai_settings') else None
        if not ai_prompt_value and isinstance(ai_settings_payload, dict):
            ai_prompt_value = ai_settings_payload.get('custom_prompt', '')
        form.ai_prompt.data = ai_prompt_value or ''

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
    if form.validate_on_submit():
        flash_message = ''
        flash_category = ''
        try:
            # Cập nhật thông tin bộ Flashcard
            flashcard_set.title = form.title.data
            flashcard_set.description = form.description.data
            flashcard_set.tags = form.tags.data
            flashcard_set.is_public = False if current_user.user_role == 'free' else form.is_public.data
            flashcard_set.ai_settings = _build_ai_settings_from_form(form, flashcard_set.ai_settings)

            # Xử lý file Excel nếu có để cập nhật các thẻ
            if form.excel_file.data and form.excel_file.data.filename != '':
                flash_message = _update_flashcards_from_excel_file(set_id, form.excel_file.data)
                flash_category = 'success'
            else:
                flash_message = 'Bộ thẻ đã được cập nhật!'
                flash_category = 'success'
            db.session.commit() # Lưu các thay đổi vào DB
        except Exception as e:
            db.session.rollback() # Hoàn tác nếu có lỗi
            flash_message = f'Lỗi khi xử lý: {str(e)}'
            flash_category = 'danger'

        # Trả về phản hồi JSON hoặc chuyển hướng tùy theo yêu cầu
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': flash_category == 'success', 'message': flash_message})
        else:
            flash(flash_message, flash_category)
            return redirect(url_for('content_management.content_dashboard', tab='flashcards'))
    
    # Xử lý lỗi form validation cho AJAX
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest' and request.method == 'POST':
        return jsonify({'success': False, 'errors': form.errors}), 400
    
    # Render template cho modal hoặc trang đầy đủ
    if request.method == 'GET' and request.args.get('is_modal') == 'true':
        return render_template('_add_edit_flashcard_set_bare.html', form=form, title='Chỉnh sửa Bộ thẻ ghi nhớ')
    return render_template('add_edit_flashcard_set.html', form=form, title='Chỉnh sửa Bộ thẻ ghi nhớ')

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
    
    return render_template('flashcard_items.html',
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
        return jsonify({'success': False, 'message': 'Dữ liệu sắp xếp không hợp lệ.'}), 400

    order_map = {}
    try:
        for entry in order_payload:
            item_id = int(entry['item_id'])
            order_value = int(entry['order'])
            order_map[item_id] = order_value
    except (KeyError, TypeError, ValueError):
        return jsonify({'success': False, 'message': 'Định dạng dữ liệu không hợp lệ.'}), 400

    if len(order_map) != len(set(order_map.values())):
        return jsonify({'success': False, 'message': 'Thứ tự mới không hợp lệ.'}), 400

    items = LearningItem.query.filter(
        LearningItem.container_id == set_id,
        LearningItem.item_type == 'FLASHCARD',
        LearningItem.item_id.in_(order_map.keys())
    ).all()

    if len(items) != len(order_map):
        return jsonify({'success': False, 'message': 'Không tìm thấy một số thẻ cần sắp xếp.'}), 404

    for item in items:
        new_position = order_map.get(item.item_id)
        if new_position is not None:
            item.order_in_container = new_position

    db.session.commit()
    return jsonify({'success': True, 'message': 'Thứ tự thẻ đã được cập nhật.'})


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
        return jsonify({'success': False, 'message': 'Bạn không có quyền thực hiện thao tác này.'}), 403

    if item_id:
        flashcard_item = LearningItem.query.filter_by(
            item_id=item_id,
            container_id=set_id,
            item_type='FLASHCARD'
        ).first()
        if not flashcard_item:
            return jsonify({'success': False, 'message': 'Không tìm thấy thẻ phù hợp.'}), 404

    payload = request.get_json(silent=True) or {}
    side = (payload.get('side') or 'front').lower()
    query = (payload.get('query') or '').strip()

    if side not in {'front', 'back'}:
        return jsonify({'success': False, 'message': 'Mặt thẻ không hợp lệ.'}), 400

    if not query:
        return jsonify({'success': False, 'message': 'Vui lòng nhập nội dung để tìm kiếm ảnh.'}), 400

    try:
        absolute_path, success, message = image_service.get_cached_or_download_image(query)
        if not success or not absolute_path:
            return jsonify({'success': False, 'message': message or 'Không tìm thấy ảnh phù hợp.'}), 404

        image_folder = _get_media_folders_from_container(flashcard_set).get('image')
        if not image_folder:
            image_folder = _ensure_container_media_folder(flashcard_set, 'image')

        try:
            os.makedirs(os.path.join(current_app.static_folder, image_folder), exist_ok=True)
        except OSError as folder_exc:
            current_app.logger.error(
                "Không thể tạo thư mục ảnh %s: %s", image_folder, folder_exc, exc_info=True
            )
            return jsonify({'success': False, 'message': 'Không thể chuẩn bị thư mục lưu ảnh.'}), 500

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
            return jsonify({'success': False, 'message': 'Không thể lưu file ảnh.'}), 500

        stored_value = normalize_media_value_for_storage(filename, image_folder)
        relative_path = build_relative_media_path(stored_value, image_folder)

        if not relative_path:
            return jsonify({'success': False, 'message': 'Không thể xử lý đường dẫn ảnh.'}), 500

        image_url = url_for('static', filename=relative_path)
        return jsonify({
            'success': True,
            'message': 'Đã tìm thấy ảnh minh họa.',
            'relative_path': relative_path,
            'stored_value': stored_value,
            'image_url': image_url
        })
    except Exception as exc:  # pylint: disable=broad-except
        current_app.logger.error(
            "Lỗi khi tìm ảnh minh họa cho bộ thẻ %s: %s", set_id, exc, exc_info=True
        )
        return jsonify({'success': False, 'message': 'Đã xảy ra lỗi khi tìm kiếm ảnh.'}), 500

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
    if request.method == 'GET':
        form.supports_pronunciation.data = 'supports_pronunciation' in container_capabilities
        form.supports_writing.data = 'supports_writing' in container_capabilities
        form.supports_quiz.data = 'supports_quiz' in container_capabilities
        form.supports_essay.data = 'supports_essay' in container_capabilities
        form.supports_listening.data = 'supports_listening' in container_capabilities
        form.supports_speaking.data = 'supports_speaking' in container_capabilities
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
            'supports_pronunciation': bool(form.supports_pronunciation.data),
            'supports_writing': bool(form.supports_writing.data),
            'supports_quiz': bool(form.supports_quiz.data),
            'supports_essay': bool(form.supports_essay.data),
            'supports_listening': bool(form.supports_listening.data),
            'supports_speaking': bool(form.supports_speaking.data),
        }
        if form.ai_prompt.data:
            content_dict['ai_prompt'] = form.ai_prompt.data

        new_item = LearningItem(
            container_id=set_id,
            item_type='FLASHCARD',
            content=content_dict,
            order_in_container=new_order
        )
        db.session.add(new_item)
        db.session.commit() # Lưu thay đổi
        
        # Trả về phản hồi JSON hoặc chuyển hướng tùy theo yêu cầu
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({
                'success': True,
                'message': 'Thẻ mới đã được thêm!',
                'item_id': new_item.item_id
            })
        else:
            flash('Thẻ mới đã được thêm!', 'success')
            return redirect(url_for('.list_flashcard_items', set_id=set_id))
    
    # Xử lý lỗi form validation cho AJAX
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest' and request.method == 'POST':
        return jsonify({'success': False, 'errors': form.errors}), 400
    
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
    }

    # Render template cho modal hoặc trang đầy đủ
    if request.method == 'GET' and request.args.get('is_modal') == 'true':
        return render_template('_add_edit_flashcard_item_bare.html', **context)
    return render_template('add_edit_flashcard_item.html', **context)

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
        flashcard_item.content['supports_pronunciation'] = bool(form.supports_pronunciation.data)
        flashcard_item.content['supports_writing'] = bool(form.supports_writing.data)
        flashcard_item.content['supports_quiz'] = bool(form.supports_quiz.data)
        flashcard_item.content['supports_essay'] = bool(form.supports_essay.data)
        flashcard_item.content['supports_listening'] = bool(form.supports_listening.data)
        flashcard_item.content['supports_speaking'] = bool(form.supports_speaking.data)
        
        if form.ai_prompt.data:
            flashcard_item.content['ai_prompt'] = form.ai_prompt.data
        elif 'ai_prompt' in flashcard_item.content:
            del flashcard_item.content['ai_prompt']

        # Đánh dấu trường JSON đã thay đổi để SQLAlchemy lưu lại
        flag_modified(flashcard_item, "content")
        db.session.commit() # Lưu thay đổi
        
        # Trả về phản hồi JSON hoặc chuyển hướng tùy theo yêu cầu
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({
                'success': True,
                'message': 'Thẻ đã được cập nhật!',
                'item_id': flashcard_item.item_id
            })
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

        form.supports_pronunciation.data = _resolve_flag('supports_pronunciation')
        form.supports_writing.data = _resolve_flag('supports_writing')
        form.supports_quiz.data = _resolve_flag('supports_quiz')
        form.supports_essay.data = _resolve_flag('supports_essay')
        form.supports_listening.data = _resolve_flag('supports_listening')
        form.supports_speaking.data = _resolve_flag('supports_speaking')
        # Gán giá trị `order_in_container` vào form
        form.order_in_container.data = flashcard_item.order_in_container
    
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
    }

    # Render template cho modal hoặc trang đầy đủ
    if request.method == 'GET' and request.args.get('is_modal') == 'true':
        return render_template('_add_edit_flashcard_item_bare.html', **context)
    return render_template('add_edit_flashcard_item.html', **context)


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
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({'success': True, 'message': 'Thẻ đã được xóa.'})
    else:
        flash('Thẻ đã được xóa.', 'success')
        return redirect(url_for('.list_flashcard_items', set_id=set_id))