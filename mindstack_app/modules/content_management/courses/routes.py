# mindstack_app/modules/content_management/courses/routes.py
# Phiên bản: 4.4
# MỤC ĐÍCH: Hỗ trợ sắp xếp lại thứ tự bài học (lesson) trong một khóa học.
# ĐÃ SỬA: Bổ sung logic vào add_lesson để chèn bài học vào vị trí cụ thể.
# ĐÃ SỬA: Bổ sung logic vào edit_lesson để thay đổi vị trí bài học và cập nhật lại thứ tự các bài học khác.
# ĐÃ SỬA: Cập nhật route list_lessons để sắp xếp theo order_in_container.

from flask import Blueprint, render_template, request, redirect, url_for, flash, abort, jsonify, current_app, send_file
from mindstack_app.utils.template_helpers import render_dynamic_template
from flask_login import login_required, current_user
from sqlalchemy import or_, func
from sqlalchemy.orm.attributes import flag_modified
from ..forms import CourseForm, LessonForm # Đã sửa từ CourseSetForm
from ....models import db, LearningContainer, LearningItem, ContainerContributor, User
from ....core.error_handlers import error_response, success_response
import pandas as pd
import tempfile
import os
import io
import re
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.datavalidation import DataValidation
from mindstack_app.utils.pagination import get_pagination_data
from mindstack_app.utils.search import apply_search_filter
from mindstack_app.utils.excel import extract_info_sheet_mapping, format_info_warnings
from mindstack_app.utils.html_sanitizer import sanitize_rich_text
from mindstack_app.utils.bbcode_parser import bbcode_to_html

COURSE_DATA_COLUMNS = [
    'item_id',
    'order_in_container',
    'title',
    'content_html',
    'estimated_time',
    'action',
]

COURSE_INFO_KEYS = [
    'title',
    'description',
    'cover_image',
    'tags',
    'is_public',
    'ai_prompt',
]

ACTION_OPTIONS = ['None', 'Update', 'Create', 'Delete', 'Skip']


def _slugify_filename(value: str) -> str:
    slug = re.sub(r'[^A-Za-z0-9\-]+', '-', value or 'course')
    slug = slug.strip('-') or 'course'
    return slug.lower()


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


def _create_course_excel(info_rows, data_rows, *, output_path: str | None = None):
    info_df = pd.DataFrame(info_rows, columns=['Key', 'Value'])
    if info_df.empty:
        info_df = pd.DataFrame(columns=['Key', 'Value'])
    else:
        info_df['Value'] = info_df['Value'].apply(lambda value: '' if value is None else str(value))

    data_df = pd.DataFrame(data_rows, columns=COURSE_DATA_COLUMNS)
    if data_df.empty:
        data_df = pd.DataFrame(columns=COURSE_DATA_COLUMNS)
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
            _apply_action_dropdown(data_sheet, COURSE_DATA_COLUMNS)

    if output_path:
        return output_path

    target.seek(0)
    return target


courses_bp = Blueprint('content_management_courses', __name__,
                       template_folder='templates') # Đã cập nhật đường dẫn template



def _has_editor_access(container_id):
    if current_user.user_role == User.ROLE_FREE:
        return False
    return ContainerContributor.query.filter_by(
        container_id=container_id,
        user_id=current_user.user_id,
        permission_level='editor'
    ).first() is not None

def _apply_is_public_restrictions(form):
    """Disable public toggle for free users and ensure value stays False."""
    if hasattr(form, 'is_public') and current_user.user_role == 'free':
        form.is_public.data = False
        existing_render_kw = dict(form.is_public.render_kw or {})
        existing_render_kw['disabled'] = True
        form.is_public.render_kw = existing_render_kw


