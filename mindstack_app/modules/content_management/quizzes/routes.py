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
from sqlalchemy import or_
from sqlalchemy.orm.attributes import flag_modified
from ..forms import QuizSetForm, QuizItemForm
from ....models import db, LearningContainer, LearningItem, LearningGroup, ContainerContributor, User, UserNote
import pandas as pd
import tempfile
import os
from ....modules.shared.utils.pagination import get_pagination_data
from ....modules.shared.utils.search import apply_search_filter
import copy
import zipfile
import shutil
import re
import io

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

def _process_relative_url(url):
    """Chuẩn hóa đường dẫn tương đối và thêm tiền tố tĩnh khi cần."""
    if url is None:
        return None

    normalized = str(url).strip()
    if not normalized:
        return ''

    return normalized


def _build_absolute_media_url(file_path):
    if not file_path:
        return None
    if file_path.startswith(('http://', 'https://')) or file_path.startswith('/'):
        return file_path
    try:
        return url_for('static', filename=file_path)
    except Exception as exc:
        current_app.logger.error(f"Không thể tạo URL tuyệt đối cho media '{file_path}': {exc}")
        return file_path


def _slugify_filename(value: str) -> str:
    value = (value or '').strip().lower()
    if not value:
        return 'quiz-set'
    value = re.sub(r'[^a-z0-9\-]+', '-', value)
    value = re.sub(r'-{2,}', '-', value).strip('-')
    return value or 'quiz-set'


def _resolve_local_media_path(path_value: str):
    if not path_value:
        return None

    normalized = str(path_value).strip()
    if not normalized or normalized.startswith(('http://', 'https://')):
        return None

    base_static = os.path.join(current_app.root_path, 'static')
    candidates = []
    if normalized.startswith('/'):
        candidates.append(os.path.join(base_static, normalized.lstrip('/')))
    else:
        upload_folder = current_app.config.get('UPLOAD_FOLDER')
        if upload_folder:
            candidates.append(os.path.join(upload_folder, normalized))
        candidates.append(os.path.join(base_static, normalized))

    for candidate in candidates:
        if candidate and os.path.isfile(candidate):
            return candidate

    return None


def _copy_media_into_package(
    original_path: str,
    media_dir: str,
    existing_map: dict,
    media_subdir: Optional[str] = None,
) -> str:
    if not original_path:
        return original_path

    normalized = str(original_path).strip()
    if not normalized:
        return ''

    if normalized.startswith(('http://', 'https://')):
        return normalized

    local_path = _resolve_local_media_path(normalized)
    if not local_path:
        return normalized

    if local_path in existing_map:
        return existing_map[local_path]

    audio_exts = {'.mp3', '.wav', '.m4a', '.ogg', '.flac', '.aac'}
    image_exts = {'.png', '.jpg', '.jpeg', '.gif', '.bmp', '.webp', '.svg'}

    filename = os.path.basename(local_path)
    name, ext = os.path.splitext(filename)
    ext_lower = ext.lower()
    target_subdir = media_subdir
    if not target_subdir:
        if ext_lower in audio_exts:
            target_subdir = 'audio'
        elif ext_lower in image_exts:
            target_subdir = 'images'

    base_media_dir = media_dir
    if target_subdir:
        base_media_dir = os.path.join(media_dir, target_subdir)

    os.makedirs(base_media_dir, exist_ok=True)
    candidate = filename
    counter = 1
    while os.path.exists(os.path.join(base_media_dir, candidate)):
        candidate = f"{name}_{counter}{ext}"
        counter += 1

    destination = os.path.join(base_media_dir, candidate)
    shutil.copy2(local_path, destination)
    relative_parts = ['media']
    if target_subdir:
        relative_parts.append(target_subdir)
    relative_parts.append(candidate)
    relative_in_zip = '/'.join(relative_parts)
    existing_map[local_path] = relative_in_zip
    return relative_in_zip


