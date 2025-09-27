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
from sqlalchemy import or_
from sqlalchemy.orm.attributes import flag_modified
from ..forms import FlashcardSetForm, FlashcardItemForm
from ....models import db, LearningContainer, LearningItem, ContainerContributor, User
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
# THÊM MỚI: Import AudioService
from ...learning.flashcard_learning.audio_service import AudioService
from ...learning.flashcard_learning.image_service import ImageService

flashcards_bp = Blueprint('content_management_flashcards', __name__,
                            template_folder='templates') # Đã cập nhật đường dẫn template

# Khởi tạo service
audio_service = AudioService()
image_service = ImageService()


CAPABILITY_FLAGS = (
    'supports_pronunciation',
    'supports_writing',
    'supports_quiz',
    'supports_essay',
    'supports_listening',
    'supports_speaking',
)


def _apply_is_public_restrictions(form):
    """Disable public toggle for free users and ensure value stays False."""
    if hasattr(form, 'is_public') and current_user.user_role == 'free':
        form.is_public.data = False
        existing_render_kw = dict(form.is_public.render_kw or {})
        existing_render_kw['disabled'] = True
        form.is_public.render_kw = existing_render_kw

def _normalize_capabilities(raw_capabilities):
    """Convert different representations of capability flags into a set of strings."""
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
    """Return the set of learning capability flags enabled on a flashcard container."""
    if not container or not isinstance(getattr(container, 'ai_settings', None), dict):
        return set()
    return _normalize_capabilities(container.ai_settings.get('capabilities'))


def _build_ai_settings_from_form(form, existing_settings=None):
    """Compose the ai_settings payload based on form input and existing settings."""
    settings = {}
    if isinstance(existing_settings, dict):
        # Sao chép để tránh chỉnh sửa tại chỗ
        settings.update(existing_settings)

    ai_prompt_value = (getattr(form.ai_prompt, 'data', '') or '').strip()
    if ai_prompt_value:
        settings['custom_prompt'] = ai_prompt_value
    else:
        settings.pop('custom_prompt', None)

    capability_flags = [
        flag_name
        for flag_name in CAPABILITY_FLAGS
        if getattr(getattr(form, flag_name, None), 'data', False)
    ]

    if capability_flags:
        settings['capabilities'] = capability_flags
    else:
        settings.pop('capabilities', None)

    return settings or None

def _process_relative_url(url):
    """Chuẩn hóa đường dẫn tương đối và thêm tiền tố tĩnh khi cần."""
    if url is None:
        return None

    normalized = str(url).strip()
    if not normalized:
        return ''

    return normalized


def _get_static_image_url(url):
    if not url:
        return None

    if isinstance(url, str):
        normalized = url.strip()
    else:
        normalized = str(url).strip()

    if not normalized:
        return None

    if normalized.startswith(('http://', 'https://', '/')):
        return normalized

    relative_path = normalized
    if relative_path.startswith('uploads/'):
        relative_path = relative_path.replace('uploads/', '', 1)

    return url_for('static', filename=relative_path)


def _get_static_audio_url(url):
    """Chuyển đổi đường dẫn audio tương đối thành URL tĩnh đầy đủ."""
    if not url:
        return None

    if isinstance(url, str):
        normalized = url.strip()
    else:
        normalized = str(url).strip()

    if not normalized:
        return None

    if normalized.startswith(('http://', 'https://', '/')):
        return normalized

    relative_path = normalized
    if relative_path.startswith('uploads/'):
        relative_path = relative_path.replace('uploads/', '', 1)

    return url_for('static', filename=relative_path)


def _slugify_filename(value: str) -> str:
    """Chuyển tiêu đề thành chuỗi thân thiện để đặt tên file zip."""
    value = (value or '').strip().lower()
    if not value:
        return 'flashcard-set'
    value = re.sub(r'[^a-z0-9\-]+', '-', value)
    value = re.sub(r'-{2,}', '-', value).strip('-')
    return value or 'flashcard-set'


def _resolve_local_media_path(path_value: str):
    """Trả về đường dẫn tuyệt đối tới file media nếu thuộc thư mục uploads/static."""
    if not path_value:
        return None

    normalized = str(path_value).strip()
    if not normalized:
        return None

    if normalized.startswith(('http://', 'https://')):
        return None

    # Nếu đường dẫn bắt đầu bằng /static, thử map tới thư mục static
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
    """Sao chép file media vào thư mục tạm và trả về đường dẫn tương đối trong gói.

    Các file sẽ được đặt trong thư mục ``media`` và được tách thành ``audio`` hoặc
    ``images`` nếu ``media_subdir`` được cung cấp (hoặc suy ra từ phần mở rộng).
    """
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