def _build_course_export_payload(course_set, lessons):
    info_mapping = {
        'title': course_set.title or '',
        'description': course_set.description or '',
        'cover_image': course_set.cover_image or '',
        'tags': course_set.tags or '',
        'is_public': 'True' if course_set.is_public else 'False',
        'ai_prompt': course_set.ai_prompt or '',
    }

    info_rows = [
        {'Key': key, 'Value': info_mapping.get(key, '')}
        for key in COURSE_INFO_KEYS
    ]

    data_rows = []
    for lesson in lessons:
        content = lesson.content or {}
        html_content = content.get('content_html')
        if not html_content and content.get('bbcode_content'):
            html_content = bbcode_to_html(content.get('bbcode_content'))
        row = {
            'item_id': lesson.item_id,
            'order_in_container': lesson.order_in_container if lesson.order_in_container is not None else '',
            'title': content.get('title') or '',
            'content_html': html_content or '',
            'estimated_time': content.get('estimated_time') if content.get('estimated_time') is not None else '',
            'action': 'None',
        }
        data_rows.append(row)

    return info_rows, data_rows


def _update_lessons_from_excel_file(container_id: int, excel_file) -> str:
    temp_filepath = None
    try:
        course_set = LearningContainer.query.get(container_id)
        if not course_set:
            raise ValueError('Không tìm thấy khoá học để cập nhật.')

        with tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx') as tmp_file:
            excel_file.save(tmp_file.name)
            temp_filepath = tmp_file.name

        df = pd.read_excel(temp_filepath, sheet_name='Data')
        required_cols = {'title', 'content_html'}
        if not required_cols.issubset(set(df.columns)):
            raise ValueError('Sheet "Data" phải có các cột title và content_html.')

        info_notices: list[str] = []
        info_mapping, info_warnings = extract_info_sheet_mapping(temp_filepath)
        if info_mapping:
            title_value = info_mapping.get('title')
            if title_value is not None:
                course_set.title = str(title_value)
            description_value = info_mapping.get('description')
            if description_value is not None:
                course_set.description = str(description_value)
            tags_value = info_mapping.get('tags')
            if tags_value is not None:
                course_set.tags = str(tags_value)
            is_public_value = info_mapping.get('is_public')
            if is_public_value is not None:
                desired_public = str(is_public_value).strip().lower() in {'true', '1', 'yes', 'y', 'on'}
                if current_user.user_role == User.ROLE_FREE:
                    course_set.is_public = False
                else:
                    course_set.is_public = desired_public
            ai_prompt_value = info_mapping.get('ai_prompt')
            if ai_prompt_value is not None:
                prompt_clean = str(ai_prompt_value).strip()
                course_set.ai_prompt = prompt_clean or None
            cover_value = info_mapping.get('cover_image')
            if cover_value is not None:
                course_set.cover_image = str(cover_value).strip()
        if info_warnings:
            info_notices.extend(info_warnings)

        existing_items = (
            LearningItem.query.filter_by(container_id=container_id, item_type='LESSON')
            .order_by(LearningItem.order_in_container, LearningItem.item_id)
            .all()
        )
        existing_map = {item.item_id: item for item in existing_items}

        stats = {
            'created': 0,
            'updated': 0,
            'deleted': 0,
            'skipped': 0,
            'reordered': 0,
        }

        action_aliases = {
            'delete': {'delete', 'remove'},
            'skip': {'skip', 'keep', 'none', 'ignore', 'nochange', 'unchanged'},
            'create': {'create', 'new', 'add', 'insert'},
            'update': {'update', 'upsert', 'edit', 'modify'},
        }

        def _normalize_action(raw_action: str | None, has_item_id: bool) -> str:
            value = (raw_action or '').strip().lower()
            if value:
                for normalized, aliases in action_aliases.items():
                    if value in aliases:
                        if normalized == 'create' and has_item_id:
                            return 'update'
                        if normalized == 'update' and not has_item_id:
                            return 'create'
                        return normalized
            return 'update' if has_item_id else 'create'

        def _get_cell(row_data, column_name, *, trim: bool = True):
            if column_name not in df.columns:
                return None
            value = row_data[column_name]
            if pd.isna(value):
                return None
            text = str(value)
            return text.strip() if trim else text

        def _parse_int(value, field_name, row_index):
            if value is None or value == '':
                return None
            try:
                return int(float(value))
            except (TypeError, ValueError):
                raise ValueError(f"Hàng {row_index}: {field_name} '{value}' không hợp lệ.")

        ordered_entries = []
        processed_ids = set()
        delete_ids = set()

        for index, row in df.iterrows():
            row_number = index + 2
            item_id_value = _get_cell(row, 'item_id')
            item_id = None
            if item_id_value:
                item_id = _parse_int(item_id_value, 'item_id', row_number)

            order_value = _get_cell(row, 'order_in_container')
            order_number = _parse_int(order_value, 'order_in_container', row_number) if order_value else None
            if order_number is not None:
                stats['reordered'] += 1

            title_value = _get_cell(row, 'title')
            content_value = _get_cell(row, 'content_html', trim=False)
            estimated_time_value = _get_cell(row, 'estimated_time')
            estimated_time = _parse_int(estimated_time_value, 'estimated_time', row_number) if estimated_time_value else None

            action_value = _normalize_action(_get_cell(row, 'action'), bool(item_id))

            if item_id:
                lesson_item = existing_map.get(item_id)
                if not lesson_item:
                    raise ValueError(f"Hàng {row_number}: Không tìm thấy bài học với ID {item_id}.")

                if action_value == 'delete':
                    delete_ids.add(item_id)
                    stats['deleted'] += 1
                    continue

                if action_value == 'skip':
                    ordered_entries.append({
                        'type': 'existing',
                        'item': lesson_item,
                        'order': order_number if order_number is not None else (lesson_item.order_in_container or 0),
                        'sequence': index,
                    })
                    processed_ids.add(item_id)
                    stats['skipped'] += 1
                    continue

                if not title_value or not content_value:
                    raise ValueError(f"Hàng {row_number}: Thiếu tiêu đề hoặc nội dung cho bài học hiện có.")

                sanitized_html = sanitize_rich_text(content_value)
                lesson_item.content['title'] = title_value
                lesson_item.content['content_html'] = sanitized_html
                lesson_item.content.pop('bbcode_content', None)
                lesson_item.content['estimated_time'] = estimated_time
                flag_modified(lesson_item, 'content')

                ordered_entries.append({
                    'type': 'existing',
                    'item': lesson_item,
                    'order': order_number if order_number is not None else (lesson_item.order_in_container or 0),
                    'sequence': index,
                })
                processed_ids.add(item_id)
                stats['updated'] += 1
            else:
                if action_value in {'delete', 'skip'}:
                    stats['skipped'] += 1
                    continue
                if not title_value or not content_value:
                    stats['skipped'] += 1
                    continue

                sanitized_html = sanitize_rich_text(content_value)
                content_dict = {
                    'title': title_value,
                    'content_html': sanitized_html,
                    'estimated_time': estimated_time,
                }
                ordered_entries.append({
                    'type': 'new',
                    'data': content_dict,
                    'order': order_number,
                    'sequence': index,
                })
                stats['created'] += 1

        untouched_items = [
            item for item in existing_items
            if item.item_id not in processed_ids and item.item_id not in delete_ids
        ]
        for offset, lesson_item in enumerate(untouched_items, start=len(df) + 1):
            ordered_entries.append({
                'type': 'existing',
                'item': lesson_item,
                'order': lesson_item.order_in_container or 0,
                'sequence': offset,
            })

        for delete_id in delete_ids:
            if delete_id in existing_map:
                db.session.delete(existing_map[delete_id])

        ordered_entries.sort(key=lambda entry: (
            entry['order'] if entry['order'] is not None else float('inf'),
            entry['sequence'],
        ))

        next_order = 1
        for entry in ordered_entries:
            if entry['type'] == 'existing':
                lesson_item = entry['item']
                lesson_item.order_in_container = next_order
            else:
                content_dict = entry['data']
                new_item = LearningItem(
                    container_id=container_id,
                    item_type='LESSON',
                    content=content_dict,
                    order_in_container=next_order,
                )
                db.session.add(new_item)
            next_order += 1

        summary_parts = []
        for key, label in [
            ('created', 'tạo mới'),
            ('updated', 'cập nhật'),
            ('deleted', 'xoá'),
            ('skipped', 'bỏ qua'),
        ]:
            summary_parts.append(f"{stats[key]} {label}")
        if stats['reordered']:
            summary_parts.append(f"{stats['reordered']} thay đổi thứ tự")

        summary_text = ', '.join(summary_parts)
        if info_notices:
            summary_text += ' Lưu ý: ' + format_info_warnings(info_notices)

        return 'Đã xử lý Excel: ' + summary_text + '.'

    finally:
        if temp_filepath and os.path.exists(temp_filepath):
            os.remove(temp_filepath)

