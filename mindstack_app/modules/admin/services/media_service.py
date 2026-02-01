# File: mindstack_app/modules/admin/services/media_service.py
import os
from flask import url_for
from datetime import datetime

ADMIN_ALLOWED_MEDIA_EXTENSIONS = {
    '.jpg', '.jpeg', '.png', '.gif', '.webp', '.svg', '.bmp', '.ico',
    '.mp3', '.wav', '.ogg', '.m4a', '.aac', '.flac', '.opus',
    '.mp4', '.webm', '.mov', '.mkv', '.avi', '.m4v',
    '.pdf', '.docx', '.pptx', '.xlsx', '.csv', '.txt', '.zip', '.rar', '.7z', '.json'
}

def format_file_size(num_bytes):
    """
    Mô tả: Định dạng kích thước file (bytes) thành chuỗi dễ đọc (KB, MB, GB).
    """
    units = ['B', 'KB', 'MB', 'GB', 'TB']
    size = float(num_bytes)
    for unit in units:
        if size < 1024.0 or unit == units[-1]:
            if unit == 'B':
                return f"{int(size)} {unit}"
            return f"{size:.1f} {unit}"
        size /= 1024.0
    return f"{size:.1f} PB"

def normalize_subpath(path_value):
    """
    Mô tả: Chuẩn hóa đường dẫn thư mục con, loại bỏ các ký tự nguy hiểm.
    """
    normalized = os.path.normpath(path_value or '').replace('\\', '/')
    if normalized in ('', '.', '/'):
        return ''
    if normalized.startswith('..'):
        raise ValueError('Đường dẫn không hợp lệ.')
    return normalized.strip('/')

def collect_directory_listing(base_dir, upload_root):
    """
    Mô tả: Lấy danh sách các thư mục và file trong một thư mục.
    """
    directories = []
    files = []

    if not os.path.isdir(base_dir):
        return directories, files

    for entry in os.scandir(base_dir):
        if entry.name.startswith('.'):
            continue
        relative = os.path.relpath(entry.path, upload_root).replace('\\', '/')
        if entry.is_dir():
            directories.append({
                'name': entry.name,
                'path': relative.strip('/'),
                'item_count': sum(1 for _ in os.scandir(entry.path)) if os.path.isdir(entry.path) else 0,
                'modified': datetime.fromtimestamp(entry.stat().st_mtime)
            })
        elif entry.is_file():
            stat = entry.stat()
            files.append({
                'name': entry.name,
                'path': relative,
                'url': url_for('media_uploads', filename=relative),
                'size': format_file_size(stat.st_size),
                'size_bytes': stat.st_size,
                'modified': datetime.fromtimestamp(stat.st_mtime),
                'extension': os.path.splitext(entry.name)[1].lower()
            })

    directories.sort(key=lambda item: item['name'].lower())
    files.sort(key=lambda item: item['modified'], reverse=True)
    return directories, files
