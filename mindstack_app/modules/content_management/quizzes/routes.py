# File: newmindstack/mindstack_app/modules/content_management/quizzes/routes.py
# Phiên bản: 3.36
# MỤC ĐÍCH: Tích hợp quyền chỉnh sửa vào QuizSession.
# ĐÃ SỬA: Sửa đổi route list_quiz_items để hiển thị đúng nút Sửa.

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
from ..forms import QuizSetForm, QuizItemForm
from ....models import db, LearningContainer, LearningItem, LearningGroup, ContainerContributor, User, UserNote
from ....config import Config
from ....services.config_service import get_runtime_config
import pandas as pd
import tempfile
import os
from mindstack_app.utils.pagination import get_pagination_data
from mindstack_app.utils.search import apply_search_filter
from mindstack_app.utils.excel import extract_info_sheet_mapping, format_info_warnings
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.datavalidation import DataValidation
from mindstack_app.utils.media_paths import (
    normalize_media_folder,
    normalize_media_value_for_storage,
    build_relative_media_path,
)
import copy
import zipfile
import shutil
import re
import io
import math

QUIZ_DATA_COLUMNS = [
    'item_id',
    'order_in_container',
    'question',
    'pre_question_text',
    'option_a',
    'option_b',
    'option_c',
    'option_d',
    'correct_answer_text',
    'guidance',
    'ai_explanation',
    'question_image_file',
    'question_audio_file',
    'ai_prompt',
    'group_id',
    'group_shared_components',
    'group_item_order',
    'action',
]

QUIZ_INFO_KEYS = [
    'title',
    'description',
    'cover_image',
    'tags',
    'is_public',
    'image_base_folder',
    'audio_base_folder',
    'ai_prompt',
]

ACTION_OPTIONS = ['None', 'Update', 'Create', 'Delete', 'Skip']

GROUP_SHARED_COMPONENT_MAP = {
    'question': 'question',
    'pre_question_text': 'pre_question_text',
    'correct_answer': 'correct_answer',
    'explanation': 'explanation',
    'image': 'question_image_file',
    'audio': 'question_audio_file',
    'prompt': 'ai_prompt',
}


def _resolve_correct_answer_letter(content: dict) -> str:
    """Return the answer letter (A-D) even if the stored value is option text."""

    if not isinstance(content, dict):
        return ''

    options = content.get('options') or {}
    raw_answer = content.get('correct_answer') or ''
    normalized_answer = str(raw_answer).strip()
    upper_answer = normalized_answer.upper()

    if upper_answer in {'A', 'B', 'C', 'D'}:
        return upper_answer

    for letter in ('A', 'B', 'C', 'D'):
        option_text = options.get(letter)
        if option_text is None:
            continue
        if normalized_answer and normalized_answer == str(option_text).strip():
            return letter

    return ''


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


def _create_quiz_excel(info_rows, data_rows, *, output_path: Optional[str] = None, readme_rows: Optional[list[tuple[str, str]]] = None):
    info_df = pd.DataFrame(info_rows, columns=['Key', 'Value'])
    if not info_df.empty:
        info_df['Value'] = info_df['Value'].apply(lambda value: '' if value is None else str(value))
    else:
        info_df = pd.DataFrame(columns=['Key', 'Value'])

    data_df = pd.DataFrame(data_rows, columns=QUIZ_DATA_COLUMNS)
    if data_df.empty:
        data_df = pd.DataFrame(columns=QUIZ_DATA_COLUMNS)
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
            _apply_action_dropdown(data_sheet, QUIZ_DATA_COLUMNS)
        if readme_rows:
            readme_df = pd.DataFrame(readme_rows, columns=['Hướng dẫn', 'Chi tiết'])
            readme_df.to_excel(writer, sheet_name='ReadMe', index=False)

    if output_path:
        return output_path

    target.seek(0)
    return target


def _build_sample_quiz_template():
    info_rows = [
        ('title', 'Mẫu bộ Quiz - thay tiêu đề ở đây'),
        ('description', 'Ví dụ ngắn để minh hoạ bộ 3 cột group_id/group_shared_components/group_item_order'),
        ('cover_image', 'Đường dẫn ảnh cover (URL hoặc uploads/...)'),
        ('tags', 'sample,template'),
        ('is_public', 'False'),
        ('image_base_folder', 'quiz/images'),
        ('audio_base_folder', 'quiz/audio'),
        ('ai_prompt', ''),
    ]

    def _row(**kwargs):
        base = {column: '' for column in QUIZ_DATA_COLUMNS}
        base.update(kwargs)
        return base

    data_rows = [
        _row(
            order_in_container=1,
            question='Câu hỏi độc lập (không thuộc group)',
            option_a='Đáp án A',
            option_b='Đáp án B',
            correct_answer_text='A',
            guidance='Giải thích riêng cho câu hỏi này',
            ai_explanation='',
            question_image_file='uploads/quiz/images/question-1.png',
            action='create',
        ),
        _row(
            order_in_container=2,
            question='Bước 1 trong group chung',
            option_a='Lựa chọn 1',
            option_b='Lựa chọn 2',
            correct_answer_text='A',
            guidance='Giải thích chung cho cả group',
            ai_explanation='',
            question_image_file='uploads/quiz/images/shared.png',
            question_audio_file='uploads/quiz/audio/shared.mp3',
            ai_prompt='Gợi ý dùng chung cho cả group',
            group_id=1001,
            group_shared_components='question,pre_question_text,correct_answer,explanation,image,audio,prompt',
            group_item_order=1,
            action='create',
        ),
        _row(
            order_in_container=3,
            question='Bước 2 trong group chung (kế thừa media/prompt)',
            option_a='Lựa chọn 1',
            option_b='Lựa chọn 2',
            correct_answer_text='B',
            ai_explanation='',
            group_id=1001,
            group_shared_components='question,pre_question_text,correct_answer,explanation,image,audio,prompt',
            group_item_order=2,
            action='create',
        ),
    ]

    return info_rows, data_rows


def _build_quiz_readme_rows():
    shared_tokens = ', '.join(sorted(GROUP_SHARED_COMPONENT_MAP.keys()))
    return [
        (
            'Mục đích file',
            'Sử dụng sheet Data để thêm/sửa/xoá câu hỏi; sheet Info để cập nhật thông tin bộ Quiz.',
        ),
        (
            'Cấu trúc bắt buộc',
            'Data phải có option_a, option_b, correct_answer_text. Mỗi dòng (trừ Delete/Skip) cần đủ các cột này.',
        ),
        (
            'group_id',
            'Dùng để gom các câu hỏi thành một nhóm. Có thể là số hoặc chuỗi. Khi trùng group_id/external_id sẽ gộp chung.',
        ),
        (
            'group_shared_components',
            f'Theo danh sách hợp lệ: {shared_tokens}. Có thể ghi nhiều giá trị, ngăn cách bằng dấu phẩy.',
        ),
        (
            'Cách hoạt động shared components',
            'Nhập giá trị một lần ở bất kỳ dòng nào của group; các dòng khác có thể để trống cột tương ứng nếu đã đánh dấu chia sẻ.',
        ),
        (
            'group_item_order',
            'Thứ tự trong cùng group (khác với order_in_container). Có thể để trống nếu không cần sắp xếp nội bộ.',
        ),
        (
            'Hành động',
            "Cột action hỗ trợ: None/Update (mặc định), Create, Delete, Skip. Không phân biệt hoa thường.",
        ),
        (
            'Đường dẫn media',
            "Nếu dùng thư mục cơ sở (image_base_folder/audio_base_folder) trong sheet Info, chỉ cần nhập tên file, hệ thống sẽ tự ghép đường dẫn.",
        ),
    ]


quizzes_bp = Blueprint('content_management_quizzes', __name__,
                        template_folder='templates') # Đã cập nhật đường dẫn template


def _apply_is_public_restrictions(form):
    """Disable public toggle for free users and ensure value stays False."""
    if hasattr(form, 'is_public') and current_user.user_role == 'free':
        form.is_public.data = False
        existing_render_kw = dict(form.is_public.render_kw or {})
        existing_render_kw['disabled'] = True
        form.is_public.render_kw = existing_render_kw


def _has_editor_access(container_id):
    if current_user.user_role == User.ROLE_FREE:
        return False
    return ContainerContributor.query.filter_by(
        container_id=container_id,
        user_id=current_user.user_id,
        permission_level='editor'
    ).first() is not None


def _get_editable_quiz_sets_query(*, exclude_id: Optional[int] = None):
    base_query = LearningContainer.query.filter_by(container_type='QUIZ_SET')

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

def _get_media_folders_from_container(container) -> dict[str, str]:
    if not container:
        return {}
    folders = getattr(container, 'media_folders', {}) or {}
    if folders:
        return dict(folders)
    return {}


def _extract_media_folders(settings_payload) -> dict[str, str]:
    """Return normalized media folder mapping from a settings payload."""

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


def _process_relative_url(url, media_folder: Optional[str] = None):
    """Normalize a user-provided media path before storing it."""
    if url is None:
        return None

    normalized = str(url).strip()
    if not normalized:
        return ''

    return normalize_media_value_for_storage(normalized, media_folder)


def _parse_shared_components(raw_value) -> set[str]:
    if raw_value is None:
        return set()
    tokens = [
        token.strip().lower() for token in str(raw_value).split(',') if token and str(token).strip()
    ]
    return {token for token in tokens if token in GROUP_SHARED_COMPONENT_MAP}


def _build_absolute_media_url(file_path, media_folder: Optional[str] = None):
    if not file_path:
        return None
    try:
        relative_path = build_relative_media_path(file_path, media_folder)
        if not relative_path:
            return None
        if relative_path.startswith(('http://', 'https://')):
            return relative_path
        static_path = relative_path.lstrip('/')
        return url_for('static', filename=static_path)
    except Exception as exc:
        current_app.logger.error(f"Không thể tạo URL tuyệt đối cho media '{file_path}': {exc}")
        return file_path