@courses_bp.route('/courses/process_excel_info', methods=['POST'])
@login_required
def process_excel_info():
    """
    Xử lý file Excel được tải lên để trích xuất thông tin từ sheet 'Info'.

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
            if not info_data and info_warnings:
                message = format_info_warnings(info_warnings)
                return error_response(message, 'BAD_REQUEST', 400)
            message = 'Đã đọc thông tin từ sheet Info.'
            if info_warnings:
                message += ' ' + format_info_warnings(info_warnings)
            return success_response(message=message, data={'data': info_data})
        except Exception as e:
            current_app.logger.error(f"Lỗi khi xử lý sheet Info (Course): {e}")
            return error_response(f'Lỗi đọc file Excel: {e}', 'SERVER_ERROR', 500)
        finally:
            if temp_filepath and os.path.exists(temp_filepath):
                os.remove(temp_filepath)
    return error_response('File không hợp lệ. Vui lòng chọn file .xlsx', 'BAD_REQUEST', 400)


@courses_bp.route('/courses/<int:set_id>/export-excel', methods=['GET'])
@login_required
def export_course_set_excel(set_id):
    course_set = LearningContainer.query.get_or_404(set_id)

    if course_set.creator_user_id != current_user.user_id:
        if current_user.user_role == User.ROLE_FREE:
            abort(403)
        if current_user.user_role != User.ROLE_ADMIN and not _has_editor_access(set_id):
            abort(403)

    lessons = (
        LearningItem.query.filter_by(container_id=set_id, item_type='LESSON')
        .order_by(LearningItem.order_in_container, LearningItem.item_id)
        .all()
    )

    info_rows, data_rows = _build_course_export_payload(course_set, lessons)
    excel_buffer = _create_course_excel(info_rows, data_rows)
    download_name = f"{_slugify_filename(course_set.title)}.xlsx"

    return send_file(
        excel_buffer,
        as_attachment=True,
        download_name=download_name,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    )


@courses_bp.route('/courses/<int:set_id>/manage-excel', methods=['GET', 'POST'])
@login_required
def manage_course_excel(set_id):
    course_set = LearningContainer.query.get_or_404(set_id)

    if course_set.creator_user_id != current_user.user_id:
        if current_user.user_role == User.ROLE_FREE:
            abort(403)
        if current_user.user_role != User.ROLE_ADMIN and not _has_editor_access(set_id):
            abort(403)

    if request.method == 'POST':
        uploaded_file = request.files.get('excel_file')
        if not uploaded_file or uploaded_file.filename == '':
            flash('Vui lòng chọn file Excel (.xlsx) để nhập.', 'danger')
            return redirect(url_for('content_management.content_management_courses.manage_course_excel', set_id=set_id))
        if not uploaded_file.filename.lower().endswith('.xlsx'):
            flash('Định dạng file không hợp lệ. Vui lòng chọn file .xlsx.', 'danger')
            return redirect(url_for('content_management.content_management_courses.manage_course_excel', set_id=set_id))

        try:
            message = _update_lessons_from_excel_file(set_id, uploaded_file)
            db.session.commit()
            flash(message, 'success')
        except Exception as exc:  # pylint: disable=broad-except
            db.session.rollback()
            flash(f'Lỗi khi xử lý: {exc}', 'danger')

        return redirect(url_for('content_management.content_management_courses.manage_course_excel', set_id=set_id))

    export_excel_url = url_for('content_management.content_management_courses.export_course_set_excel', set_id=set_id)
    item_count = LearningItem.query.filter_by(container_id=set_id, item_type='LESSON').count()
    template_url = url_for('content_management.content_management_courses.download_course_excel_template')

    return render_dynamic_template('pages/content_management/courses/excel/manage_course_excel.html',
        course_set=course_set,
        export_excel_url=export_excel_url,
        template_url=template_url,
        item_count=item_count,
    )


@courses_bp.route('/courses/excel-template', methods=['GET'])
@login_required
def download_course_excel_template():
    info_rows = [
        {'Key': 'title', 'Value': 'Tiêu đề khoá học'},
        {'Key': 'description', 'Value': 'Mô tả khoá học'},
        {'Key': 'cover_image', 'Value': 'Đường dẫn ảnh cover (URL hoặc uploads/...)'},
        {'Key': 'tags', 'Value': 'Các thẻ, cách nhau bằng dấu phẩy'},
        {'Key': 'is_public', 'Value': 'true/false - Khoá học công khai hay không'},
        {'Key': 'ai_prompt', 'Value': 'Prompt AI dùng chung cho khoá học (tuỳ chọn)'},
    ]

    sample_row = {
        'item_id': '',
        'order_in_container': 1,
        'title': 'Bài học mẫu',
        'content_html': '<p>Nội dung bài học sử dụng HTML.</p>',
        'estimated_time': 10,
        'action': 'None',
    }

    excel_buffer = _create_course_excel(info_rows, [sample_row])
    return send_file(
        excel_buffer,
        as_attachment=True,
        download_name='course_template.xlsx',
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    )


@courses_bp.route('/courses')
@login_required
def list_course_sets():
    """
    Hiển thị danh sách các bộ Khóa học.

    Hàm này truy xuất các bộ Khóa học mà người dùng hiện tại đã tạo hoặc đóng góp,
    áp dụng bộ lọc tìm kiếm và phân trang, sau đó hiển thị chúng.
    """
    page = request.args.get('page', 1, type=int)
    search_query = request.args.get('q', '', type=str)
    search_field = request.args.get('search_field', 'all', type=str)

    base_query = LearningContainer.query.filter_by(container_type='COURSE')

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
    base_query = apply_search_filter(base_query, search_query, search_field_map, search_field)

    pagination = get_pagination_data(base_query.order_by(LearningContainer.created_at.desc()), page)
    course_sets = pagination.items

    for set_item in course_sets:
        set_item.item_count = db.session.query(LearningItem).filter_by(
            container_id=set_item.container_id,
            item_type='LESSON'
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
        'course_sets': course_sets, 
        'pagination': pagination, 
        'search_query': search_query,
        'search_field': search_field,
        'search_field_map': search_field_map
    }

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return render_dynamic_template('pages/content_management/courses/sets/_courses_list.html', **template_vars)
    else:
        return render_dynamic_template('pages/content_management/courses/sets/courses.html', **template_vars)

@courses_bp.route('/courses/add', methods=['GET', 'POST'])
@login_required
def add_course_set():
    """
    Thêm một bộ Khóa học mới.
    """
    form = CourseForm()
    _apply_is_public_restrictions(form)
    if form.validate_on_submit():
        flash_message = ''
        flash_category = ''
        try:
            ai_prompt_value = (form.ai_prompt.data or '').strip()
            new_set = LearningContainer(
                creator_user_id=current_user.user_id,
                container_type='COURSE',
                title=form.title.data,
                description=form.description.data,
                cover_image=form.cover_image.data,
                tags=form.tags.data,
                is_public=False if current_user.user_role == 'free' else form.is_public.data,
                ai_prompt=ai_prompt_value or None,
            )
            db.session.add(new_set)
            db.session.commit()
            flash_message = 'Bộ khóa học mới đã được tạo thành công!'
            flash_category = 'success'
        except Exception as e:
            db.session.rollback()
            flash_message = f'Lỗi khi xử lý: {str(e)}'
            flash_category = 'danger'
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return success_response(message=flash_message)
        else:
            flash(flash_message, flash_category)
            return redirect(url_for('content_management.content_dashboard', tab='courses'))

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest' and request.method == 'POST':
        return error_response('Dữ liệu không hợp lệ', 'VALIDATION_ERROR', 400, details=form.errors)
    
    if request.method == 'GET' and request.args.get('is_modal') == 'true':
        return render_dynamic_template('pages/content_management/courses/sets/_add_edit_course_set_bare.html', form=form, title='Thêm Bộ khóa học mới')
    
    return render_dynamic_template('pages/content_management/courses/sets/add_edit_course_set.html', form=form, title='Thêm Bộ khóa học mới')


@courses_bp.route('/courses/edit/<int:set_id>', methods=['GET', 'POST'])
@login_required
def edit_course_set(set_id):
    """
    Chỉnh sửa một bộ Khóa học hiện có.
    """
    course_set = LearningContainer.query.get_or_404(set_id)
    if course_set.creator_user_id != current_user.user_id:
        if current_user.user_role == User.ROLE_FREE:
            abort(403)
        if current_user.user_role != User.ROLE_ADMIN and not _has_editor_access(set_id):
            abort(403)
        
    form = CourseForm(obj=course_set)
    _apply_is_public_restrictions(form)
    if form.validate_on_submit():
        flash_message = ''
        flash_category = ''
        try:
            course_set.title = form.title.data
            course_set.description = form.description.data
            course_set.cover_image = form.cover_image.data
            course_set.tags = form.tags.data
            course_set.is_public = False if current_user.user_role == 'free' else form.is_public.data
            ai_prompt_value = (form.ai_prompt.data or '').strip()
            course_set.ai_prompt = ai_prompt_value or None
            db.session.commit()
            flash_message = 'Bộ khóa học đã được cập nhật!'
            flash_category = 'success'
        except Exception as e:
            db.session.rollback()
            flash_message = f'Lỗi khi xử lý: {str(e)}'
            flash_category = 'danger'
            
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return success_response(message=flash_message)
        else:
            flash(flash_message, flash_category)
            return redirect(url_for('content_management.content_dashboard', tab='courses'))

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest' and request.method == 'POST':
        return error_response('Dữ liệu không hợp lệ', 'VALIDATION_ERROR', 400, details=form.errors)
    
    if request.method == 'GET' and request.args.get('is_modal') == 'true':
        return render_dynamic_template('pages/content_management/courses/sets/_add_edit_course_set_bare.html', form=form, title='Chỉnh sửa Bộ khóa học')
    
    return render_dynamic_template('pages/content_management/courses/sets/add_edit_course_set.html', form=form, title='Chỉnh sửa Bộ khóa học')

@courses_bp.route('/courses/delete/<int:set_id>', methods=['POST'])
@login_required
def delete_course_set(set_id):
    """
    Xóa một bộ Khóa học.
    """
    course_set = LearningContainer.query.get_or_404(set_id)
    if current_user.user_role != 'admin' and course_set.creator_user_id != current_user.user_id:
        abort(403)
    db.session.delete(course_set)
    db.session.commit()
    flash('Bộ khóa học đã được xóa thành công!', 'success')
    return redirect(url_for('content_management.content_dashboard', tab='courses'))

@courses_bp.route('/courses/<int:set_id>/lessons')
@login_required
def list_lessons(set_id):
    """
    Hiển thị danh sách các bài học trong một bộ Khóa học cụ thể.
    """
    course = LearningContainer.query.get_or_404(set_id)
    if not course.is_public and course.creator_user_id != current_user.user_id:
        if current_user.user_role == User.ROLE_ADMIN:
            pass
        elif current_user.user_role == User.ROLE_FREE or not _has_editor_access(set_id):
            abort(403)
        
    page = request.args.get('page', 1, type=int)
    search_query = request.args.get('q', '', type=str)
    search_field = request.args.get('search_field', 'all', type=str)

    base_query = LearningItem.query.filter_by(
        container_id=course.container_id,
        item_type='LESSON'
    )
    
    item_search_field_map = {
        'title': LearningItem.content['title'],
        'content': func.coalesce(LearningItem.content['content_html'], LearningItem.content['bbcode_content']),
    }

    base_query = apply_search_filter(base_query, search_query, item_search_field_map, search_field)

    # ĐÃ SỬA: Sắp xếp theo `order_in_container` thay vì ID
    pagination = get_pagination_data(base_query.order_by(LearningItem.order_in_container), page)
    lessons = pagination.items
    can_edit = (
        current_user.user_role == User.ROLE_ADMIN or
        course.creator_user_id == current_user.user_id or
        _has_editor_access(set_id)
    )
       
    return render_dynamic_template('pages/content_management/courses/lessons/lessons.html',
                           course=course,
                           lessons=lessons,
                           can_edit=can_edit,
                           pagination=pagination,
                           search_query=search_query,
                           search_field=search_field,
                           search_field_map=item_search_field_map
                           )

@courses_bp.route('/courses/<int:set_id>/lessons/reorder', methods=['POST'])
@login_required
def reorder_lessons(set_id):
    course_set = LearningContainer.query.get_or_404(set_id)
    if course_set.creator_user_id != current_user.user_id:
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
        return error_response('Định dạng dữ liệu không hợp lệ.', 'BAD_REQUEST', 400)

    if len(order_map) != len(set(order_map.values())):
        return error_response('Thứ tự mới không hợp lệ.', 'BAD_REQUEST', 400)

    items = LearningItem.query.filter(
        LearningItem.container_id == set_id,
        LearningItem.item_type == 'LESSON',
        LearningItem.item_id.in_(order_map.keys())
    ).all()

    if len(items) != len(order_map):
        return error_response('Không tìm thấy một số bài học cần sắp xếp.', 'NOT_FOUND', 404)

    for item in items:
        new_position = order_map.get(item.item_id)
        if new_position is not None:
            item.order_in_container = new_position

    db.session.commit()
    return success_response(message='Thứ tự bài học đã được cập nhật.')

@courses_bp.route('/courses/<int:set_id>/lessons/add', methods=['GET', 'POST'])
@login_required
def add_lesson(set_id):
    """
    Thêm một bài học mới vào một bộ Khóa học cụ thể.
    """
    course_set = LearningContainer.query.get_or_404(set_id)
    if course_set.creator_user_id != current_user.user_id:
        if current_user.user_role == User.ROLE_FREE:
            abort(403)
        if current_user.user_role != User.ROLE_ADMIN and not _has_editor_access(set_id):
            abort(403)
        
    form = LessonForm()
    if form.validate_on_submit():
        # THÊM MỚI: Xử lý logic chèn bài học
        new_order = form.order_in_container.data
        
        if new_order is not None:
            # Cập nhật lại thứ tự của các bài học cũ
            db.session.query(LearningItem).filter(
                LearningItem.container_id == set_id,
                LearningItem.item_type == 'LESSON',
                LearningItem.order_in_container >= new_order
            ).update({
                LearningItem.order_in_container: LearningItem.order_in_container + 1
            }, synchronize_session=False)
        else:
            # Nếu không có thứ tự cụ thể, thêm vào cuối
            max_order = db.session.query(db.func.max(LearningItem.order_in_container)).filter_by(
                container_id=set_id,
                item_type='LESSON'
            ).scalar()
            new_order = (max_order or 0) + 1
        
        content_dict = {
            'title': form.title.data,
            'content_html': sanitize_rich_text(form.content_html.data),
            'estimated_time': form.estimated_time.data,
        }

        new_item = LearningItem(
            container_id=set_id,
            item_type='LESSON',
            content=content_dict,
            order_in_container=new_order
        )
        db.session.add(new_item)
        db.session.commit()
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return success_response(message='Bài học mới đã được thêm!')
        else:
            flash('Bài học đã được thêm!', 'success')
            return redirect(url_for('.list_lessons', set_id=set_id))

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest' and request.method == 'POST':
        return error_response('Dữ liệu không hợp lệ', 'VALIDATION_ERROR', 400, details=form.errors)
        
    if request.method == 'GET' and request.args.get('is_modal') == 'true':
        return render_dynamic_template('pages/content_management/courses/lessons/add_edit_lesson.html', form=form, course_set=course_set, title='Thêm Bài học')
        
    return render_dynamic_template('pages/content_management/courses/lessons/add_edit_lesson.html', form=form, course_set=course_set, title='Thêm Bài học')

@courses_bp.route('/courses/<int:set_id>/lessons/edit/<int:item_id>', methods=['GET', 'POST'])
@login_required
def edit_lesson(set_id, item_id):
    """
    Chỉnh sửa một bài học hiện có trong một bộ Khóa học cụ thể.
    """
    course_set = LearningContainer.query.get_or_404(set_id)
    lesson_item = LearningItem.query.filter_by(item_id=item_id, container_id=set_id).first_or_404()
    if course_set.creator_user_id != current_user.user_id:
        if current_user.user_role == User.ROLE_FREE:
            abort(403)
        if current_user.user_role != User.ROLE_ADMIN and not _has_editor_access(set_id):
            abort(403)
        
    form = LessonForm()
    if form.validate_on_submit():
        # Lấy thứ tự cũ và mới
        old_order = lesson_item.order_in_container
        new_order = form.order_in_container.data
        
        # Nếu thứ tự thay đổi, cập nhật lại các bài học khác
        if new_order is not None and new_order != old_order:
            if new_order > old_order:
                db.session.query(LearningItem).filter(
                    LearningItem.container_id == set_id,
                    LearningItem.item_type == 'LESSON',
                    LearningItem.order_in_container > old_order,
                    LearningItem.order_in_container <= new_order
                ).update({
                    LearningItem.order_in_container: LearningItem.order_in_container - 1
                }, synchronize_session=False)
            else: # new_order < old_order
                db.session.query(LearningItem).filter(
                    LearningItem.container_id == set_id,
                    LearningItem.item_type == 'LESSON',
                    LearningItem.order_in_container >= new_order,
                    LearningItem.order_in_container < old_order
                ).update({
                    LearningItem.order_in_container: LearningItem.order_in_container + 1
                }, synchronize_session=False)
            lesson_item.order_in_container = new_order
        
        lesson_item.content['title'] = form.title.data
        lesson_item.content['content_html'] = sanitize_rich_text(form.content_html.data)
        lesson_item.content.pop('bbcode_content', None)
        lesson_item.content['estimated_time'] = form.estimated_time.data
        flag_modified(lesson_item, "content")
        db.session.commit()
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return success_response(message='Bài học đã được cập nhật!')
        else:
            flash('Bài học đã được cập nhật!', 'success')
            return redirect(url_for('.list_lessons', set_id=set_id))
            
    if request.method == 'GET':
        form.title.data = lesson_item.content.get('title')
        existing_html = lesson_item.content.get('content_html')
        if not existing_html:
            existing_html = bbcode_to_html(lesson_item.content.get('bbcode_content', ''))
        form.content_html.data = existing_html
        form.estimated_time.data = lesson_item.content.get('estimated_time')
        form.order_in_container.data = lesson_item.order_in_container
        
    if request.method == 'GET' and request.args.get('is_modal') == 'true':
        return render_dynamic_template('pages/content_management/courses/lessons/add_edit_lesson.html', form=form, course_set=course_set, lesson_item=lesson_item, title='Sửa Bài học')
        
    return render_dynamic_template('pages/content_management/courses/lessons/add_edit_lesson.html', form=form, course_set=course_set, lesson_item=lesson_item, title='Sửa Bài học')

@courses_bp.route('/courses/<int:set_id>/lessons/delete/<int:item_id>', methods=['POST'])
@login_required
def delete_lesson(set_id, item_id):
    """
    Xóa một bài học khỏi một bộ Khóa học cụ thể.
    """
    course_set = LearningContainer.query.get_or_404(set_id)
    lesson_item = LearningItem.query.get_or_404(item_id)
    if course_set.creator_user_id != current_user.user_id:
        if current_user.user_role == User.ROLE_FREE:
            abort(403)
        if current_user.user_role != User.ROLE_ADMIN and not _has_editor_access(set_id):
            abort(403)
        
    db.session.delete(lesson_item)
    db.session.commit()
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return success_response(message='Bài học đã được xóa.')
    else:
        flash('Bài học đã được xóa.', 'success')
        return redirect(url_for('.list_lessons', set_id=set_id))
