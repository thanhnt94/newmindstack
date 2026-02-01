import os
import zipfile
import json
from datetime import datetime
from flask import render_template, redirect, url_for, flash, request, send_file, current_app
from werkzeug.utils import safe_join
from .. import blueprint
from ..services.backup_service import (
    DATASET_CATALOG,
    get_backup_folder,
    resolve_database_path,
    collect_dataset_payload,
    write_dataset_to_zip,
    restore_from_uploaded_bytes
)

@blueprint.route('/')
def manage_backup_restore():
    """
    Mô tả: Hiển thị trang quản lý sao lưu và khôi phục dữ liệu.
    """
    backup_folder = get_backup_folder()
    backup_entries: list[dict[str, object]] = []
    
    if os.path.exists(backup_folder):
        for filename in os.listdir(backup_folder):
            if not filename.endswith('.zip'):
                continue

            file_path = os.path.join(backup_folder, filename)
            created_at = datetime.fromtimestamp(os.path.getmtime(file_path))
            file_size = os.path.getsize(file_path)
            
            # Format size to human readable
            if file_size < 1024 * 1024:
                size_label = f"{round(file_size / 1024, 1)} KB"
            else:
                size_label = f"{round(file_size / (1024 * 1024), 1)} MB"

            has_uploads = False

            try:
                with zipfile.ZipFile(file_path, 'r') as zipf:
                    members = zipf.namelist()
                    has_uploads = any(member.startswith('uploads/') for member in members)

                    if not has_uploads and 'manifest.json' in members:
                        try:
                            manifest_raw = zipf.read('manifest.json')
                            manifest_data = json.loads(manifest_raw.decode('utf-8'))
                            has_uploads = bool(manifest_data.get('includes_uploads', False))
                        except (KeyError, ValueError, UnicodeDecodeError):
                            pass
            except zipfile.BadZipFile:
                pass

            backup_entries.append(
                {
                    'name': filename,
                    'created_at': created_at,
                    'created_at_label': created_at.strftime('%d/%m/%Y %H:%M:%S'),
                    'size_label': size_label,
                    'has_uploads': has_uploads,
                }
            )

    backup_entries.sort(key=lambda entry: entry['created_at'], reverse=True)

    dataset_options = [
        {
            'key': key,
            'label': config['label'],
            'description': config['description'],
        }
        for key, config in DATASET_CATALOG.items()
    ]

    return render_template(
        'admin/backup_restore.html',
        backup_entries=backup_entries,
        dataset_options=dataset_options,
    )