def _build_ai_settings_from_form(form, existing_settings=None):
    payload = {}
    if isinstance(existing_settings, dict):
        payload.update(existing_settings)

    ai_prompt_value = (getattr(form.ai_prompt, 'data', '') or '').strip()
    if ai_prompt_value:
        payload['custom_prompt'] = ai_prompt_value
    else:
        payload.pop('custom_prompt', None)

    media_folders = {}
    image_folder_value = normalize_media_folder(getattr(getattr(form, 'image_base_folder', None), 'data', None))
    audio_folder_value = normalize_media_folder(getattr(getattr(form, 'audio_base_folder', None), 'data', None))
    if image_folder_value:
        media_folders['image'] = image_folder_value
    if audio_folder_value:
        media_folders['audio'] = audio_folder_value

    if media_folders:
        payload['media_folders'] = media_folders
    else:
        payload.pop('media_folders', None)

    return payload or None


def _slugify_filename(value: str) -> str:
    """Sanitize filenames while keeping the original title readable.

    Only remove characters disallowed by Windows (\\ / : * ? " < > |) and control
    characters. Collapse whitespace, strip trailing dots/spaces, and fall back to a
    safe default if the title becomes empty.
    """

    sanitized = (value or '').strip()
    if not sanitized:
        return 'quiz-set'

    sanitized = re.sub(r'[\\/:*?"<>|]', ' ', sanitized)
    sanitized = re.sub(r'[\0-\x1f]', '', sanitized)
    sanitized = re.sub(r'\s+', ' ', sanitized).strip()
    sanitized = sanitized.strip('. ')

    if not sanitized:
        return 'quiz-set'

    if len(sanitized) > 150:
        sanitized = sanitized[:150].rstrip('. ')

    return sanitized or 'quiz-set'


def _resolve_local_media_path(path_value: str, *, media_folder: Optional[str] = None):
    if not path_value:
        return None

    normalized = str(path_value).strip()
    if not normalized or normalized.startswith(('http://', 'https://')):
        return None

    normalized = normalized.lstrip('/')
    if normalized.startswith('uploads/'):
        normalized = normalized[len('uploads/'):]

    base_static = os.path.join(current_app.root_path, 'static')
    upload_folder = get_runtime_config('UPLOAD_FOLDER', Config.UPLOAD_FOLDER)
    candidates = []

    relative_candidates = [normalized]
    folder_normalized = normalize_media_folder(media_folder)
    if folder_normalized:
        if '/' not in normalized:
            relative_candidates.insert(0, f"{folder_normalized}/{normalized}")
        else:
            relative_candidates.insert(0, normalized)

    for rel_path in relative_candidates:
        if upload_folder:
            candidates.append(os.path.join(upload_folder, rel_path))
        candidates.append(os.path.join(base_static, rel_path))

    for candidate in candidates:
        if candidate and os.path.isfile(candidate):
            return candidate

    return None


def _transfer_media_to_folder(
    value: Optional[str], *, source_folder: Optional[str], target_folder: Optional[str]
):
    """Copy a local media file into the target folder and return the stored value.

    If the value is an absolute/HTTP URL or the target folder is unavailable, the
    original value is returned unchanged.
    """

    if not value or not target_folder:
        return value

    normalized_value = str(value).strip()
    if not normalized_value or normalized_value.startswith(('http://', 'https://')):
        return value

    normalized_target = normalize_media_folder(target_folder)
    if not normalized_target:
        return value

    candidate_paths = [
        _resolve_local_media_path(normalized_value, media_folder=source_folder),
        _resolve_local_media_path(normalized_value, media_folder=target_folder),
        _resolve_local_media_path(normalized_value, media_folder=None),
    ]
    local_path = next((path for path in candidate_paths if path and os.path.isfile(path)), None)
    if not local_path:
        return value

    destination_dir = os.path.join(current_app.static_folder, normalized_target)
    try:
        os.makedirs(destination_dir, exist_ok=True)
    except OSError as exc:
        current_app.logger.error(
            "Không thể chuẩn bị thư mục media %s: %s", destination_dir, exc, exc_info=True
        )
        return value

    filename = os.path.basename(local_path)
    destination_path = os.path.join(destination_dir, filename)

    try:
        if not os.path.exists(destination_path):
            shutil.copy2(local_path, destination_path)
    except OSError as exc:  # pylint: disable=broad-except
        current_app.logger.error(
            "Không thể sao chép media %s sang %s: %s", local_path, destination_path, exc, exc_info=True
        )
        return value

    return normalize_media_value_for_storage(filename, normalized_target)


def _copy_media_into_package(
    original_path: str,
    media_dir: Optional[str],
    existing_map: dict,
    media_subdir: Optional[str] = None,
    media_folder: Optional[str] = None,
    export_mode: str = 'zip',
) -> str:
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

    # Drop uploads prefix if present
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


def _build_quiz_export_payload(
    quiz_set,
    items,
    groups,
    *,
    export_mode: str,
    media_dir: Optional[str],
    media_cache: Optional[dict],
    image_folder: Optional[str],
    audio_folder: Optional[str],
):
    media_cache = media_cache or {}

    ai_settings_payload = quiz_set.ai_settings if hasattr(quiz_set, 'ai_settings') else None
    ai_prompt_value = getattr(quiz_set, 'ai_prompt', None)
    if not ai_prompt_value and isinstance(ai_settings_payload, dict):
        ai_prompt_value = ai_settings_payload.get('custom_prompt', '')

    info_mapping = {
        'title': quiz_set.title or '',
        'description': quiz_set.description or '',
        'cover_image': quiz_set.cover_image or '',
        'tags': quiz_set.tags or '',
        'is_public': 'True' if quiz_set.is_public else 'False',
        'image_base_folder': image_folder or '',
        'audio_base_folder': audio_folder or '',
        'ai_prompt': ai_prompt_value or '',
    }

    info_rows = [
        {'Key': key, 'Value': info_mapping.get(key, '')}
        for key in QUIZ_INFO_KEYS
    ]

    group_shared_tracker: dict[int, set[str]] = {}
    data_rows = []
    for item in items:
        content = item.content or {}
        group = groups.get(item.group_id) if item.group_id else None
        group_content = group.content if group else {}
        shared_components = set()
        if isinstance(group_content, dict):
            shared_components = set(group_content.get('shared_components') or [])

        row = {column: '' for column in QUIZ_DATA_COLUMNS}
        row['item_id'] = item.item_id
        row['order_in_container'] = item.order_in_container if item.order_in_container is not None else ''
        row['question'] = content.get('question') or ''
        row['pre_question_text'] = content.get('pre_question_text') or ''
        options = content.get('options') or {}
        row['option_a'] = options.get('A') or ''
        row['option_b'] = options.get('B') or ''
        row['option_c'] = options.get('C') or ''
        row['option_d'] = options.get('D') or ''
        row['correct_answer_text'] = content.get('correct_answer') or ''
        row['guidance'] = content.get('explanation') or ''
        row['ai_explanation'] = item.ai_explanation or ''

        def _shared_value(token: str, field_name: str, raw_value):
            if not group or token not in shared_components:
                return raw_value
            seen = group_shared_tracker.setdefault(group.group_id, set())
            canonical_value = group_content.get(field_name) or raw_value or ''
            if token in seen:
                return ''
            seen.add(token)
            return canonical_value

        row['question'] = _shared_value('question', 'question', row['question'])
        row['pre_question_text'] = _shared_value('pre_question_text', 'pre_question_text', row['pre_question_text'])
        row['correct_answer_text'] = _shared_value('correct_answer', 'correct_answer', row['correct_answer_text'])
        row['guidance'] = _shared_value('explanation', 'explanation', row['guidance'])
        row['question_image_file'] = _shared_value(
            'image',
            'question_image_file',
            _copy_media_into_package(
                content.get('question_image_file'),
                media_dir,
                media_cache,
                media_subdir='images',
                media_folder=image_folder,
                export_mode=export_mode,
            ) or ''
        )
        row['question_audio_file'] = _shared_value(
            'audio',
            'question_audio_file',
            _copy_media_into_package(
                content.get('question_audio_file'),
                media_dir,
                media_cache,
                media_subdir='audio',
                media_folder=audio_folder,
                export_mode=export_mode,
            ) or ''
        )
        row['ai_prompt'] = _shared_value('prompt', 'ai_prompt', content.get('ai_prompt') or '')

        row['group_id'] = (group_content.get('external_id') if group_content else None) or (group.group_id if group else '')
        if shared_components:
            row['group_shared_components'] = ','.join(sorted(shared_components))
        row['group_item_order'] = content.get('group_item_order') if content.get('group_item_order') is not None else ''

        # [NEW] Export custom data columns
        custom_data = item.custom_data or {}
        for key, value in custom_data.items():
            row[key] = value

        row['action'] = 'None'
        data_rows.append(row)

    return info_rows, data_rows