def _serialize_quiz_item_for_response(item, user_id=None):
    content_copy = copy.deepcopy(item.content or {})
    options = content_copy.get('options') or {}
    content_copy['options'] = {
        'A': options.get('A'),
        'B': options.get('B'),
        'C': options.get('C'),
        'D': options.get('D')
    }

    image_path = content_copy.get('question_image_file')
    if image_path:
        content_copy['question_image_file'] = _build_absolute_media_url(image_path)

    audio_path = content_copy.get('question_audio_file')
    if audio_path:
        content_copy['question_audio_file'] = _build_absolute_media_url(audio_path)

    note_content = ''
    if user_id is not None:
        note = UserNote.query.filter_by(user_id=user_id, item_id=item.item_id).first()
        note_content = note.content if note else ''

    return {
        'item_id': item.item_id,
        'container_id': item.container_id,
        'content': content_copy,
        'ai_explanation': item.ai_explanation,
        'note_content': note_content,
        'group_id': item.group_id,
        'group_details': None
    }

def _update_quiz_from_excel_file(container_id: int, excel_file) -> str:
    """Cập nhật câu hỏi quiz từ file Excel được tải lên."""
    temp_filepath = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx') as tmp_file:
            excel_file.save(tmp_file.name)
            temp_filepath = tmp_file.name

        df = pd.read_excel(temp_filepath, sheet_name='Data')

        required_cols = ['option_a', 'option_b', 'correct_answer_text']
        if not all(col in df.columns for col in required_cols):
            raise ValueError(
                "File Excel (sheet 'Data') phải có các cột bắt buộc: option_a, option_b, correct_answer_text."
            )

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

        processed_ids = set()
        delete_ids = set()
        ordered_entries = []
        group_cache = {}

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

        def _resolve_group(row_data, row_index):
            group_id_value = _get_cell(row_data, 'group_id')
            group_ref_value = _get_cell(row_data, 'group_ref')
            group_passage = _get_cell(row_data, 'group_passage_text')
            group_audio = _get_cell(row_data, 'group_audio_file')
            group_image = _get_cell(row_data, 'group_image_file')

            group_id_local = None
            if group_id_value:
                group_id_local = _parse_int(group_id_value, row_index, 'group_id')
            elif group_ref_value and group_ref_value.lower().startswith('group-'):
                try:
                    group_id_local = int(group_ref_value.split('-', 1)[1])
                except (ValueError, IndexError):
                    group_id_local = None

            if group_id_local and group_id_local in existing_groups:
                group_obj = existing_groups[group_id_local]
                content_dict = dict(group_obj.content or {})
                updated = False
                if group_passage:
                    content_dict['passage_text'] = group_passage
                    updated = True
                if group_audio:
                    content_dict['question_audio_file'] = _process_relative_url(group_audio)
                    updated = True
                if group_image:
                    content_dict['question_image_file'] = _process_relative_url(group_image)
                    updated = True
                if updated:
                    group_obj.content = content_dict
                    flag_modified(group_obj, 'content')
                return group_obj

            if group_ref_value and group_ref_value in group_cache:
                return group_cache[group_ref_value]

            if any([group_passage, group_audio, group_image]):
                group_content = {}
                if group_passage:
                    group_content['passage_text'] = group_passage
                if group_audio:
                    group_content['question_audio_file'] = _process_relative_url(group_audio)
                if group_image:
                    group_content['question_image_file'] = _process_relative_url(group_image)

                if group_passage:
                    group_type = 'PASSAGE'
                elif group_audio:
                    group_type = 'AUDIO'
                elif group_image:
                    group_type = 'IMAGE'
                else:
                    group_type = 'PASSAGE'

                new_group = LearningGroup(
                    container_id=container_id,
                    group_type=group_type,
                    content=group_content,
                )
                db.session.add(new_group)
                db.session.flush()
                if group_ref_value:
                    group_cache[group_ref_value] = new_group
                return new_group

            return None

        for index, row in df.iterrows():
            row_number = index + 2
            item_id_value = _get_cell(row, 'item_id')
            action_value = (_get_cell(row, 'action') or '').lower()
            order_value = _get_cell(row, 'order_in_container')
            order_number = _parse_int(order_value, row_number, 'order_in_container') if order_value else None

            question_text = _get_cell(row, 'question') or ''
            option_a = _get_cell(row, 'option_a')
            option_b = _get_cell(row, 'option_b')
            option_c = _get_cell(row, 'option_c')
            option_d = _get_cell(row, 'option_d')
            correct_answer = _get_cell(row, 'correct_answer_text')

            if not (option_a and option_b and correct_answer) and action_value != 'delete':
                raise ValueError(f"Hàng {row_number}: Thiếu option A/B hoặc đáp án đúng.")

            item_id = None
            if item_id_value:
                item_id = _parse_int(item_id_value, row_number, 'item_id')

            if item_id:
                item = existing_map.get(item_id)
                if not item:
                    raise ValueError(f"Hàng {row_number}: Không tìm thấy câu hỏi với ID {item_id}.")

                if action_value == 'delete':
                    delete_ids.add(item_id)
                    continue

                content_dict = item.content or {}
                content_dict['question'] = question_text
                content_dict.setdefault('options', {})
                content_dict['options']['A'] = option_a
                content_dict['options']['B'] = option_b
                content_dict['options']['C'] = option_c
                content_dict['options']['D'] = option_d
                content_dict['correct_answer'] = correct_answer
                content_dict['explanation'] = _get_cell(row, 'guidance')
                content_dict['pre_question_text'] = _get_cell(row, 'pre_question_text')
                passage_text = _get_cell(row, 'passage_text')
                content_dict['passage_text'] = passage_text
                passage_order = _parse_int(_get_cell(row, 'passage_order'), row_number, 'passage_order')
                content_dict['passage_order'] = passage_order
                image_value = _get_cell(row, 'question_image_file')
                audio_value = _get_cell(row, 'question_audio_file')
                content_dict['question_image_file'] = _process_relative_url(image_value) if image_value else None
                content_dict['question_audio_file'] = _process_relative_url(audio_value) if audio_value else None
                ai_prompt_value = _get_cell(row, 'ai_prompt')
                if ai_prompt_value:
                    content_dict['ai_prompt'] = ai_prompt_value
                else:
                    content_dict.pop('ai_prompt', None)

                item_group = _resolve_group(row, row_number)
                item.group_id = item_group.group_id if item_group else None

                item.content = content_dict
                flag_modified(item, 'content')

                ordered_entries.append({
                    'type': 'existing',
                    'item': item,
                    'order': order_number if order_number is not None else (item.order_in_container or 0),
                    'sequence': index,
                })
                processed_ids.add(item_id)
            else:
                if action_value == 'delete':
                    continue

                new_content = {
                    'question': question_text,
                    'options': {
                        'A': option_a,
                        'B': option_b,
                        'C': option_c,
                        'D': option_d,
                    },
                    'correct_answer': correct_answer,
                    'explanation': _get_cell(row, 'guidance'),
                    'pre_question_text': _get_cell(row, 'pre_question_text'),
                }
                passage_text = _get_cell(row, 'passage_text')
                if passage_text:
                    new_content['passage_text'] = passage_text
                passage_order = _parse_int(_get_cell(row, 'passage_order'), row_number, 'passage_order')
                if passage_order is not None:
                    new_content['passage_order'] = passage_order
                image_value = _get_cell(row, 'question_image_file')
                audio_value = _get_cell(row, 'question_audio_file')
                if image_value:
                    new_content['question_image_file'] = _process_relative_url(image_value)
                if audio_value:
                    new_content['question_audio_file'] = _process_relative_url(audio_value)
                ai_prompt_value = _get_cell(row, 'ai_prompt')
                if ai_prompt_value:
                    new_content['ai_prompt'] = ai_prompt_value

                item_group = _resolve_group(row, row_number)
                ordered_entries.append({
                    'type': 'new',
                    'data': new_content,
                    'group_id': item_group.group_id if item_group else None,
                    'group_obj': item_group,
                    'order': order_number,
                    'sequence': index,
                })

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
                group_id_value = entry.get('group_id')
                group_obj = entry.get('group_obj')
                new_item = LearningItem(
                    container_id=container_id,
                    group_id=group_id_value if group_id_value else (group_obj.group_id if group_obj else None),
                    item_type='QUIZ_MCQ',
                    content=entry['data'],
                    order_in_container=next_order,
                )
                db.session.add(new_item)
            next_order += 1

        return 'Bộ câu hỏi và dữ liệu từ Excel đã được cập nhật!'
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
            df_info = pd.read_excel(temp_filepath, sheet_name='Info')
            info_data = df_info.set_index('Key')['Value'].dropna().to_dict()
            return jsonify({'success': True, 'data': info_data})
        except ValueError:
            return jsonify({'success': False, 'message': "Không tìm thấy sheet 'Info' trong file."})
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
        return render_template('_quiz_sets_list.html', **template_vars)
    else:
        return render_template('quiz_sets.html', **template_vars)


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

    with tempfile.TemporaryDirectory() as tmp_dir:
        media_dir = os.path.join(tmp_dir, 'media')
        os.makedirs(media_dir, exist_ok=True)
        media_cache = {}

        info_rows = [
            {'Key': 'title', 'Value': quiz_set.title},
            {'Key': 'description', 'Value': quiz_set.description or ''},
            {'Key': 'tags', 'Value': quiz_set.tags or ''},
            {'Key': 'is_public', 'Value': str(quiz_set.is_public)},
        ]
        if quiz_set.ai_settings:
            info_rows.append({'Key': 'ai_prompt', 'Value': quiz_set.ai_settings.get('custom_prompt', '')})

        data_rows = []
        for item in items:
            content = item.content or {}
            group = groups.get(item.group_id) if item.group_id else None
            group_content = group.content if group else {}
            row = {
                'item_id': item.item_id,
                'order_in_container': item.order_in_container,
                'question': content.get('question'),
                'pre_question_text': content.get('pre_question_text'),
                'option_a': (content.get('options') or {}).get('A'),
                'option_b': (content.get('options') or {}).get('B'),
                'option_c': (content.get('options') or {}).get('C'),
                'option_d': (content.get('options') or {}).get('D'),
                'correct_answer_text': content.get('correct_answer'),
                'guidance': content.get('explanation'),
                'question_image_file': _copy_media_into_package(
                    content.get('question_image_file'), media_dir, media_cache, media_subdir='images'
                ),
                'question_audio_file': _copy_media_into_package(
                    content.get('question_audio_file'), media_dir, media_cache, media_subdir='audio'
                ),
                'passage_text': content.get('passage_text'),
                'passage_order': content.get('passage_order'),
                'ai_prompt': content.get('ai_prompt'),
                'group_id': group.group_id if group else None,
                'group_ref': f"group-{group.group_id}" if group else '',
                'group_type': group.group_type if group else '',
                'group_passage_text': group_content.get('passage_text') if isinstance(group_content, dict) else None,
                'group_audio_file': _copy_media_into_package(
                    group_content.get('question_audio_file') if isinstance(group_content, dict) else None,
                    media_dir,
                    media_cache,
                    media_subdir='audio',
                ),
                'group_image_file': _copy_media_into_package(
                    group_content.get('question_image_file') if isinstance(group_content, dict) else None,
                    media_dir,
                    media_cache,
                    media_subdir='images',
                ),
                'action': '',
            }
            data_rows.append(row)

        excel_path = os.path.join(tmp_dir, 'quizzes.xlsx')
        with pd.ExcelWriter(excel_path, engine='openpyxl') as writer:
            pd.DataFrame(info_rows).to_excel(writer, sheet_name='Info', index=False)
            pd.DataFrame(data_rows).to_excel(writer, sheet_name='Data', index=False)

        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zipf:
            zipf.write(excel_path, arcname='quizzes.xlsx')
            if os.path.isdir(media_dir):
                for root_dir, _, files in os.walk(media_dir):
                    for filename in files:
                        file_path = os.path.join(root_dir, filename)
                        arcname = os.path.relpath(file_path, tmp_dir)
                        zipf.write(file_path, arcname)

        zip_buffer.seek(0)
        download_name = f"{_slugify_filename(quiz_set.title)}.zip"
        return send_file(zip_buffer, as_attachment=True, download_name=download_name, mimetype='application/zip')


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

    export_url = url_for('content_management.content_management_quizzes.export_quiz_set', set_id=set_id)
    return render_template(
        'manage_quiz_excel.html',
        quiz_set=quiz_set,
        export_url=export_url,
    )