def _has_editor_access(container_id):
    if current_user.user_role == User.ROLE_FREE:
        return False
    return ContainerContributor.query.filter_by(
        container_id=container_id,
        user_id=current_user.user_id,
        permission_level='editor'
    ).first() is not None


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
            'ai_explanation',
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
        container_capabilities = _get_container_capabilities(
            LearningContainer.query.get(container_id)
        )

        def _get_cell(row_data, column_name):
            if column_name not in df.columns:
                return None
            value = row_data[column_name]
            if pd.isna(value):
                return None
            return str(value).strip()

        for index, row in df.iterrows():
            item_id_value = _get_cell(row, 'item_id')
            action_value = (_get_cell(row, 'action') or '').lower()
            order_value = _get_cell(row, 'order_in_container')
            order_number = None
            if order_value:
                try:
                    order_number = int(float(order_value))
                except (TypeError, ValueError):
                    raise ValueError(
                        f"Hàng {index + 2}: order_in_container '{order_value}' không hợp lệ."
                    )

            front_content = _get_cell(row, 'front') or ''
            back_content = _get_cell(row, 'back') or ''

            item_id = None
            if item_id_value:
                try:
                    item_id = int(float(item_id_value))
                except (TypeError, ValueError):
                    raise ValueError(
                        f"Hàng {index + 2}: item_id '{item_id_value}' không hợp lệ."
                    )

            if item_id:
                item = existing_map.get(item_id)
                if not item:
                    raise ValueError(f"Hàng {index + 2}: Không tìm thấy thẻ với ID {item_id}.")

                if action_value == 'delete':
                    delete_ids.add(item_id)
                    continue

                if not front_content or not back_content:
                    raise ValueError(
                        f"Hàng {index + 2}: Thẻ với ID {item_id} thiếu dữ liệu front/back."
                    )

                content_dict = item.content or {}
                content_dict['front'] = front_content
                content_dict['back'] = back_content
                for field in optional_fields:
                    cell_value = _get_cell(row, field)
                    if cell_value:
                        if field in url_fields:
                            content_dict[field] = _process_relative_url(cell_value)
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
                if not front_content or not back_content:
                    # Bỏ qua dòng rỗng
                    continue

                content_dict = {'front': front_content, 'back': back_content}
                for field in optional_fields:
                    cell_value = _get_cell(row, field)
                    if cell_value:
                        if field in url_fields:
                            content_dict[field] = _process_relative_url(cell_value)
                        elif field in capability_fields:
                            content_dict[field] = cell_value.lower() in {'true', '1', 'yes', 'y', 'on'}
                        else:
                            content_dict[field] = cell_value
                for capability_flag in container_capabilities:
                    content_dict.setdefault(capability_flag, True)
                ordered_entries.append({
                    'type': 'new',
                    'data': content_dict,
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
                new_item = LearningItem(
                    container_id=container_id,
                    item_type='FLASHCARD',
                    content=entry['data'],
                    order_in_container=next_order,
                )
                db.session.add(new_item)
            next_order += 1

        return 'Bộ thẻ và dữ liệu từ Excel đã được cập nhật!'
    finally:
        if temp_filepath and os.path.exists(temp_filepath):
            os.remove(temp_filepath)

@flashcards_bp.route('/flashcards/process_excel_info', methods=['POST'])
@login_required
def process_excel_info():
    """
    Xử lý file Excel được tải lên để trích xuất thông tin từ sheet 'Info'.

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
            
            # Đọc sheet 'Info' từ file Excel
            df_info = pd.read_excel(temp_filepath, sheet_name='Info')
            info_data = df_info.set_index('Key')['Value'].dropna().to_dict()
            return jsonify({'success': True, 'data': info_data})
        except ValueError:
            # Xử lý trường hợp không tìm thấy sheet 'Info'
            return jsonify({'success': False, 'message': "Không tìm thấy sheet 'Info' trong file."})
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
    Hiển thị danh sách các bộ Flashcard.

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
            creator_label = creator.username
            if creator.user_id == current_user.user_id:
                creator_label += " (Bạn)"
            set_item.creator_display_name = creator_label
        else:
            set_item.creator_display_name = "Không xác định"

        # Danh sách những người có quyền chỉnh sửa
        editor_labels = []
        seen_user_ids = set()

        if creator:
            seen_user_ids.add(creator.user_id)
            creator_editor_label = creator.username
            if creator.user_id == current_user.user_id:
                creator_editor_label += " (Bạn)"
            else:
                creator_editor_label += " (Người tạo)"
            editor_labels.append(creator_editor_label)

        for contributor in getattr(set_item, 'contributors', []) or []:
            if contributor.permission_level != 'editor':
                continue
            contributor_user = getattr(contributor, 'user', None)
            if not contributor_user or contributor_user.user_id in seen_user_ids:
                continue

            contributor_label = contributor_user.username
            if contributor_user.user_id == current_user.user_id:
                contributor_label += " (Bạn)"
            editor_labels.append(contributor_label)
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

    with tempfile.TemporaryDirectory() as tmp_dir:
        media_dir = os.path.join(tmp_dir, 'media')
        os.makedirs(media_dir, exist_ok=True)
        media_cache = {}

        info_rows = [
            {'Key': 'title', 'Value': flashcard_set.title},
            {'Key': 'description', 'Value': flashcard_set.description or ''},
            {'Key': 'tags', 'Value': flashcard_set.tags or ''},
            {'Key': 'is_public', 'Value': str(flashcard_set.is_public)},
        ]

        container_capabilities = _get_container_capabilities(flashcard_set)
        for capability_key in CAPABILITY_FLAGS:
            info_rows.append({'Key': capability_key, 'Value': str(capability_key in container_capabilities)})

        if flashcard_set.ai_settings:
            info_rows.append({'Key': 'ai_prompt', 'Value': flashcard_set.ai_settings.get('custom_prompt', '')})

        data_rows = []
        for item in items:
            content = item.content or {}
            row = {
                'item_id': item.item_id,
                'order_in_container': item.order_in_container,
                'front': content.get('front'),
                    'back': content.get('back'),
                    'front_audio_content': content.get('front_audio_content'),
                    'back_audio_content': content.get('back_audio_content'),
                    'front_audio_url': _copy_media_into_package(
                        content.get('front_audio_url'), media_dir, media_cache, media_subdir='audio'
                    ),
                    'back_audio_url': _copy_media_into_package(
                        content.get('back_audio_url'), media_dir, media_cache, media_subdir='audio'
                    ),
                    'front_img': _copy_media_into_package(
                        content.get('front_img'), media_dir, media_cache, media_subdir='images'
                    ),
                    'back_img': _copy_media_into_package(
                        content.get('back_img'), media_dir, media_cache, media_subdir='images'
                    ),
                    'ai_explanation': content.get('ai_explanation'),
                    'ai_prompt': content.get('ai_prompt'),
                    'supports_pronunciation': content.get('supports_pronunciation'),
                    'supports_writing': content.get('supports_writing'),
                    'supports_quiz': content.get('supports_quiz'),
                    'supports_essay': content.get('supports_essay'),
                    'supports_listening': content.get('supports_listening'),
                    'supports_speaking': content.get('supports_speaking'),
                    'action': '',
                }
            data_rows.append(row)

        excel_path = os.path.join(tmp_dir, 'flashcards.xlsx')
        with pd.ExcelWriter(excel_path, engine='openpyxl') as writer:
            pd.DataFrame(info_rows).to_excel(writer, sheet_name='Info', index=False)
            pd.DataFrame(data_rows).to_excel(writer, sheet_name='Data', index=False)

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

    export_url = url_for('content_management.content_management_flashcards.export_flashcard_set', set_id=set_id)
    return render_template(
        'manage_flashcard_excel.html',
        flashcard_set=flashcard_set,
        export_url=export_url,
    )


@flashcards_bp.route('/flashcards/add', methods=['GET', 'POST'])
@login_required
def add_flashcard_set():
    """
    Thêm một bộ Flashcard mới.

    Hàm này xử lý việc tạo bộ Flashcard, bao gồm cả việc nhập dữ liệu từ file Excel
    và thêm các thẻ Flashcard liên quan.
    """
    form = FlashcardSetForm()
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
            db.session.add(new_set)
            db.session.flush() # Lưu tạm thời để có container_id

            # Xử lý file Excel nếu có
            if form.excel_file.data and form.excel_file.data.filename != '':
                excel_file = form.excel_file.data
                with tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx') as tmp_file:
                    excel_file.save(tmp_file.name)
                    temp_filepath = tmp_file.name
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
        return render_template('_add_edit_flashcard_set_bare.html', form=form, title='Thêm Bộ thẻ ghi nhớ')
    return render_template('add_edit_flashcard_set.html', form=form, title='Thêm Bộ thẻ ghi nhớ')

@flashcards_bp.route('/flashcards/edit/<int:set_id>', methods=['GET', 'POST'])
@login_required
def edit_flashcard_set(set_id):
    """
    Chỉnh sửa một bộ Flashcard hiện có.

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
        if isinstance(flashcard_set.ai_settings, dict):
            form.ai_prompt.data = flashcard_set.ai_settings.get('custom_prompt', '')
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
    Xóa một bộ Flashcard.

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
    Hiển thị danh sách các thẻ Flashcard trong một bộ cụ thể.

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

        relative_path = image_service.convert_to_static_url(absolute_path)
        if not relative_path:
            return jsonify({'success': False, 'message': 'Không thể xử lý đường dẫn ảnh.'}), 500

        image_url = url_for('static', filename=relative_path)
        return jsonify({
            'success': True,
            'message': 'Đã tìm thấy ảnh minh họa.',
            'relative_path': relative_path,
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
    Thêm một thẻ Flashcard mới vào một bộ cụ thể.

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
            'front_audio_url': _process_relative_url(form.front_audio_url.data),
            'back_audio_content': form.back_audio_content.data,
            'back_audio_url': _process_relative_url(form.back_audio_url.data),
            'front_img': _process_relative_url(form.front_img.data),
            'back_img': _process_relative_url(form.back_img.data),
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
        'front_image_url': _get_static_image_url(form.front_img.data),
        'back_image_url': _get_static_image_url(form.back_img.data),
        'front_audio_url_resolved': _get_static_audio_url(form.front_audio_url.data),
        'back_audio_url_resolved': _get_static_audio_url(form.back_audio_url.data),
        'image_search_url': url_for('.search_flashcard_image', set_id=set_id, item_id=0),
        'regenerate_audio_url': url_for('learning.flashcard_learning.regenerate_audio_from_content')
    }

    # Render template cho modal hoặc trang đầy đủ
    if request.method == 'GET' and request.args.get('is_modal') == 'true':
        return render_template('_add_edit_flashcard_item_bare.html', **context)
    return render_template('add_edit_flashcard_item.html', **context)

@flashcards_bp.route('/flashcards/<int:set_id>/items/edit/<int:item_id>', methods=['GET', 'POST'])
@login_required
def edit_flashcard_item(set_id, item_id):
    """
    Chỉnh sửa một thẻ Flashcard hiện có trong một bộ cụ thể.

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
    container_capabilities = _get_container_capabilities(flashcard_set)
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
        flashcard_item.content['front_audio_url'] = _process_relative_url(form.front_audio_url.data)
        flashcard_item.content['back_audio_content'] = form.back_audio_content.data
        flashcard_item.content['back_audio_url'] = _process_relative_url(form.back_audio_url.data)
        flashcard_item.content['front_img'] = _process_relative_url(form.front_img.data)
        flashcard_item.content['back_img'] = _process_relative_url(form.back_img.data)
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
        'front_image_url': _get_static_image_url(form.front_img.data),
        'back_image_url': _get_static_image_url(form.back_img.data),
        'front_audio_url_resolved': _get_static_audio_url(form.front_audio_url.data),
        'back_audio_url_resolved': _get_static_audio_url(form.back_audio_url.data),
        'image_search_url': url_for('.search_flashcard_image', set_id=set_id, item_id=item_id),
        'regenerate_audio_url': url_for('learning.flashcard_learning.regenerate_audio_from_content')
    }

    # Render template cho modal hoặc trang đầy đủ
    if request.method == 'GET' and request.args.get('is_modal') == 'true':
        return render_template('_add_edit_flashcard_item_bare.html', **context)
    return render_template('add_edit_flashcard_item.html', **context)

@flashcards_bp.route('/flashcards/delete/<int:set_id>/items/delete/<int:item_id>', methods=['POST'])
@login_required
def delete_flashcard_item(set_id, item_id):
    """
    Xóa một thẻ Flashcard khỏi một bộ cụ thể.

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