def _serialize_quiz_item_for_response(item, user_id=None):
    content_copy = copy.deepcopy(item.content or {})
    options = content_copy.get('options') or {}
    content_copy['options'] = {
        'A': options.get('A'),
        'B': options.get('B'),
        'C': options.get('C'),
        'D': options.get('D')
    }

    resolved_correct_answer = _resolve_correct_answer_letter(content_copy)
    if resolved_correct_answer:
        content_copy['correct_answer'] = resolved_correct_answer

    media_folders = _get_media_folders_from_container(item.container if item else None)
    image_folder = media_folders.get('image')
    audio_folder = media_folders.get('audio')

    image_path = content_copy.get('question_image_file')
    if image_path:
        content_copy['question_image_file'] = _build_absolute_media_url(image_path, image_folder)

    audio_path = content_copy.get('question_audio_file')
    if audio_path:
        content_copy['question_audio_file'] = _build_absolute_media_url(audio_path, audio_folder)

    note_content = ''
    if user_id is not None:
        note = UserNote.query.filter_by(user_id=user_id, item_id=item.item_id).first()
        note_content = note.content if note else ''

        group_details = None
        if item.group_id and getattr(item, 'group', None):
            group_content = item.group.content or {}
            group_details = {
                'group_id': item.group_id,
                'external_id': group_content.get('external_id'),
                'shared_components': group_content.get('shared_components') or [],
                'shared_values': {
                    token: group_content.get(field)
                    for token, field in GROUP_SHARED_COMPONENT_MAP.items()
                    if token in (group_content.get('shared_components') or [])
            }
        }

    return {
        'item_id': item.item_id,
        'container_id': item.container_id,
        'content': content_copy,
        'ai_explanation': item.ai_explanation,
        'note_content': note_content,
        'group_id': item.group_id,
        'group_details': group_details
    }