@blueprint.route('/create/database', methods=['POST'])
def create_database_backup():
    try:
        backup_folder = get_backup_folder()
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_filename = f'mindstack_database_backup_{timestamp}.zip'
        backup_path = os.path.join(backup_folder, backup_filename)

        db_path = resolve_database_path()
        if not os.path.exists(db_path):
            raise FileNotFoundError('Không tìm thấy file cơ sở dữ liệu để sao lưu.')

        with zipfile.ZipFile(backup_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            zipf.write(db_path, os.path.basename(db_path))
            manifest = {
                'type': 'database',
                'generated_at': datetime.utcnow().isoformat() + 'Z',
                'database_file': os.path.basename(db_path),
            }
            zipf.writestr('manifest.json', json.dumps(manifest, ensure_ascii=False, indent=2))

        flash('Đã sao lưu cơ sở dữ liệu thành công!', 'success')
    except Exception as exc:
        current_app.logger.error('Lỗi khi tạo bản sao lưu database: %s', exc)
        flash(f'Lỗi khi tạo bản sao lưu cơ sở dữ liệu: {exc}', 'danger')

    return redirect(url_for('backup.manage_backup_restore'))


@blueprint.route('/create/full', methods=['POST'])
def download_full_backup():
    try:
        backup_folder = get_backup_folder()
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_filename = f'mindstack_full_backup_{timestamp}.zip'
        backup_path = os.path.join(backup_folder, backup_filename)

        db_path = resolve_database_path()
        if not os.path.exists(db_path):
            raise FileNotFoundError('Không tìm thấy file cơ sở dữ liệu.')

        with zipfile.ZipFile(backup_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            zipf.write(db_path, os.path.basename(db_path))
            
            uploads_folder = os.path.join(current_app.root_path, 'static', 'uploads')
            if os.path.exists(uploads_folder):
                for root, dirs, files in os.walk(uploads_folder):
                    for file in files:
                        file_path = os.path.join(root, file)
                        arcname = os.path.join('uploads', os.path.relpath(file_path, uploads_folder))
                        zipf.write(file_path, arcname)

            manifest = {
                'type': 'full',
                'generated_at': datetime.utcnow().isoformat() + 'Z',
                'database_file': os.path.basename(db_path),
                'includes_uploads': True
            }
            zipf.writestr('manifest.json', json.dumps(manifest, ensure_ascii=False, indent=2))

        return send_file(backup_path, as_attachment=True, download_name=backup_filename)

    except Exception as exc:
        current_app.logger.error('Lỗi khi tạo bản sao lưu toàn bộ: %s', exc)
        flash(f'Lỗi khi tạo bản sao lưu toàn bộ: {exc}', 'danger')
        return redirect(url_for('backup.manage_backup_restore'))


@blueprint.route('/files/<path:filename>')
def download_backup_file(filename):
    backup_folder = get_backup_folder()
    target_path = safe_join(backup_folder, filename)

    if not target_path or not os.path.isfile(target_path):
        flash('File sao lưu không tồn tại.', 'danger')
        return redirect(url_for('backup.manage_backup_restore'))

    return send_file(target_path, as_attachment=True, download_name=os.path.basename(target_path))


@blueprint.route('/files/<path:filename>/delete', methods=['POST'])
def delete_backup_file(filename):
    backup_folder = get_backup_folder()
    target_path = safe_join(backup_folder, filename)

    if not target_path or not os.path.isfile(target_path):
        flash('File sao lưu không tồn tại.', 'danger')
        return redirect(url_for('backup.manage_backup_restore'))

    try:
        os.remove(target_path)
        flash('Đã xóa file sao lưu thành công.', 'success')
    except Exception as e:
        flash(f'Lỗi khi xóa file: {str(e)}', 'danger')

    return redirect(url_for('backup.manage_backup_restore'))


def _build_dataset_export_response(dataset_key):
    if dataset_key not in DATASET_CATALOG:
        flash('Dataset không hợp lệ.', 'danger')
        return redirect(url_for('backup.manage_backup_restore'))

    config = DATASET_CATALOG[dataset_key]

    try:
        payload = collect_dataset_payload(dataset_key)
        backup_folder = get_backup_folder()
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f'mindstack_{dataset_key}_dataset_{timestamp}.zip'
        file_path = os.path.join(backup_folder, filename)

        with zipfile.ZipFile(file_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            write_dataset_to_zip(zipf, dataset_key, payload)

        flash(
            f"Đã xuất dữ liệu '{config['label']}' và lưu thành công dưới tên file {filename}.",
            'success',
        )
    except Exception as exc:
        current_app.logger.error('Lỗi khi xuất dataset %s: %s', dataset_key, exc)
        flash(f'Lỗi khi xuất dữ liệu: {exc}', 'danger')

    return redirect(url_for('backup.manage_backup_restore'))


@blueprint.route('/export', methods=['POST'])
def export_dataset_from_form():
    dataset_key = request.form.get('dataset_key', '')
    if not dataset_key:
        flash('Vui lòng chọn gói dữ liệu cần xuất.', 'warning')
        return redirect(url_for('backup.manage_backup_restore'))

    return _build_dataset_export_response(dataset_key)


@blueprint.route('/export/<string:dataset_key>')
def export_dataset(dataset_key):
    return _build_dataset_export_response(dataset_key)


@blueprint.route('/restore/dataset', methods=['POST'])
def restore_dataset():
    file = request.files.get('dataset_file')
    if not file or not file.filename:
        flash('Vui lòng chọn file để khôi phục.', 'warning')
        return redirect(url_for('backup.manage_backup_restore'))

    try:
        if not (file.filename.endswith('.json') or file.filename.endswith('.zip')):
            flash('Định dạng file không hợp lệ. Vui lòng chọn file .json hoặc .zip.', 'warning')
            return redirect(url_for('backup.manage_backup_restore'))

        file_bytes = file.read()
        file_name = file.filename
        
        result = restore_from_uploaded_bytes(file_bytes, file_name)
        
        if result.get('success'):
             flash(f"Khôi phục dữ liệu thành công: {result.get('message')}", 'success')
        else:
             flash(f"Lỗi khôi phục: {result.get('error')}", 'danger')

    except Exception as e:
        current_app.logger.error(f"Restore error: {e}")
        flash(f"Đã xảy ra lỗi khi khôi phục: {str(e)}", 'danger')

    return redirect(url_for('backup.manage_backup_restore'))


@blueprint.route('/restore', methods=['POST'])
def restore_backup():
    filename = request.form.get('filename')
    
    if not filename:
        flash('Không xác định được file sao lưu.', 'danger')
        return redirect(url_for('backup.manage_backup_restore'))
        
    backup_folder = get_backup_folder()
    file_path = safe_join(backup_folder, filename)
    
    if not file_path or not os.path.exists(file_path):
        flash('File sao lưu không tồn tại.', 'danger')
        return redirect(url_for('backup.manage_backup_restore'))

    try:
        # Read file bytes from server
        with open(file_path, 'rb') as f:
            file_bytes = f.read()
            
        # Use existing service function to handle restoration
        result = restore_from_uploaded_bytes(file_bytes, filename)
        
        if result.get('success'):
             flash(f"Khôi phục thành công: {result.get('message')}", 'success')
        else:
             flash(f"Lỗi khôi phục: {result.get('error')}", 'danger')

    except Exception as e:
        current_app.logger.error(f"Restore from server error: {e}")
        flash(f"Lỗi khi khôi phục: {str(e)}", 'danger')

    return redirect(url_for('backup.manage_backup_restore'))