@quizzes_bp.route('/quizzes/add', methods=['GET', 'POST'])
@login_required
def add_quiz_set():
    """
    Thêm một bộ Quiz mới.
    """
    form = QuizSetForm()
    _apply_is_public_restrictions(form)
    if form.validate_on_submit():
        flash_message = ''
        flash_category = ''
        temp_filepath = None
        try:
            new_set = LearningContainer(
                creator_user_id=current_user.user_id,
                container_type='QUIZ_SET',
                title=form.title.data,
                description=form.description.data,
                tags=form.tags.data,
                is_public=False if current_user.user_role == 'free' else form.is_public.data,
                ai_settings={'custom_prompt': form.ai_prompt.data} if form.ai_prompt.data else None
            )
            db.session.add(new_set)
            db.session.flush()

            if form.excel_file.data and form.excel_file.data.filename != '':
                excel_file = form.excel_file.data
                with tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx') as tmp_file:
                    excel_file.save(tmp_file.name)
                    temp_filepath = tmp_file.name
                df = pd.read_excel(temp_filepath, sheet_name='Data')
                group_cache = {}
                items_added_count = 0
                for index, row in df.iterrows():
                    group_passage_text = None
                    group_audio_file = None
                    group_image_file = None

                    passage_order = str(row['passage_order']) if 'passage_order' in df.columns and pd.notna(row['passage_order']) else None
                    group_db_id = None
                    group_content = {}
                    group_type = ''

                    if passage_order:
                        group_passage_text = str(row['passage_text']) if 'passage_text' in df.columns and pd.notna(row['passage_text']) else None
                        group_audio_file = str(row['group_audio_file']) if 'group_audio_file' in df.columns and pd.notna(row['group_audio_file']) else None
                        group_image_file = str(row['group_image_file']) if 'group_image_file' in df.columns and pd.notna(row['group_image_file']) else None
                        
                        group_key = None
                        if group_passage_text:
                            group_key = group_passage_text
                            group_content['passage_text'] = group_passage_text
                            group_type = 'PASSAGE'
                        
                        if group_audio_file:
                            group_key = group_audio_file
                            group_content['question_audio_file'] = group_audio_file
                            group_type = 'AUDIO'
                        
                        if group_image_file:
                            group_key = group_image_file
                            group_content['question_image_file'] = group_image_file
                            group_type = 'IMAGE'

                        if group_key and group_key not in group_cache:
                            new_group = LearningGroup(
                                container_id=new_set.container_id,
                                group_type=group_type,
                                content=group_content
                            )
                            db.session.add(new_group)
                            db.session.flush()
                            group_cache[group_key] = new_group.group_id
                            group_db_id = new_group.group_id
                        elif group_key:
                            group_db_id = group_cache[group_key]

                    option_a = str(row['option_a']) if 'option_a' in df.columns and pd.notna(row['option_a']) else None
                    option_b = str(row['option_b']) if 'option_b' in df.columns and pd.notna(row['option_b']) else None
                    correct_answer = str(row['correct_answer_text']) if 'correct_answer_text' in df.columns and pd.notna(row['correct_answer_text']) else None
                    if not (option_a and option_b and correct_answer):
                        current_app.logger.warning(f"Bỏ qua hàng {index + 2} trong Excel: Thiếu thông tin cốt lõi (option_a, option_b, correct_answer_text).")
                        continue

                    question_text = str(row['question']) if 'question' in df.columns and pd.notna(row['question']) else ''
                    
                    item_image_file = str(row['question_image_file']) if 'question_image_file' in df.columns and pd.notna(row['question_image_file']) else None
                    item_audio_file = str(row['question_audio_file']) if 'question_audio_file' in df.columns and pd.notna(row['question_audio_file']) else None
                    
                    item_ai_prompt = str(row['ai_prompt']) if 'ai_prompt' in df.columns and pd.notna(row['ai_prompt']) else None

                    item_content = {
                        'question': question_text,
                        'options': {
                            'A': option_a, 'B': option_b,
                            'C': str(row['option_c']) if 'option_c' in df.columns and pd.notna(row['option_c']) else None,
                            'D': str(row['option_d']) if 'option_d' in df.columns and pd.notna(row['option_d']) else None
                        },
                        'correct_answer': correct_answer,
                        'explanation': str(row['guidance']) if 'guidance' in df.columns and pd.notna(row['guidance']) else None,
                        'pre_question_text': str(row['pre_question_text']) if 'pre_question_text' in df.columns and pd.notna(row['pre_question_text']) else None,
                        'passage_text': str(row['passage_text']) if 'passage_text' in df.columns and pd.notna(row['passage_text']) else None,
                        'passage_order': int(passage_order) if passage_order else None,
                        'question_image_file': item_image_file,
                        'question_audio_file': item_audio_file,
                    }
                    if item_ai_prompt:
                        item_content['ai_prompt'] = item_ai_prompt

                    current_app.logger.debug(f"Hàng {index + 2}: Item Image: '{item_image_file}', Item Audio: '{item_audio_file}'")
                    current_app.logger.debug(f"Hàng {index + 2}: Group Image: '{group_image_file}', Group Audio: '{group_audio_file}'")

                    new_item = LearningItem(
                        container_id=new_set.container_id,
                        group_id=group_db_id,
                        item_type='QUIZ_MCQ',
                        content=item_content,
                        order_in_container=int(passage_order) if passage_order else index + 1
                    )
                    db.session.add(new_item)
                    items_added_count += 1
                flash_message = f'Bộ câu hỏi và {items_added_count} câu hỏi từ Excel đã được tạo thành công!'
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
        return render_template('_add_edit_quiz_set_bare.html', form=form, title='Thêm Bộ câu hỏi mới')
    return render_template('add_edit_quiz_set.html', form=form, title='Thêm Bộ câu hỏi mới')

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
    if form.validate_on_submit():
        flash_message = 'Bộ câu hỏi đã được cập nhật!'
        flash_category = 'success'
        try:
            quiz_set.title = form.title.data
            quiz_set.description = form.description.data
            quiz_set.tags = form.tags.data
            quiz_set.is_public = False if current_user.user_role == 'free' else form.is_public.data
            quiz_set.ai_settings = {'custom_prompt': form.ai_prompt.data} if form.ai_prompt.data else None

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
        return render_template('_add_edit_quiz_set_bare.html', form=form, title='Sửa Bộ câu hỏi', quiz_set=quiz_set)
    return render_template('add_edit_quiz_set.html', form=form, title='Sửa Bộ câu hỏi', quiz_set=quiz_set)

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
        'passage_text': LearningItem.content['passage_text'],
        'question_image_file': LearningItem.content['question_image_file'],
        'question_audio_file': LearningItem.content['question_audio_file'],
        'ai_prompt': LearningItem.content['ai_prompt']
    }

    base_query = apply_search_filter(base_query, search_query, item_search_field_map, search_field)

    pagination = get_pagination_data(base_query.order_by(LearningItem.order_in_container), page)
    quiz_items = pagination.items
    
    can_edit = (current_user.user_role == 'admin' or quiz_set.creator_user_id == current_user.user_id)
    
    return render_template('quiz_items.html', 
                           quiz_set=quiz_set, 
                           quiz_items=quiz_items, 
                           can_edit=can_edit, 
                           pagination=pagination, 
                           search_query=search_query,
                           search_field=search_field,
                           search_field_map=item_search_field_map
                           )