def _update_quiz_from_excel_file(container_id: int, excel_file) -> str:
    """Cập nhật câu hỏi quiz từ file Excel được tải lên."""
    temp_filepath = None
    try:
        quiz_set = LearningContainer.query.get(container_id)

        with tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx') as tmp_file:
            excel_file.save(tmp_file.name)
            temp_filepath = tmp_file.name

        df = pd.read_excel(temp_filepath, sheet_name='Data')

        required_cols = ['option_a', 'option_b', 'correct_answer_text']
        if not all(col in df.columns for col in required_cols):
            raise ValueError(
                "File Excel (sheet 'Data') phải có các cột bắt buộc: option_a, option_b, correct_answer_text."
            )

        info_notices: list[str] = []
        media_overrides: dict[str, str] = {}
        cover_value = None
        info_mapping, info_warnings = extract_info_sheet_mapping(temp_filepath)
        if info_mapping:
            image_folder_override = normalize_media_folder(info_mapping.get('image_base_folder'))
            audio_folder_override = normalize_media_folder(info_mapping.get('audio_base_folder'))
            cover_value = info_mapping.get('cover_image')
            if image_folder_override:
                media_overrides['image'] = image_folder_override
            if audio_folder_override:
                media_overrides['audio'] = audio_folder_override
        if info_warnings:
            info_notices.extend(info_warnings)

        if media_overrides:
            quiz_set.set_media_folders(media_overrides)

        media_folders = _get_media_folders_from_container(quiz_set)
        image_folder = media_folders.get('image')
        audio_folder = media_folders.get('audio')

        if cover_value is not None:
            quiz_set.cover_image = _process_relative_url(str(cover_value), image_folder)

        existing_items = (
            LearningItem.query.filter_by(container_id=container_id, item_type='QUIZ_MCQ')
            .order_by(LearningItem.order_in_container, LearningItem.item_id)
            .all()
        )
        existing_map = {item.item_id: item for item in existing_items}
        existing_groups = {
            group.group_id: group
            for group in LearningGroup.query.filter_by(container_id=container_id).all()
        }
        existing_groups_by_external = {
            (group.content or {}).get('external_id'): group
            for group in existing_groups.values()
            if (group.content or {}).get('external_id') not in (None, '')
        }

        processed_ids = set()
        delete_ids = set()
        ordered_entries = []
        group_cache = {}
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

        def _parse_int(value, row_index, field_name):
            if value is None or value == '':
                return None
            try:
                return int(float(value))
            except (TypeError, ValueError):
                raise ValueError(f"Hàng {row_index}: {field_name} '{value}' không hợp lệ.")

        def _parse_excel_group_id(value, row_index, field_name):
            if value is None:
                return None

            value_str = str(value).strip()
            if value_str in ('', 'nan', 'NaN', 'None'):
                return None

            return value_str

        group_state = {}

        def _normalize_numeric_group_id(raw_value: str):
            try:
                numeric_value = float(raw_value)
            except (TypeError, ValueError):
                return None

            if math.isnan(numeric_value):
                return None
            if numeric_value.is_integer():
                return int(numeric_value)
            return None

        def _get_or_create_group(group_id_value):
            if group_id_value in (None, ''):
                return None

            if group_id_value in group_state:
                return group_state[group_id_value]

            numeric_group_id = _normalize_numeric_group_id(group_id_value)
            existing_group = None
            if numeric_group_id is not None and numeric_group_id in existing_groups:
                existing_group = existing_groups[numeric_group_id]
            elif group_id_value in existing_groups_by_external:
                existing_group = existing_groups_by_external[group_id_value]

            if existing_group:
                content_dict = dict(existing_group.content or {})
                entry = {
                    'group': existing_group,
                    'shared_components': set(content_dict.get('shared_components') or []),
                    'shared_values': {
                        field: content_dict.get(field)
                        for field in GROUP_SHARED_COMPONENT_MAP.values()
                        if content_dict.get(field) is not None
                    },
                    'external_id': content_dict.get('external_id') or group_id_value
                }
                if content_dict.get('external_id') in (None, ''):
                    content_dict['external_id'] = group_id_value
                    existing_group.content = content_dict
                    flag_modified(existing_group, 'content')
                group_state[group_id_value] = entry
                return entry

            new_group = LearningGroup(
                container_id=container_id,
                group_type='PASSAGE',
                content={'external_id': group_id_value},
            )
            db.session.add(new_group)
            db.session.flush()
            entry = {
                'group': new_group,
                'shared_components': set(),
                'shared_values': {},
                'external_id': group_id_value,
            }
            group_state[group_id_value] = entry
            return entry

        for index, row in df.iterrows():
            row_number = index + 2
            item_id_value = _get_cell(row, 'item_id')
            order_value = _get_cell(row, 'order_in_container')
            order_number = _parse_int(order_value, row_number, 'order_in_container') if order_value else None
            if order_number is not None:
                stats['reordered'] += 1

            question_text = _get_cell(row, 'question') or ''
            option_a = _get_cell(row, 'option_a')
            option_b = _get_cell(row, 'option_b')
            option_c = _get_cell(row, 'option_c')
            option_d = _get_cell(row, 'option_d')
            correct_answer = _get_cell(row, 'correct_answer_text')
            group_item_order = _parse_int(_get_cell(row, 'group_item_order'), row_number, 'group_item_order')
            shared_components = _parse_shared_components(_get_cell(row, 'group_shared_components'))
            group_id_value = _parse_excel_group_id(_get_cell(row, 'group_id'), row_number, 'group_id')
            if order_number is None and group_id_value not in (None, ''):
                order_number = index + 1
                stats['reordered'] += 1
            group_entry = _get_or_create_group(group_id_value)
            if group_entry and shared_components:
                group_entry['shared_components'].update(shared_components)

            item_id = None
            if item_id_value:
                item_id = _parse_int(item_id_value, row_number, 'item_id')

            action_value = _normalize_action(_get_cell(row, 'action'), has_item_id=bool(item_id))

            def _has_value_or_shared(token: str, field_name: str, raw_value):
                if raw_value not in (None, ''):
                    return True
                if not group_entry or token not in group_entry['shared_components']:
                    return False
                return group_entry['shared_values'].get(field_name) not in (None, '')

            has_correct_answer = _has_value_or_shared('correct_answer', 'correct_answer', correct_answer)
            if not (option_a and option_b and has_correct_answer) and action_value not in {'delete', 'skip'}:
                raise ValueError(f"Hàng {row_number}: Thiếu option A/B hoặc đáp án đúng.")

            if item_id:
                item = existing_map.get(item_id)
                if not item:
                    raise ValueError(f"Hàng {row_number}: Không tìm thấy câu hỏi với ID {item_id}.")

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

                content_dict = item.content or {}
                content_dict.setdefault('options', {})
                content_dict['options']['A'] = option_a
                content_dict['options']['B'] = option_b
                content_dict['options']['C'] = option_c
                content_dict['options']['D'] = option_d

                def _value_with_group(token: str, field_name: str, raw_value):
                    if not group_entry or token not in group_entry['shared_components']:
                        return raw_value
                    cached_value = group_entry['shared_values'].get(field_name)
                    chosen = raw_value if raw_value not in (None, '') else cached_value
                    if chosen not in (None, ''):
                        group_entry['shared_values'][field_name] = chosen
                    return chosen

                guidance_value = _get_cell(row, 'guidance')
                pre_question_value = _get_cell(row, 'pre_question_text')
                image_value = _get_cell(row, 'question_image_file')
                audio_value = _get_cell(row, 'question_audio_file')
                ai_prompt_value = _get_cell(row, 'ai_prompt')
                ai_explanation_value = _get_cell(row, 'ai_explanation')

                content_dict['question'] = _value_with_group('question', 'question', question_text)
                content_dict['correct_answer'] = _value_with_group('correct_answer', 'correct_answer', correct_answer)
                content_dict['explanation'] = _value_with_group('explanation', 'explanation', guidance_value)
                content_dict['pre_question_text'] = _value_with_group('pre_question_text', 'pre_question_text', pre_question_value)
                image_processed = _process_relative_url(image_value, image_folder) if image_value else None
                audio_processed = _process_relative_url(audio_value, audio_folder) if audio_value else None
                content_dict['question_image_file'] = _value_with_group('image', 'question_image_file', image_processed)
                content_dict['question_audio_file'] = _value_with_group('audio', 'question_audio_file', audio_processed)
                content_dict.pop('ai_explanation', None)

                prompt_value = _value_with_group('prompt', 'ai_prompt', ai_prompt_value)
                if prompt_value:
                    content_dict['ai_prompt'] = prompt_value
                else:
                    content_dict.pop('ai_prompt', None)

                if group_item_order is not None:
                    content_dict['group_item_order'] = group_item_order
                else:
                    content_dict.pop('group_item_order', None)

                item.group_id = group_entry['group'].group_id if group_entry else None
                item.ai_explanation = ai_explanation_value or None

                item.content = content_dict
                flag_modified(item, 'content')

                # Process custom columns
                known_quiz_columns = {
                    'item_id', 'order_in_container', 'action', 'group_id', 'group_item_order', 'group_shared_components',
                    'question', 'pre_question_text', 'correct_answer_text', 'guidance',
                    'option_a', 'option_b', 'option_c', 'option_d',
                    'question_image_file', 'question_audio_file',
                    'ai_prompt', 'ai_explanation'
                }
                custom_cols = [c for c in df.columns if c not in known_quiz_columns]
                custom_dict = item.custom_data or {}
                for col in custom_cols:
                    val = _get_cell(row, col)
                    if val:
                        custom_dict[col] = val
                    elif col in custom_dict:
                        custom_dict.pop(col)
                
                item.custom_data = custom_dict if custom_dict else None
                flag_modified(item, 'custom_data')

                ordered_entries.append({
                    'type': 'existing',
                    'item': item,
                    'order': order_number if order_number is not None else (item.order_in_container or 0),
                    'sequence': index,
                })
                processed_ids.add(item_id)
                stats['updated'] += 1
                if action_value == 'skip':
                    stats['skipped'] += 1
                    continue

                def _value_with_group(token: str, field_name: str, raw_value):
                    if not group_entry or token not in group_entry['shared_components']:
                        return raw_value
                    cached_value = group_entry['shared_values'].get(field_name)
                    chosen = raw_value if raw_value not in (None, '') else cached_value
                    if chosen not in (None, ''):
                        group_entry['shared_values'][field_name] = chosen
                    return chosen

                image_value = _get_cell(row, 'question_image_file')
                audio_value = _get_cell(row, 'question_audio_file')
                ai_prompt_value = _get_cell(row, 'ai_prompt')
                ai_explanation_value = _get_cell(row, 'ai_explanation')
                guidance_value = _get_cell(row, 'guidance')
                pre_question_value = _get_cell(row, 'pre_question_text')

                # Define known columns to separate custom data
                known_quiz_columns = {
                    'item_id', 'order_in_container', 'action', 'group_id', 'group_item_order', 'group_shared_components',
                    'question', 'pre_question_text', 'correct_answer_text', 'guidance',
                    'option_a', 'option_b', 'option_c', 'option_d',
                    'question_image_file', 'question_audio_file',
                    'ai_prompt', 'ai_explanation'
                }
                
                # Identify custom columns
                custom_cols = [c for c in df.columns if c not in known_quiz_columns]
                custom_dict = {}
                for col in custom_cols:
                    val = _get_cell(row, col)
                    if val:
                        custom_dict[col] = val

                new_item = LearningItem(
                    container_id=container_id,
                    item_type='QUIZ_MCQ',
                    content={
                        'question': _value_with_group('question', 'question', question_text),
                        'options': {
                            'A': option_a,
                            'B': option_b,
                            'C': option_c,
                            'D': option_d,
                        },
                        'correct_answer': _value_with_group('correct_answer', 'correct_answer', correct_answer),
                        'explanation': _value_with_group('explanation', 'explanation', guidance_value),
                        'pre_question_text': _value_with_group('pre_question_text', 'pre_question_text', pre_question_value),
                        'question_image_file': _value_with_group('image', 'question_image_file', _process_relative_url(image_value, image_folder) if image_value else None),
                        'question_audio_file': _value_with_group('audio', 'question_audio_file', _process_relative_url(audio_value, audio_folder) if audio_value else None),
                        'ai_prompt': _value_with_group('prompt', 'ai_prompt', ai_prompt_value) if _value_with_group('prompt', 'ai_prompt', ai_prompt_value) else None,
                        'group_item_order': group_item_order if group_item_order is not None else None,
                    },
                    custom_data=custom_dict if custom_dict else None,
                    ai_explanation=ai_explanation_value or None,
                    group_id=group_entry['group'].group_id if group_entry else None,
                    order_in_container=order_number,
                )
                
                # Check order for new items
                ordered_entries.append({
                    'type': 'new',
                    'item': new_item, 
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
            # Handle both existing items and newly created item instances
            item = entry.get('item')
            if item:
                item.order_in_container = next_order
                if entry['type'] == 'new':
                    db.session.add(item)
            else:
                # Fallback for any legacy entry structure (should not happen with new logic)
                current_app.logger.warning("Found entry without item object in ordered_entries")
            
            next_order += 1

        for group_entry in group_state.values():
            group_obj = group_entry['group']
            content_dict = dict(group_obj.content or {})
            if group_entry.get('external_id'):
                content_dict['external_id'] = group_entry['external_id']
            content_dict['shared_components'] = sorted(group_entry['shared_components'])
            for token, field_name in GROUP_SHARED_COMPONENT_MAP.items():
                if token in group_entry['shared_components']:
                    value = group_entry['shared_values'].get(field_name)
                    if value not in (None, ''):
                        content_dict[field_name] = value
            group_obj.content = content_dict
            flag_modified(group_obj, 'content')

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
        return f'Bộ câu hỏi quiz đã được xử lý: {summary_text}.'
    finally:
        if temp_filepath and os.path.exists(temp_filepath):
            os.remove(temp_filepath)


@quizzes_bp.route('/quizzes/process_excel_info', methods=['POST'])
@login_required
def process_excel_info():
    """
    Xử lý file Excel được tải lên để trích xuất thông tin từ sheet 'Info'.
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
            current_app.logger.error(f"Lỗi khi xử lý sheet Info: {e}")
            return jsonify({'success': False, 'message': f'Lỗi đọc file Excel: {e}'}), 500
        finally:
            if temp_filepath and os.path.exists(temp_filepath):
                os.remove(temp_filepath)
    return jsonify({'success': False, 'message': 'File không hợp lệ. Vui lòng chọn file .xlsx'}), 400

@quizzes_bp.route('/quizzes')
@login_required
def list_quiz_sets():
    """
    Hiển thị danh sách các bộ Quiz.
    """
    page = request.args.get('page', 1, type=int)
    search_query = request.args.get('q', '', type=str)
    search_field = request.args.get('search_field', 'all', type=str)

    base_query = LearningContainer.query.filter_by(container_type='QUIZ_SET')
    
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
        
    search_field_map = {
        'title': LearningContainer.title,
        'description': LearningContainer.description,
        'tags': LearningContainer.tags
    }
    
    filtered_query = apply_search_filter(base_query, search_query, search_field_map, search_field)

    pagination = get_pagination_data(filtered_query.order_by(LearningContainer.created_at.desc()), page)
    quiz_sets = pagination.items
    
    for set_item in quiz_sets:
        set_item.item_count = db.session.query(LearningItem).filter_by(
            container_id=set_item.container_id,
            item_type='QUIZ_MCQ'
        ).count()

        creator = getattr(set_item, 'creator', None)
        if creator:
            set_item.creator_display_name = creator.username
        else:
            set_item.creator_display_name = "Không xác định"

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

    template_vars = {
        'quiz_sets': quiz_sets, 
        'pagination': pagination, 
        'search_query': search_query,
        'search_field': search_field,
        'search_field_map': search_field_map
    }

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return render_template('v3/pages/content_management/quizzes/sets/_quiz_sets_list.html', **template_vars)
    else:
        return render_template('v3/pages/content_management/quizzes/sets/quiz_sets.html', **template_vars)


@quizzes_bp.route('/quizzes/<int:set_id>/export', methods=['GET'])
@login_required
def export_quiz_set(set_id):
    """Xuất bộ quiz ra gói zip gồm Excel và media."""
    quiz_set = LearningContainer.query.get_or_404(set_id)

    if current_user.user_role not in {User.ROLE_ADMIN} and quiz_set.creator_user_id != current_user.user_id:
        if current_user.user_role == User.ROLE_FREE or not _has_editor_access(set_id):
            abort(403)

    items = (
        LearningItem.query.filter_by(container_id=set_id, item_type='QUIZ_MCQ')
        .order_by(LearningItem.order_in_container, LearningItem.item_id)
        .all()
    )
    groups = {
        group.group_id: group
        for group in LearningGroup.query.filter_by(container_id=set_id).all()
    }

    media_folders = _get_media_folders_from_container(quiz_set)
    image_folder = media_folders.get('image')
    audio_folder = media_folders.get('audio')

    with tempfile.TemporaryDirectory() as tmp_dir:
        media_dir = os.path.join(tmp_dir, 'uploads')
        os.makedirs(media_dir, exist_ok=True)
        media_cache = {}

        info_rows, data_rows = _build_quiz_export_payload(
            quiz_set,
            items,
            groups,
            export_mode='zip',
            media_dir=media_dir,
            media_cache=media_cache,
            image_folder=image_folder,
            audio_folder=audio_folder,
        )

        excel_filename = f"{_slugify_filename(quiz_set.title)}.xlsx"
        excel_path = os.path.join(tmp_dir, excel_filename)
        _create_quiz_excel(info_rows, data_rows, output_path=excel_path)

        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zipf:
            zipf.write(excel_path, arcname=excel_filename)
            if os.path.isdir(media_dir):
                for root_dir, _, files in os.walk(media_dir):
                    for filename in files:
                        file_path = os.path.join(root_dir, filename)
                        arcname = os.path.relpath(file_path, tmp_dir)
                        zipf.write(file_path, arcname)

        zip_buffer.seek(0)
        download_name = f"{_slugify_filename(quiz_set.title)}.zip"
        return send_file(zip_buffer, as_attachment=True, download_name=download_name, mimetype='application/zip')


@quizzes_bp.route('/quizzes/<int:set_id>/export-excel', methods=['GET'])
@login_required
def export_quiz_set_excel(set_id):
    """Xuất bộ quiz ra file Excel duy nhất, giữ nguyên đường dẫn media."""
    quiz_set = LearningContainer.query.get_or_404(set_id)

    if current_user.user_role not in {User.ROLE_ADMIN} and quiz_set.creator_user_id != current_user.user_id:
        if current_user.user_role == User.ROLE_FREE or not _has_editor_access(set_id):
            abort(403)

    items = (
        LearningItem.query.filter_by(container_id=set_id, item_type='QUIZ_MCQ')
        .order_by(LearningItem.order_in_container, LearningItem.item_id)
        .all()
    )
    groups = {
        group.group_id: group
        for group in LearningGroup.query.filter_by(container_id=set_id).all()
    }

    media_folders = _get_media_folders_from_container(quiz_set)
    image_folder = media_folders.get('image')
    audio_folder = media_folders.get('audio')

    info_rows, data_rows = _build_quiz_export_payload(
        quiz_set,
        items,
        groups,
        export_mode='excel',
        media_dir=None,
        media_cache={},
        image_folder=image_folder,
        audio_folder=audio_folder,
    )

    excel_buffer = _create_quiz_excel(info_rows, data_rows)
    download_name = f"{_slugify_filename(quiz_set.title)}.xlsx"
    return send_file(
        excel_buffer,
        as_attachment=True,
        download_name=download_name,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    )


@quizzes_bp.route('/quizzes/template-excel', methods=['GET'])
@login_required
def download_quiz_template():
    """Tạo nhanh file Excel mẫu (không phụ thuộc bộ quiz cụ thể)."""

    info_rows, data_rows = _build_sample_quiz_template()
    excel_buffer = _create_quiz_excel(
        info_rows,
        data_rows,
        readme_rows=_build_quiz_readme_rows(),
    )
    return send_file(
        excel_buffer,
        as_attachment=True,
        download_name='quiz_template.xlsx',
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    )


@quizzes_bp.route('/quizzes/<int:set_id>/manage-excel', methods=['GET', 'POST'])
@login_required
def manage_quiz_excel(set_id):
    """Trang quản lý import/export Excel cho bộ quiz."""
    quiz_set = LearningContainer.query.get_or_404(set_id)

    if current_user.user_role != User.ROLE_ADMIN and quiz_set.creator_user_id != current_user.user_id:
        abort(403)

    if request.method == 'POST':
        uploaded_file = request.files.get('excel_file')
        if not uploaded_file or uploaded_file.filename == '':
            flash('Vui lòng chọn file Excel (.xlsx) để nhập.', 'danger')
            return redirect(url_for('content_management.content_management_quizzes.manage_quiz_excel', set_id=set_id))
        if not uploaded_file.filename.lower().endswith('.xlsx'):
            flash('Định dạng file không hợp lệ. Vui lòng chọn file .xlsx.', 'danger')
            return redirect(url_for('content_management.content_management_quizzes.manage_quiz_excel', set_id=set_id))

        try:
            message = _update_quiz_from_excel_file(set_id, uploaded_file)
            db.session.commit()
            flash(message, 'success')
        except Exception as exc:  # pylint: disable=broad-except
            db.session.rollback()
            flash(f'Lỗi khi xử lý: {exc}', 'danger')

        return redirect(url_for('content_management.content_management_quizzes.manage_quiz_excel', set_id=set_id))

    export_excel_url = url_for('content_management.content_management_quizzes.export_quiz_set_excel', set_id=set_id)
    template_excel_url = url_for('content_management.content_management_quizzes.download_quiz_template')
    export_zip_url = url_for('content_management.content_management_quizzes.export_quiz_set', set_id=set_id)
    item_count = LearningItem.query.filter_by(container_id=set_id, item_type='QUIZ_MCQ').count()
    return render_template(
        'v3/pages/content_management/quizzes/excel/manage_quiz_excel.html',
        quiz_set=quiz_set,
        export_excel_url=export_excel_url,
        template_excel_url=template_excel_url,
        export_zip_url=export_zip_url,
        item_count=item_count,
    )


@quizzes_bp.route('/quizzes/add', methods=['GET', 'POST'])
@login_required
def add_quiz_set():
    """
    Thêm một bộ Quiz mới.
    """
    form = QuizSetForm()
    template_excel_url = url_for('content_management.content_management_quizzes.download_quiz_template')
    _apply_is_public_restrictions(form)
    if form.validate_on_submit():
        flash_message = ''
        flash_category = ''
        temp_filepath = None
        try:
            ai_settings_payload = _build_ai_settings_from_form(form)
            media_folders = _extract_media_folders(ai_settings_payload)
            image_folder = media_folders.get('image')
            audio_folder = media_folders.get('audio')
            cover_image_value = _process_relative_url(form.cover_image.data, image_folder)
            new_set = LearningContainer(
                creator_user_id=current_user.user_id,
                container_type='QUIZ_SET',
                title=form.title.data,
                description=form.description.data,
                cover_image=cover_image_value,
                tags=form.tags.data,
                is_public=False if current_user.user_role == 'free' else form.is_public.data,
                ai_settings=ai_settings_payload,
            )
            if media_folders:
                new_set.set_media_folders(media_folders)
            db.session.add(new_set)
            db.session.flush()

            if form.excel_file.data and form.excel_file.data.filename != '':
                excel_file = form.excel_file.data
                with tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx') as tmp_file:
                    excel_file.save(tmp_file.name)
                    temp_filepath = tmp_file.name
                info_notices: list[str] = []
                media_overrides: dict[str, str] = {}
                cover_image_override = cover_image_value
                info_mapping, info_warnings = extract_info_sheet_mapping(temp_filepath)
                if info_mapping:
                    image_folder_override = normalize_media_folder(info_mapping.get('image_base_folder'))
                    audio_folder_override = normalize_media_folder(info_mapping.get('audio_base_folder'))
                    cover_image_override = info_mapping.get('cover_image', cover_image_override)
                    if image_folder_override:
                        media_overrides['image'] = image_folder_override
                    if audio_folder_override:
                        media_overrides['audio'] = audio_folder_override
                if info_warnings:
                    info_notices.extend(info_warnings)

                if media_overrides:
                    new_set.set_media_folders(media_overrides)
                    image_folder = media_overrides.get('image') or image_folder
                    audio_folder = media_overrides.get('audio') or audio_folder
                if cover_image_override is not None:
                    new_set.cover_image = _process_relative_url(str(cover_image_override), image_folder)

                df = pd.read_excel(temp_filepath, sheet_name='Data')

                def _parse_excel_int(value, row_index, field_name):
                    if value is None or pd.isna(value):
                        return None
                    value_str = str(value).strip()
                    if value_str == '' or value_str.lower() == 'nan':
                        return None
                    try:
                        return int(float(value_str))
                    except (TypeError, ValueError):
                        raise ValueError(
                            f"Hàng {row_index}: {field_name} '{value}' không hợp lệ."
                        )

                def _parse_excel_group_id(value, row_index, field_name):
                    """Chấp nhận mọi giá trị chuỗi (hoặc số) cho group_id."""
                    if value is None or pd.isna(value):
                        return None

                    value_str = str(value).strip()
                    if value_str == '' or value_str.lower() == 'nan':
                        return None

                    try:
                        numeric_value = float(value)
                        if math.isnan(numeric_value):
                            return None
                        if numeric_value.is_integer():
                            return str(int(numeric_value))
                    except (TypeError, ValueError):
                        pass

                    return value_str

                group_state = {}
                items_added_count = 0

                def _get_or_create_group(group_id_value):
                    if group_id_value in (None, ''):
                        return None
                    if group_id_value in group_state:
                        return group_state[group_id_value]

                    new_group = LearningGroup(
                        container_id=new_set.container_id,
                        group_type='PASSAGE',
                        content={'external_id': group_id_value},
                    )
                    db.session.add(new_group)
                    db.session.flush()
                    entry = {
                        'group': new_group,
                        'shared_components': set(),
                        'shared_values': {},
                        'external_id': group_id_value,
                    }
                    group_state[group_id_value] = entry
                    return entry

                for index, row in df.iterrows():
                    row_number = index + 2  # Bắt đầu từ hàng 2 trong Excel (sau tiêu đề)

                    option_a = str(row['option_a']) if 'option_a' in df.columns and pd.notna(row['option_a']) else None
                    option_b = str(row['option_b']) if 'option_b' in df.columns and pd.notna(row['option_b']) else None
                    correct_answer = str(row['correct_answer_text']) if 'correct_answer_text' in df.columns and pd.notna(row['correct_answer_text']) else None

                    question_text = str(row['question']) if 'question' in df.columns and pd.notna(row['question']) else ''

                    group_id_value = _parse_excel_group_id(row.get('group_id'), row_number, 'group_id')
                    group_item_order = _parse_excel_int(row.get('group_item_order'), row_number, 'group_item_order')
                    shared_components = _parse_shared_components(row.get('group_shared_components'))
                    group_entry = _get_or_create_group(group_id_value)
                    if group_entry and shared_components:
                        group_entry['shared_components'].update(shared_components)

                    def _has_value_or_shared(token: str, field_name: str, raw_value):
                        if raw_value not in (None, ''):
                            return True
                        if not group_entry or token not in group_entry['shared_components']:
                            return False
                        return group_entry['shared_values'].get(field_name) not in (None, '')

                    has_correct_answer = _has_value_or_shared('correct_answer', 'correct_answer', correct_answer)
                    if not (option_a and option_b and has_correct_answer):
                        current_app.logger.warning(
                            f"Bỏ qua hàng {index + 2} trong Excel: Thiếu thông tin cốt lõi (option_a, option_b, correct_answer_text)."
                        )
                        continue

                    def _value_with_group(token: str, field_name: str, raw_value):
                        if not group_entry or token not in group_entry['shared_components']:
                            return raw_value
                        cached_value = group_entry['shared_values'].get(field_name)
                        chosen = raw_value if raw_value not in (None, '') else cached_value
                        if chosen not in (None, ''):
                            group_entry['shared_values'][field_name] = chosen
                        return chosen

                    item_image_file = str(row['question_image_file']) if 'question_image_file' in df.columns and pd.notna(row['question_image_file']) else None
                    item_audio_file = str(row['question_audio_file']) if 'question_audio_file' in df.columns and pd.notna(row['question_audio_file']) else None
                    item_ai_prompt = str(row['ai_prompt']) if 'ai_prompt' in df.columns and pd.notna(row['ai_prompt']) else None
                    item_guidance = str(row['guidance']) if 'guidance' in df.columns and pd.notna(row['guidance']) else None
                    item_pre_text = str(row['pre_question_text']) if 'pre_question_text' in df.columns and pd.notna(row['pre_question_text']) else None

                    image_processed = _process_relative_url(item_image_file, image_folder) if item_image_file else None
                    audio_processed = _process_relative_url(item_audio_file, audio_folder) if item_audio_file else None

                    question_value = _value_with_group('question', 'question', question_text)
                    pre_question_shared = _value_with_group('pre_question_text', 'pre_question_text', item_pre_text)
                    correct_answer_value = _value_with_group('correct_answer', 'correct_answer', correct_answer)

                    item_content = {
                        'question': question_value,
                        'options': {
                            'A': option_a, 'B': option_b,
                            'C': str(row['option_c']) if 'option_c' in df.columns and pd.notna(row['option_c']) else None,
                            'D': str(row['option_d']) if 'option_d' in df.columns and pd.notna(row['option_d']) else None
                        },
                        'correct_answer': correct_answer_value,
                        'explanation': _value_with_group('explanation', 'explanation', item_guidance),
                        'pre_question_text': pre_question_shared,
                        'question_image_file': _value_with_group('image', 'question_image_file', image_processed),
                        'question_audio_file': _value_with_group('audio', 'question_audio_file', audio_processed),
                    }
                    prompt_value = _value_with_group('prompt', 'ai_prompt', item_ai_prompt)
                    if prompt_value:
                        item_content['ai_prompt'] = prompt_value
                    if group_item_order is not None:
                        item_content['group_item_order'] = group_item_order

                    new_item = LearningItem(
                        container_id=new_set.container_id,
                        group_id=group_entry['group'].group_id if group_entry else None,
                        item_type='QUIZ_MCQ',
                        content=item_content,
                        order_in_container=row_number - 1
                    )
                    db.session.add(new_item)
                    items_added_count += 1

                for group_entry in group_state.values():
                    group_obj = group_entry['group']
                    content_dict = dict(group_obj.content or {})
                    if group_entry.get('external_id'):
                        content_dict['external_id'] = group_entry['external_id']
                    content_dict['shared_components'] = sorted(group_entry['shared_components'])
                    for token, field_name in GROUP_SHARED_COMPONENT_MAP.items():
                        if token in group_entry['shared_components']:
                            value = group_entry['shared_values'].get(field_name)
                            if value not in (None, ''):
                                content_dict[field_name] = value
                    group_obj.content = content_dict
                    flag_modified(group_obj, 'content')
                flash_message = f'Bộ câu hỏi và {items_added_count} câu hỏi từ Excel đã được tạo thành công!'
                if info_notices:
                    flash_message += ' Lưu ý: ' + format_info_warnings(info_notices)
                flash_category = 'success'
            else:
                flash_message = 'Bộ câu hỏi mới đã được tạo thành công!'
                flash_category = 'success'
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"LỖI XẢY RA khi thêm bộ quiz hoặc xử lý Excel: {e}", exc_info=True)
            flash_message = f'Lỗi khi xử lý: {str(e)}'
            flash_category = 'danger'
        finally:
            if temp_filepath and os.path.exists(temp_filepath):
                os.remove(temp_filepath)
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': flash_category == 'success', 'message': flash_message})
        else:
            flash(flash_message, flash_category)
            return redirect(url_for('content_management.content_dashboard', tab='quizzes'))
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest' and request.method == 'POST':
        return jsonify({'success': False, 'errors': form.errors}), 400
    
    if request.method == 'GET' and request.args.get('is_modal') == 'true':
        return render_template(
            'v3/pages/content_management/quizzes/sets/_add_edit_quiz_set_bare.html',
            form=form,
            title='Thêm Bộ câu hỏi mới',
            template_excel_url=template_excel_url,
            form_action=request.path,
        )
    return render_template(
        'v3/pages/content_management/quizzes/sets/add_edit_quiz_set.html',
        form=form,
        title='Thêm Bộ câu hỏi mới',
        template_excel_url=template_excel_url,
        form_action=request.path,
    )

@quizzes_bp.route('/quizzes/edit/<int:set_id>', methods=['GET', 'POST'])
@login_required
def edit_quiz_set(set_id):
    """
    Chỉnh sửa một bộ Quiz hiện có.
    """
    quiz_set = LearningContainer.query.get_or_404(set_id)
    if current_user.user_role != 'admin' and quiz_set.creator_user_id != current_user.user_id:
        abort(403)
    
    form = QuizSetForm(obj=quiz_set)
    _apply_is_public_restrictions(form)
    if request.method == 'GET':
        ai_prompt_value = getattr(quiz_set, 'ai_prompt', None)
        ai_settings_payload = quiz_set.ai_settings if hasattr(quiz_set, 'ai_settings') else None
        if not ai_prompt_value and isinstance(ai_settings_payload, dict):
            ai_prompt_value = ai_settings_payload.get('custom_prompt', '')
        form.ai_prompt.data = ai_prompt_value or ''

        media_folders = _get_media_folders_from_container(quiz_set)
        form.image_base_folder.data = media_folders.get('image')
        form.audio_base_folder.data = media_folders.get('audio')

    editable_set_ids = [
        cid
        for (cid,) in (
            _get_editable_quiz_sets_query()
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
        flash_message = 'Bộ câu hỏi đã được cập nhật!'
        flash_category = 'success'
        try:
            media_folders = _get_media_folders_from_container(quiz_set)
            image_folder = media_folders.get('image')
            quiz_set.title = form.title.data
            quiz_set.description = form.description.data
            quiz_set.cover_image = _process_relative_url(form.cover_image.data, image_folder)
            quiz_set.tags = form.tags.data
            quiz_set.is_public = False if current_user.user_role == 'free' else form.is_public.data
            quiz_set.ai_settings = _build_ai_settings_from_form(form, quiz_set.ai_settings)

            if form.excel_file.data and form.excel_file.data.filename != '':
                flash_message = _update_quiz_from_excel_file(set_id, form.excel_file.data)

            db.session.commit()
        except Exception as exc:
            db.session.rollback()
            current_app.logger.error(f"Lỗi khi cập nhật bộ quiz: {exc}", exc_info=True)
            flash_message = f'Lỗi khi xử lý: {exc}'
            flash_category = 'danger'

        flash(flash_message, flash_category)
        return redirect(url_for('content_management.content_dashboard', tab='quizzes'))
    
    if request.method == 'GET' and request.args.get('is_modal') == 'true':
        return render_template(
            'v3/pages/content_management/quizzes/sets/_add_edit_quiz_set_bare.html',
            form=form,
            title='Sửa Bộ câu hỏi',
            quiz_set=quiz_set,
            previous_set_id=previous_set_id,
            next_set_id=next_set_id,
            form_action=request.path,
        )
    return render_template(
        'v3/pages/content_management/quizzes/sets/add_edit_quiz_set.html',
        form=form,
        title='Sửa Bộ câu hỏi',
        quiz_set=quiz_set,
        previous_set_id=previous_set_id,
        next_set_id=next_set_id,
        form_action=request.path,
    )

@quizzes_bp.route('/quizzes/delete/<int:set_id>', methods=['POST'])
@login_required
def delete_quiz_set(set_id):
    """
    Xóa một bộ Quiz.
    """
    quiz_set = LearningContainer.query.get_or_404(set_id)
    if current_user.user_role != 'admin' and quiz_set.creator_user_id != current_user.user_id:
        abort(403)
    
    db.session.delete(quiz_set)
    db.session.commit()
    
    flash('Bộ câu hỏi đã được xóa thành công!', 'success')
    return redirect(url_for('content_management.content_dashboard', tab='quizzes'))

@quizzes_bp.route('/quizzes/<int:set_id>/items')
@login_required
def list_quiz_items(set_id):
    """
    Hiển thị danh sách các câu hỏi trong một bộ Quiz cụ thể.
    """
    quiz_set = LearningContainer.query.get_or_404(set_id)
    if not quiz_set.is_public and current_user.user_role != 'admin' and quiz_set.creator_user_id != current_user.user_id:
        abort(403)
    
    page = request.args.get('page', 1, type=int)
    search_query = request.args.get('q', '', type=str)
    search_field = request.args.get('search_field', 'all', type=str)

    base_query = LearningItem.query.filter_by(container_id=quiz_set.container_id, item_type='QUIZ_MCQ')
    
    item_search_field_map = {
        'question': LearningItem.content['question'],
        'option_a': LearningItem.content['options']['A'],
        'option_b': LearningItem.content['options']['B'],
        'option_c': LearningItem.content['options']['C'],
        'option_d': LearningItem.content['options']['D'],
        'correct_answer': LearningItem.content['correct_answer'],
        'guidance': LearningItem.content['explanation'],
        'pre_question_text': LearningItem.content['pre_question_text'],
        'question_image_file': LearningItem.content['question_image_file'],
        'question_audio_file': LearningItem.content['question_audio_file'],
        'ai_prompt': LearningItem.content['ai_prompt'],
        'group_item_order': LearningItem.content['group_item_order'],
    }

    base_query = apply_search_filter(base_query, search_query, item_search_field_map, search_field)

    pagination = get_pagination_data(base_query.order_by(LearningItem.order_in_container), page)
    quiz_items = pagination.items

    for item in quiz_items:
        item.resolved_correct_answer = _resolve_correct_answer_letter(item.content)

    can_edit = (current_user.user_role == 'admin' or quiz_set.creator_user_id == current_user.user_id)

    return render_template('v3/pages/content_management/quizzes/items/quiz_items.html',
                           quiz_set=quiz_set,
                           quiz_items=quiz_items,
                           can_edit=can_edit,
                           pagination=pagination,
                           search_query=search_query,
                           search_field=search_field,
                           search_field_map=item_search_field_map
                           )

@quizzes_bp.route('/quizzes/<int:set_id>/items/reorder', methods=['POST'])
@login_required
def reorder_quiz_items(set_id):
    quiz_set = LearningContainer.query.get_or_404(set_id)
    if quiz_set.creator_user_id != current_user.user_id:
        if current_user.user_role != User.ROLE_ADMIN:
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
        LearningItem.item_type == 'QUIZ_MCQ',
        LearningItem.item_id.in_(order_map.keys())
    ).all()

    if len(items) != len(order_map):
        return jsonify({'success': False, 'message': 'Không tìm thấy một số câu hỏi cần sắp xếp.'}), 404

    for item in items:
        new_position = order_map.get(item.item_id)
        if new_position is not None:
            item.order_in_container = new_position

    db.session.commit()
    return jsonify({'success': True, 'message': 'Thứ tự câu hỏi đã được cập nhật.'})

@quizzes_bp.route('/quizzes/<int:set_id>/items/add', methods=['GET', 'POST'])
@login_required
def add_quiz_item(set_id):
    """
    Thêm một câu hỏi mới vào một bộ Quiz cụ thể.
    """
    quiz_set = LearningContainer.query.get_or_404(set_id)
    if current_user.user_role != 'admin' and quiz_set.creator_user_id != current_user.user_id:
        abort(403)

    media_folders = _get_media_folders_from_container(quiz_set)
    image_folder = media_folders.get('image')
    audio_folder = media_folders.get('audio')
    move_targets = (
        _get_editable_quiz_sets_query(exclude_id=set_id)
        .order_by(LearningContainer.title)
        .all()
    )

    form = QuizItemForm()
    if form.validate_on_submit():
        new_order = form.order_in_container.data
        
        if new_order is not None:
            db.session.query(LearningItem).filter(
                LearningItem.container_id == set_id,
                LearningItem.item_type == 'QUIZ_MCQ',
                LearningItem.order_in_container >= new_order
            ).update({
                LearningItem.order_in_container: LearningItem.order_in_container + 1
            })
        else:
            max_order = db.session.query(db.func.max(LearningItem.order_in_container)).filter_by(
                container_id=set_id,
                item_type='QUIZ_MCQ'
            ).scalar()
            new_order = (max_order or 0) + 1
        
        content_dict = {
            'question': form.question.data,
            'options': {
                'A': form.option_a.data, 'B': form.option_b.data,
                'C': form.option_c.data, 'D': form.option_d.data
            },
            'correct_answer': form.correct_answer_text.data,
            'explanation': form.guidance.data,
            'pre_question_text': form.pre_question_text.data,
            'question_image_file': _process_relative_url(form.question_image_file.data, image_folder),
            'question_audio_file': _process_relative_url(form.question_audio_file.data, audio_folder),
            'audio_transcript': form.audio_transcript.data
        }
        if form.ai_prompt.data:
            content_dict['ai_prompt'] = form.ai_prompt.data
        if form.group_item_order.data is not None:
            content_dict['group_item_order'] = form.group_item_order.data

        target_group = None
        shared_components = _parse_shared_components(form.group_shared_components.data)
        if form.group_id.data:
            target_group = LearningGroup.query.get(form.group_id.data)
            if not target_group:
                target_group = LearningGroup(
                    container_id=set_id,
                    group_type='PASSAGE',
                    content={}
                )
                db.session.add(target_group)
                db.session.flush()
            group_content = dict(target_group.content or {})
            if shared_components:
                group_content['shared_components'] = sorted(shared_components)
                for token, field_name in GROUP_SHARED_COMPONENT_MAP.items():
                    if token in shared_components and content_dict.get(field_name) not in (None, ''):
                        group_content[field_name] = content_dict.get(field_name)
            target_group.content = group_content
            flag_modified(target_group, 'content')

        new_item = LearningItem(
            container_id=set_id,
            group_id=target_group.group_id if target_group else None,
            item_type='QUIZ_MCQ',
            content=content_dict,
            order_in_container=new_order
        )
        db.session.add(new_item)
        db.session.commit()
        flash('Câu hỏi mới đã được thêm!', 'success')
        return redirect(url_for('.list_quiz_items', set_id=set_id))
    
    preview_image_url = ''
    if getattr(form.question_image_file, 'data', None):
        preview_image_url = _build_absolute_media_url(form.question_image_file.data, image_folder) or ''
    preview_audio_url = ''
    if getattr(form.question_audio_file, 'data', None):
        preview_audio_url = _build_absolute_media_url(form.question_audio_file.data, audio_folder) or ''

    template_context = {
        'form': form,
        'quiz_set': quiz_set,
        'title': 'Thêm Câu hỏi',
        'image_base_folder': image_folder or '',
        'audio_base_folder': audio_folder or '',
        'image_preview_url': preview_image_url,
        'audio_preview_url': preview_audio_url,
        'move_targets': [],
        'previous_item_id': None,
        'next_item_id': None,
        'is_modal_view': request.args.get('is_modal') == 'true',
    }

    if request.method == 'GET' and request.args.get('is_modal') == 'true':
        return render_template('v3/pages/content_management/quizzes/items/_add_edit_quiz_item_bare.html', **template_context)
    return render_template('v3/pages/content_management/quizzes/items/add_edit_quiz_item.html', **template_context)

@quizzes_bp.route('/quizzes/<int:set_id>/items/edit/<int:item_id>', methods=['GET', 'POST'])
@login_required
def edit_quiz_item(set_id, item_id):
    """
    Chỉnh sửa một câu hỏi hiện có trong một bộ Quiz cụ thể.
    """
    quiz_item = LearningItem.query.get_or_404(item_id)
    quiz_set = LearningContainer.query.get_or_404(set_id)
    if current_user.user_role != 'admin' and quiz_set.creator_user_id != current_user.user_id:
        abort(403)

    media_folders = _get_media_folders_from_container(quiz_set)
    image_folder = media_folders.get('image')
    audio_folder = media_folders.get('audio')

    move_targets = (
        _get_editable_quiz_sets_query(exclude_id=set_id)
        .order_by(LearningContainer.title)
        .all()
    )

    current_order = quiz_item.order_in_container if quiz_item.order_in_container is not None else -1

    previous_item = (
        LearningItem.query.filter(
            LearningItem.container_id == set_id,
            LearningItem.item_type == 'QUIZ_MCQ',
            LearningItem.order_in_container < current_order,
        )
        .order_by(LearningItem.order_in_container.desc())
        .first()
    )
    next_item = (
        LearningItem.query.filter(
            LearningItem.container_id == set_id,
            LearningItem.item_type == 'QUIZ_MCQ',
            LearningItem.order_in_container > current_order,
        )
        .order_by(LearningItem.order_in_container.asc())
        .first()
    )

    form = QuizItemForm()
    if request.method == 'GET':
        form.question.data = quiz_item.content.get('question')
        form.pre_question_text.data = quiz_item.content.get('pre_question_text')
        form.option_a.data = quiz_item.content.get('options', {}).get('A')
        form.option_b.data = quiz_item.content.get('options', {}).get('B')
        form.option_c.data = quiz_item.content.get('options', {}).get('C')
        form.option_d.data = quiz_item.content.get('options', {}).get('D')
        form.correct_answer_text.data = _resolve_correct_answer_letter(quiz_item.content) or quiz_item.content.get('correct_answer')
        form.guidance.data = quiz_item.content.get('explanation')
        form.question_image_file.data = quiz_item.content.get('question_image_file')
        form.question_audio_file.data = quiz_item.content.get('question_audio_file')
        form.audio_transcript.data = quiz_item.content.get('audio_transcript')
        form.ai_explanation.data = quiz_item.ai_explanation
        form.ai_prompt.data = quiz_item.content.get('ai_prompt')
        form.order_in_container.data = quiz_item.order_in_container
        form.group_id.data = quiz_item.group_id
        form.group_item_order.data = quiz_item.content.get('group_item_order')
        group_content = quiz_item.group.content if quiz_item.group else {}
        if isinstance(group_content, dict):
            form.group_shared_components.data = ','.join(group_content.get('shared_components') or [])

    if form.validate_on_submit():
        old_order = quiz_item.order_in_container
        new_order = form.order_in_container.data

        if new_order is not None and new_order != old_order:
            if new_order > old_order:
                db.session.query(LearningItem).filter(
                    LearningItem.container_id == set_id,
                    LearningItem.item_type == 'QUIZ_MCQ',
                    LearningItem.order_in_container > old_order,
                    LearningItem.order_in_container <= new_order
                ).update({
                    LearningItem.order_in_container: LearningItem.order_in_container - 1
                })
            else:
                db.session.query(LearningItem).filter(
                    LearningItem.container_id == set_id,
                    LearningItem.item_type == 'QUIZ_MCQ',
                    LearningItem.order_in_container >= new_order,
                    LearningItem.order_in_container < old_order
                ).update({
                    LearningItem.order_in_container: LearningItem.order_in_container + 1
                })
            quiz_item.order_in_container = new_order
        
        quiz_item.content['question'] = form.question.data
        quiz_item.content['pre_question_text'] = form.pre_question_text.data
        quiz_item.content.setdefault('options', {})
        quiz_item.content['options']['A'] = form.option_a.data
        quiz_item.content['options']['B'] = form.option_b.data
        quiz_item.content['options']['C'] = form.option_c.data
        quiz_item.content['options']['D'] = form.option_d.data
        quiz_item.content['correct_answer'] = form.correct_answer_text.data
        quiz_item.content['explanation'] = form.guidance.data
        quiz_item.content['question_image_file'] = _process_relative_url(form.question_image_file.data, image_folder)
        quiz_item.content['question_audio_file'] = _process_relative_url(form.question_audio_file.data, audio_folder)
        quiz_item.content['audio_transcript'] = form.audio_transcript.data
        quiz_item.ai_explanation = form.ai_explanation.data

        if form.ai_prompt.data:
            quiz_item.content['ai_prompt'] = form.ai_prompt.data
        elif 'ai_prompt' in quiz_item.content:
            del quiz_item.content['ai_prompt']

        if form.group_item_order.data is not None:
            quiz_item.content['group_item_order'] = form.group_item_order.data
        elif 'group_item_order' in quiz_item.content:
            del quiz_item.content['group_item_order']

        target_group = None
        shared_components = _parse_shared_components(form.group_shared_components.data)
        if form.group_id.data:
            target_group = LearningGroup.query.get(form.group_id.data)
            if not target_group:
                target_group = LearningGroup(
                    container_id=set_id,
                    group_type='PASSAGE',
                    content={},
                )
                db.session.add(target_group)
                db.session.flush()
            group_content = dict(target_group.content or {})
            if shared_components:
                group_content['shared_components'] = sorted(shared_components)
                for token, field_name in GROUP_SHARED_COMPONENT_MAP.items():
                    if token in shared_components and quiz_item.content.get(field_name) not in (None, ''):
                        group_content[field_name] = quiz_item.content.get(field_name)
            target_group.content = group_content
            flag_modified(target_group, 'content')
            quiz_item.group_id = target_group.group_id
        else:
            quiz_item.group_id = None

        flag_modified(quiz_item, "content")
        db.session.commit()
        success_message = 'Câu hỏi đã được cập nhật!'
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            item_payload = _serialize_quiz_item_for_response(quiz_item, current_user.user_id)
            return jsonify({'success': True, 'message': success_message, 'data': item_payload})
        flash(success_message, 'success')
        return redirect(url_for('.list_quiz_items', set_id=set_id))

    if request.method == 'POST' and request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({'success': False, 'message': 'Dữ liệu không hợp lệ.', 'errors': form.errors}), 400

    preview_image_url = ''
    if getattr(form.question_image_file, 'data', None):
        preview_image_url = _build_absolute_media_url(form.question_image_file.data, image_folder) or ''
    preview_audio_url = ''
    if getattr(form.question_audio_file, 'data', None):
        preview_audio_url = _build_absolute_media_url(form.question_audio_file.data, audio_folder) or ''

    template_context = {
        'form': form,
        'quiz_set': quiz_set,
        'quiz_item': quiz_item,
        'title': 'Chỉnh sửa Câu hỏi',
        'image_base_folder': image_folder or '',
        'audio_base_folder': audio_folder or '',
        'image_preview_url': preview_image_url,
        'audio_preview_url': preview_audio_url,
        'move_targets': move_targets,
        'previous_item_id': previous_item.item_id if previous_item else None,
        'next_item_id': next_item.item_id if next_item else None,
        'is_modal_view': request.args.get('is_modal') == 'true',
    }

    if request.method == 'GET' and request.args.get('is_modal') == 'true':
        return render_template('items/_add_edit_quiz_item_bare.html', **template_context)
    return render_template('items/add_edit_quiz_item.html', **template_context)


@quizzes_bp.route('/quizzes/<int:set_id>/items/<int:item_id>/move', methods=['POST'])
@login_required
def move_quiz_item(set_id, item_id):
    quiz_set = LearningContainer.query.get_or_404(set_id)
    quiz_item = LearningItem.query.filter_by(item_id=item_id, container_id=set_id, item_type='QUIZ_MCQ').first_or_404()

    if current_user.user_role not in {User.ROLE_ADMIN} and quiz_set.creator_user_id != current_user.user_id:
        if current_user.user_role == User.ROLE_FREE or not _has_editor_access(set_id):
            abort(403)

    target_set_id = request.form.get('target_set_id', type=int)
    is_modal_request = request.form.get('is_modal') == 'true'
    if not target_set_id:
        flash('Vui lòng chọn bộ Quiz đích để di chuyển.', 'warning')
        return redirect(url_for('.edit_quiz_item', set_id=set_id, item_id=item_id))

    target_set = LearningContainer.query.filter_by(container_id=target_set_id, container_type='QUIZ_SET').first()
    if not target_set:
        flash('Không tìm thấy bộ Quiz đích.', 'danger')
        return redirect(url_for('.edit_quiz_item', set_id=set_id, item_id=item_id))

    if current_user.user_role not in {User.ROLE_ADMIN} and target_set.creator_user_id != current_user.user_id:
        if current_user.user_role == User.ROLE_FREE or not _has_editor_access(target_set.container_id):
            abort(403)

    if target_set.container_id == set_id:
        flash('Câu hỏi đã nằm trong bộ này.', 'info')
        return redirect(url_for('.edit_quiz_item', set_id=set_id, item_id=item_id))

    source_media_folders = _get_media_folders_from_container(quiz_set)
    target_media_folders = _get_media_folders_from_container(target_set)

    group_id = quiz_item.group_id
    grouped_items = []
    source_group = None
    if group_id:
        grouped_items = (
            LearningItem.query.filter_by(
                container_id=set_id,
                item_type='QUIZ_MCQ',
                group_id=group_id,
            )
            .order_by(LearningItem.order_in_container)
            .all()
        )
        source_group = LearningGroup.query.get(group_id)

    items_to_move = grouped_items or [quiz_item]

    max_moved_order = max((item.order_in_container or 0) for item in items_to_move)
    next_item_after_move = (
        LearningItem.query.filter(
            LearningItem.container_id == set_id,
            LearningItem.item_type == 'QUIZ_MCQ',
            LearningItem.order_in_container > max_moved_order,
        )
        .order_by(LearningItem.order_in_container.asc())
        .first()
    )

    target_group = None
    if source_group:
        target_group = LearningGroup(
            container_id=target_set.container_id,
            group_type=source_group.group_type,
            content=copy.deepcopy(source_group.content or {}),
        )
        db.session.add(target_group)
        db.session.flush()
    elif grouped_items:
        target_group = LearningGroup(
            container_id=target_set.container_id,
            group_type='PASSAGE',
            content={},
        )
        db.session.add(target_group)
        db.session.flush()

    max_order = db.session.query(func.max(LearningItem.order_in_container)).filter_by(
        container_id=target_set.container_id,
        item_type='QUIZ_MCQ'
    ).scalar() or 0

    media_field_map = {
        'question_image_file': 'image',
        'question_audio_file': 'audio',
    }
    next_order = max_order + 1
    for item in items_to_move:
        updated_content = dict(item.content or {})
        for field_name, media_type in media_field_map.items():
            updated_value = _transfer_media_to_folder(
                updated_content.get(field_name),
                source_folder=source_media_folders.get(media_type),
                target_folder=target_media_folders.get(media_type),
            )
            if updated_value is not None:
                updated_content[field_name] = updated_value

        item.container_id = target_set.container_id
        item.group_id = target_group.group_id if target_group else None
        item.order_in_container = next_order
        next_order += 1
        if not target_group:
            updated_content.pop('group_item_order', None)
        item.content = updated_content
        flag_modified(item, 'content')

    remaining_items = (
        LearningItem.query.filter_by(container_id=set_id, item_type='QUIZ_MCQ')
        .order_by(LearningItem.order_in_container)
        .all()
    )
    for index, item in enumerate(remaining_items, start=1):
        if item.order_in_container != index:
            item.order_in_container = index

    db.session.commit()

    moved_count = len(items_to_move)
    flash(
        f"Đã di chuyển {moved_count} câu hỏi sang bộ '{target_set.title}'.",
        'success',
    )
    if next_item_after_move:
        redirect_args = {
            'set_id': set_id,
            'item_id': next_item_after_move.item_id,
        }
        if is_modal_request:
            redirect_args['is_modal'] = 'true'
        return redirect(url_for('.edit_quiz_item', **redirect_args))

    return redirect(url_for('.list_quiz_items', set_id=target_set.container_id))

@quizzes_bp.route('/quizzes/<int:set_id>/items/delete/<int:item_id>', methods=['POST'])
@login_required
def delete_quiz_item(set_id, item_id):
    """
    Xóa một câu hỏi khỏi một bộ Quiz cụ thể.
    """
    quiz_item = LearningItem.query.get_or_404(item_id)
    quiz_set = LearningContainer.query.get_or_404(set_id)
    if current_user.user_role != 'admin' and quiz_set.creator_user_id != current_user.user_id:
        abort(403)
    
    db.session.delete(quiz_item)
    db.session.commit()
    
    flash('Câu hỏi đã được xóa.', 'success')
    return redirect(url_for('.list_quiz_items', set_id=set_id))
