# File: mindstack_app/modules/content_management/routes/media.py
import os
from uuid import uuid4
from flask import request, current_app, url_for
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from mindstack_app.core.config import Config
from mindstack_app.services.config_service import get_runtime_config
from mindstack_app.core.error_handlers import error_response, success_response
from mindstack_app.models import User
from .. import blueprint
from ..config import ContentManagementModuleDefaultConfig

def _select_media_subdir(media_type: str) -> str:
    media_type = (media_type or 'file').lower()
    if media_type == 'image':
        return 'images'
    if media_type == 'media':
        return 'media'
    return 'files'

@blueprint.route('/media/upload', methods=['POST'])
@login_required
def upload_rich_text_media():
    """Tải file media sử dụng trong trình soạn thảo WYSIWYG."""
    if current_user.user_role == User.ROLE_FREE:
        return error_response('Tài khoản của bạn không có quyền tải media.', 'FORBIDDEN', 403)

    upload_root = get_runtime_config('UPLOAD_FOLDER', Config.UPLOAD_FOLDER)
    if not upload_root:
        return error_response('Máy chủ chưa cấu hình thư mục lưu trữ.', 'SERVER_ERROR', 500)

    if 'media_file' not in request.files:
        return error_response('Không tìm thấy file tải lên.', 'BAD_REQUEST', 400)

    file = request.files['media_file']
    if not file or file.filename == '':
        return error_response('Không có file nào được chọn.', 'BAD_REQUEST', 400)

    filename = secure_filename(file.filename)
    if not filename:
        return error_response('Tên file không hợp lệ.', 'BAD_REQUEST', 400)

    ext = os.path.splitext(filename)[1].lower()
    if ext not in ContentManagementModuleDefaultConfig.ALLOWED_RICH_TEXT_EXTENSIONS:
        return error_response(f'Định dạng file "{ext}" không được hỗ trợ.', 'BAD_REQUEST', 400)

    media_type = request.form.get('media_type', 'file')
    target_dir = os.path.join(upload_root, 'content', _select_media_subdir(media_type))
    os.makedirs(target_dir, exist_ok=True)

    base_name = os.path.splitext(filename)[0]
    candidate_name = f"{base_name}_{uuid4().hex[:8]}{ext}"
    candidate_path = os.path.join(target_dir, candidate_name)
    
    file.save(candidate_path)
    relative_path = os.path.relpath(candidate_path, upload_root).replace('\\', '/')
    file_url = url_for('media_uploads', filename=relative_path, _external=False)
    
    return success_response(message='File uploaded successfully', data={'location': file_url, 'filename': candidate_name})

@blueprint.route('/cover/upload', methods=['POST'])
@login_required
def upload_cover_image():
    """Tải ảnh bìa cho Course/Set vào thư mục covers."""
    if 'cover_file' not in request.files:
        return error_response('Không tìm thấy file.', 'BAD_REQUEST', 400)
    
    file = request.files['cover_file']
    if not file or file.filename == '':
        return error_response('Chưa chọn file.', 'BAD_REQUEST', 400)

    filename = secure_filename(file.filename)
    ext = os.path.splitext(filename)[1].lower()
    if ext not in {'.jpg', '.jpeg', '.png', '.webp'}:
        return error_response('Định dạng ảnh không hỗ trợ.', 'BAD_REQUEST', 400)

    covers_root = current_app.config['COVERS_FOLDER']
    os.makedirs(covers_root, exist_ok=True)
    
    new_filename = f"cover_{uuid4().hex[:12]}{ext}"
    target_path = os.path.join(covers_root, new_filename)
    
    file.save(target_path)
    db_path = f"covers/{new_filename}" 
    file_url = f"/media/{db_path}"
    
    return success_response(message='Đã tải ảnh bìa lên.', data={'url': file_url, 'db_path': db_path})