@quizzes_bp.route('/quizzes/<int:set_id>/items/add', methods=['GET', 'POST'])
@login_required
def add_quiz_item(set_id):
    """
    Thêm một câu hỏi mới vào một bộ Quiz cụ thể.
    """
    quiz_set = LearningContainer.query.get_or_404(set_id)
    if current_user.user_role != 'admin' and quiz_set.creator_user_id != current_user.user_id:
        abort(403)
    
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
            'passage_text': form.passage_text.data,
            'passage_order': form.passage_order.data,
            'question_image_file': _process_relative_url(form.question_image_file.data),
            'question_audio_file': _process_relative_url(form.question_audio_file.data)
        }
        if form.ai_prompt.data:
            content_dict['ai_prompt'] = form.ai_prompt.data

        new_item = LearningItem(
            container_id=set_id,
            group_id=None,
            item_type='QUIZ_MCQ',
            content=content_dict,
            order_in_container=new_order
        )
        db.session.add(new_item)
        db.session.commit()
        flash('Câu hỏi mới đã được thêm!', 'success')
        return redirect(url_for('.list_quiz_items', set_id=set_id))
    
    if request.method == 'GET' and request.args.get('is_modal') == 'true':
        return render_template('_add_edit_quiz_item_bare.html', form=form, quiz_set=quiz_set, title='Thêm Câu hỏi')
    return render_template('add_edit_quiz_item.html', form=form, quiz_set=quiz_set, title='Thêm Câu hỏi')

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
    
    form = QuizItemForm()
    if request.method == 'GET':
        form.question.data = quiz_item.content.get('question')
        form.pre_question_text.data = quiz_item.content.get('pre_question_text')
        form.option_a.data = quiz_item.content.get('options', {}).get('A')
        form.option_b.data = quiz_item.content.get('options', {}).get('B')
        form.option_c.data = quiz_item.content.get('options', {}).get('C')
        form.option_d.data = quiz_item.content.get('options', {}).get('D')
        form.correct_answer_text.data = quiz_item.content.get('correct_answer')
        form.guidance.data = quiz_item.content.get('explanation')
        form.question_image_file.data = quiz_item.content.get('question_image_file')
        form.question_audio_file.data = quiz_item.content.get('question_audio_file')
        form.passage_text.data = quiz_item.content.get('passage_text')
        form.passage_order.data = quiz_item.content.get('passage_order')
        form.ai_explanation.data = quiz_item.ai_explanation
        form.ai_prompt.data = quiz_item.content.get('ai_prompt')
        form.order_in_container.data = quiz_item.order_in_container

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
        quiz_item.content['question_image_file'] = _process_relative_url(form.question_image_file.data)
        quiz_item.content['question_audio_file'] = _process_relative_url(form.question_audio_file.data)
        quiz_item.content['passage_text'] = form.passage_text.data
        quiz_item.content['passage_order'] = form.passage_order.data
        quiz_item.ai_explanation = form.ai_explanation.data

        if form.ai_prompt.data:
            quiz_item.content['ai_prompt'] = form.ai_prompt.data
        elif 'ai_prompt' in quiz_item.content:
            del quiz_item.content['ai_prompt']

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

    if request.method == 'GET' and request.args.get('is_modal') == 'true':
        return render_template('_add_edit_quiz_item_bare.html', form=form, quiz_set=quiz_set, quiz_item=quiz_item, title='Chỉnh sửa Câu hỏi')
    return render_template('add_edit_quiz_item.html', form=form, quiz_set=quiz_set, quiz_item=quiz_item, title='Chỉnh sửa Câu hỏi')

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
