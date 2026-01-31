# File: mindstack_app/modules/admin/routes/backup.py
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

@blueprint.route('/backup-restore')
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

@blueprint.route('/backup/database', methods=['POST'])
def create_database_backup():
    """
    Mô tả: Tạo bản sao lưu cơ sở dữ liệu và lưu trên máy chủ.
    """
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

    return redirect(url_for('admin.manage_backup_restore'))


@blueprint.route('/backup/files/<path:filename>')
def download_backup_file(filename):
    """
    Mô tả: Cho phép tải xuống một file sao lưu.
    """
    backup_folder = get_backup_folder()
    target_path = safe_join(backup_folder, filename)

    if not target_path or not os.path.isfile(target_path):
        flash('File sao lưu không tồn tại.', 'danger')
        return redirect(url_for('admin.manage_backup_restore'))

    return send_file(target_path, as_attachment=True, download_name=os.path.basename(target_path))


def _build_dataset_export_response(dataset_key):
    if dataset_key not in DATASET_CATALOG:
        flash('Dataset không hợp lệ.', 'danger')
        return redirect(url_for('admin.manage_backup_restore'))

    config = DATASET_CATALOG[dataset_key]

    try:
        payload = collect_dataset_payload(dataset_key)
        backup_folder = get_backup_folder()
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f'mindstack_{dataset_key}_dataset_{timestamp}.zip'
        file_path = os.path.join(backup_folder, filename)

        with zipfile.ZipFile(file_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            write_dataset_to_zip(zipf, dataset_key, payload) # Needed import

        flash(
            f"Đã xuất dữ liệu '{config['label']}' và lưu thành công dưới tên file {filename}.",
            'success',
        )
    except Exception as exc:
        current_app.logger.error('Lỗi khi xuất dataset %s: %s', dataset_key, exc)
        flash(f'Lỗi khi xuất dữ liệu: {exc}', 'danger')

    return redirect(url_for('admin.manage_backup_restore'))


@blueprint.route('/backup/export', methods=['POST'])
def export_dataset_from_form():
    dataset_key = request.form.get('dataset_key', '')
    if not dataset_key:
        flash('Vui lòng chọn gói dữ liệu cần xuất.', 'warning')
        return redirect(url_for('admin.manage_backup_restore'))

    return _build_dataset_export_response(dataset_key)


@blueprint.route('/backup/export/<string:dataset_key>')
def export_dataset(dataset_key):
    return _build_dataset_export_response(dataset_key)
