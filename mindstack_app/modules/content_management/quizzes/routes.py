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
from mindstack_app.utils.template_helpers import render_dynamic_template
from flask_login import login_required, current_user
from sqlalchemy import or_, func
from sqlalchemy.orm.attributes import flag_modified
from ..forms import QuizSetForm, QuizItemForm
from mindstack_app.models import db, LearningContainer, LearningItem, LearningGroup, ContainerContributor, User, UserNote
from mindstack_app.core.error_handlers import error_response, success_response
from mindstack_app.config import Config
from mindstack_app.config import Config
from mindstack_app.services.config_service import get_runtime_config
from mindstack_app.services.quiz_config_service import QuizConfigService

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

from .services import QuizExcelService, GROUP_SHARED_COMPONENT_MAP, parse_shared_components

def _parse_shared_components(raw_value):
    return parse_shared_components(raw_value)
















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
        return render_dynamic_template('pages/content_management/quizzes/sets/_quiz_sets_list.html', **template_vars)
    else:
        return render_dynamic_template('pages/content_management/quizzes/sets/quiz_sets.html', **template_vars)


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

        info_rows, data_rows = QuizExcelService.build_quiz_export_payload(
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
        QuizExcelService.create_quiz_excel(info_rows, data_rows, output_path=excel_path)

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

    info_rows, data_rows = QuizExcelService.build_quiz_export_payload(
        quiz_set,
        items,
        groups,
        export_mode='excel',
        media_dir=None,
        media_cache={},
        image_folder=image_folder,
        audio_folder=audio_folder,
    )

    excel_buffer = QuizExcelService.create_quiz_excel(info_rows, data_rows)
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

    info_rows, data_rows = QuizExcelService.build_sample_quiz_template()
    excel_buffer = QuizExcelService.create_quiz_excel(
        info_rows,
        data_rows,
        readme_rows=QuizExcelService.build_quiz_readme_rows(),
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
            message = QuizExcelService.process_import(set_id, uploaded_file)
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
    return render_dynamic_template('pages/content_management/quizzes/excel/manage_quiz_excel.html',
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
                try:
                    message = QuizExcelService.process_import(new_set.container_id, form.excel_file.data)
                    flash_message += " " + message
                    flash_category = 'success'
                except Exception as e:
                    raise e
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
        return render_dynamic_template('pages/content_management/quizzes/sets/_add_edit_quiz_set_bare.html',
            form=form,
            title='Thêm Bộ câu hỏi mới',
            template_excel_url=template_excel_url,
            form_action=request.path,
            quiz_config=QuizConfigService.get_all(),
        )
    return render_dynamic_template('pages/content_management/quizzes/sets/add_edit_quiz_set.html',
        form=form,
        title='Thêm Bộ câu hỏi mới',
        template_excel_url=template_excel_url,
        form_action=request.path,
        quiz_config=QuizConfigService.get_all(),
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

        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            if flash_category == 'danger':
                return error_response(message=flash_message, status_code=500)
            return success_response(message=flash_message)
        
        flash(flash_message, flash_category)
        return redirect(url_for('content_management.content_dashboard', tab='quizzes'))
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest' and request.method == 'POST':
        return jsonify({'success': False, 'errors': form.errors}), 400
    if request.method == 'GET' and request.args.get('is_modal') == 'true':
        return render_dynamic_template('pages/content_management/quizzes/sets/_add_edit_quiz_set_bare.html',
            form=form,
            title='Sửa Bộ câu hỏi',
            quiz_set=quiz_set,
            previous_set_id=previous_set_id,
            next_set_id=next_set_id,
            form_action=request.path,
            quiz_config=QuizConfigService.get_all(),
        )
    return render_dynamic_template('pages/content_management/quizzes/sets/add_edit_quiz_set.html',
        form=form,
        title='Sửa Bộ câu hỏi',
        quiz_set=quiz_set,
        previous_set_id=previous_set_id,
        next_set_id=next_set_id,
        form_action=request.path,
        quiz_config=QuizConfigService.get_all(),
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
        item.resolved_correct_answer = QuizExcelService.resolve_correct_answer_letter(item.content)

    can_edit = (current_user.user_role == 'admin' or quiz_set.creator_user_id == current_user.user_id)

    return render_dynamic_template('pages/content_management/quizzes/items/quiz_items.html',
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
        return render_dynamic_template('pages/content_management/quizzes/items/_add_edit_quiz_item_bare.html', **template_context)
    return render_dynamic_template('pages/content_management/quizzes/items/add_edit_quiz_item.html', **template_context)

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
        form.correct_answer_text.data = QuizExcelService.resolve_correct_answer_letter(quiz_item.content) or quiz_item.content.get('correct_answer')
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
        return render_dynamic_template('pages/content_management/quizzes/items/_add_edit_quiz_item_bare.html', **template_context)
    return render_dynamic_template('pages/content_management/quizzes/items/add_edit_quiz_item.html', **template_context)


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

@quizzes_bp.route('/quizzes/process_excel_info', methods=['POST'])
@login_required
def process_excel_info():
    """
    Trích xuất thông tin từ sheet 'Info' của file Excel Quiz tải lên.
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
            
            # Simple check for Data sheet existence
            try:
                pd.read_excel(temp_filepath, sheet_name='Data', nrows=1)
            except Exception:
                return error_response("File Excel thiếu sheet 'Data'.", 'BAD_REQUEST', 400)

            # Analyze Columns
            column_analysis = QuizExcelService.analyze_column_structure(temp_filepath)

            if not info_data and info_warnings:
                message = format_info_warnings(info_warnings)
                return error_response(message, 'BAD_REQUEST', 400)

            # Normalize keys
            normalized_data = {}
            for k, v in info_data.items():
                clean_key = str(k).strip().lower().replace(' ', '_')
                
                clean_val = v
                if isinstance(v, str):
                    clean_val = v.replace('_x000D_', '\n')
                
                normalized_data[clean_key] = clean_val

            message = 'Đã đọc thông tin từ file Excel.'
            if info_warnings:
                message += ' ' + format_info_warnings(info_warnings)
                
            return success_response(message=message, data={
                'data': normalized_data,
                'analysis': column_analysis
            })
        except Exception as e:
            current_app.logger.error(f"Lỗi khi xử lý sheet Info (Quiz): {e}")
            return error_response(f'Lỗi đọc file Excel: {e}', 'SERVER_ERROR', 500)
        finally:
            if temp_filepath and os.path.exists(temp_filepath):
                os.remove(temp_filepath)
    return error_response('File không hợp lệ. Vui lòng chọn file .xlsx', 'BAD_REQUEST', 400)
