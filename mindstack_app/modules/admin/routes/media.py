# File: mindstack_app/modules/admin/routes/media.py
import os
from uuid import uuid4
from flask import render_template, redirect, url_for, flash, request, current_app
from werkzeug.utils import secure_filename, safe_join
from mindstack_app.core.config import Config
from mindstack_app.services.config_service import get_runtime_config
from .. import blueprint
from ..services.media_service import (
    ADMIN_ALLOWED_MEDIA_EXTENSIONS,
    normalize_subpath,
    collect_directory_listing,
    format_file_size
)

@blueprint.route('/media-library', methods=['GET', 'POST'])
def media_library():
    """
    Mô tả: Hiển thị trang quản lý thư viện media (tải file, tạo thư mục).
    """
    upload_root = get_runtime_config('UPLOAD_FOLDER', Config.UPLOAD_FOLDER)
    if not upload_root:
        flash('Hệ thống chưa cấu hình thư mục lưu trữ uploads.', 'danger')
        return redirect(url_for('admin.admin_dashboard'))

    try:
        current_folder = normalize_subpath(
            request.form.get('current_folder') if request.method == 'POST' else request.args.get('folder')
        )
    except ValueError:
        flash('Đường dẫn thư mục không hợp lệ.', 'danger')
        return redirect(url_for('admin.media_library'))

    target_dir = safe_join(upload_root, current_folder) if current_folder else upload_root
    if target_dir is None:
        flash('Đường dẫn thư mục không hợp lệ.', 'danger')
        return redirect(url_for('admin.media_library'))

    os.makedirs(target_dir, exist_ok=True)

    if request.method == 'POST':
        action = request.form.get('action', 'upload')
        if action == 'create_folder':
            new_folder_name = secure_filename(request.form.get('folder_name', '').strip())
            if not new_folder_name:
                flash('Tên thư mục không hợp lệ.', 'warning')
            else:
                new_dir = os.path.join(target_dir, new_folder_name)
                os.makedirs(new_dir, exist_ok=True)
                flash(f'Đã tạo thư mục "{new_folder_name}".', 'success')
                normalized_new_dir = normalize_subpath(os.path.relpath(new_dir, upload_root))
                return redirect(url_for('admin.media_library', folder=normalized_new_dir))
        else:
            uploaded_files = request.files.getlist('media_files')
            if not uploaded_files:
                flash('Vui lòng chọn ít nhất một file để tải lên.', 'warning')
            else:
                saved = []
                skipped = []
                for file in uploaded_files:
                    if not file or file.filename == '':
                        continue
                    original_name = file.filename
                    filename = secure_filename(original_name)
                    if not filename:
                        skipped.append(original_name)
                        continue
                    ext = os.path.splitext(filename)[1].lower()
                    if ext and ext not in ADMIN_ALLOWED_MEDIA_EXTENSIONS:
                        skipped.append(original_name)
                        continue

                    candidate_name = filename
                    destination = os.path.join(target_dir, candidate_name)
                    while os.path.exists(destination):
                        name_part, extension_part = os.path.splitext(filename)
                        candidate_name = f"{name_part}_{uuid4().hex[:6]}{extension_part}"
                        destination = os.path.join(target_dir, candidate_name)

                    try:
                        file.save(destination)
                        saved.append(candidate_name)
                    except Exception as exc:
                        current_app.logger.exception('Không thể lưu file %s: %s', candidate_name, exc)
                        skipped.append(original_name)

                if saved:
                    flash(f'Đã tải lên {len(saved)} file thành công.', 'success')
                if skipped:
                    flash('Một số file bị bỏ qua: ' + ', '.join(skipped), 'warning')

        return redirect(url_for('admin.media_library', folder=current_folder or None))

    directories, files = collect_directory_listing(target_dir, upload_root)
    breadcrumb = []
    if current_folder:
        parts = current_folder.split('/')
        cumulative = []
        for part in parts:
            cumulative.append(part)
            breadcrumb.append({'name': part, 'path': '/'.join(cumulative)})

    parent_folder = '/'.join(current_folder.split('/')[:-1]) if current_folder else ''
    total_size = format_file_size(sum(item['size_bytes'] for item in files)) if files else '0 B'

    return render_template(
        'admin/media_library.html',
        directories=directories,
        files=files,
        current_folder=current_folder,
        parent_folder=parent_folder,
        breadcrumb=breadcrumb,
        total_size=total_size,
    )

@blueprint.route('/media-library/delete', methods=['POST'])
def delete_media_item():
    """
    Mô tả: Xử lý yêu cầu xóa một file media.
    """
    upload_root = get_runtime_config('UPLOAD_FOLDER', Config.UPLOAD_FOLDER)
    if not upload_root:
        flash('Hệ thống chưa cấu hình thư mục lưu trữ uploads.', 'danger')
        return redirect(url_for('admin.admin_dashboard'))

    try:
        relative_path = normalize_subpath(request.form.get('path'))
    except ValueError:
        flash('Đường dẫn file không hợp lệ.', 'danger')
        return redirect(url_for('admin.media_library'))

    full_path = safe_join(upload_root, relative_path)
    if not full_path or not os.path.isfile(full_path):
        flash('Không tìm thấy file để xóa.', 'warning')
        parent_folder = '/'.join((relative_path or '').split('/')[:-1])
        return redirect(url_for('admin.media_library', folder=parent_folder or None))

    try:
        os.remove(full_path)
        flash('Đã xóa file thành công.', 'success')
    except Exception as exc:
        current_app.logger.exception('Không thể xóa file %s: %s', full_path, exc)
        flash('Không thể xóa file. Vui lòng thử lại.', 'danger')

    parent_folder = '/'.join(relative_path.split('/')[:-1])
    return redirect(url_for('admin.media_library', folder=parent_folder or None))
