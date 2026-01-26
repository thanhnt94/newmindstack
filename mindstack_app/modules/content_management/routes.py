# File: newmindstack/mindstack_app/modules/content_management/routes.py
# Phiên bản: 2.2
# ĐÃ SỬA: Khắc phục lỗi 404 bằng cách loại bỏ url_prefix khi đăng ký các blueprint con.

from flask import Blueprint, render_template, request, redirect, url_for, flash, abort, jsonify, current_app
from mindstack_app.utils.template_helpers import render_dynamic_template
from flask_login import login_required, current_user
from sqlalchemy import or_, func
from ...models import db, LearningContainer, ContainerContributor, User
from .forms import ContributorForm # SỬA: Import form mới
from werkzeug.utils import secure_filename
from uuid import uuid4
import os

from ...config import Config
from ...services.config_service import get_runtime_config

from .courses.routes import courses_bp
from .flashcards.routes import flashcards_bp
from .quizzes.routes import quizzes_bp
from ...core.error_handlers import error_response, success_response

# Định nghĩa Blueprint chính cho content_management
content_management_bp = Blueprint('content_management', __name__,
                                  template_folder='templates') # Vẫn giữ template_folder này cho các template chung

# Đăng ký các blueprint con
# ĐÃ SỬA: Loại bỏ url_prefix vì các routes con đã tự định nghĩa đường dẫn đầy đủ
content_management_bp.register_blueprint(courses_bp)
content_management_bp.register_blueprint(flashcards_bp)
content_management_bp.register_blueprint(quizzes_bp)


def _select_media_subdir(media_type: str) -> str:
    media_type = (media_type or 'file').lower()
    if media_type == 'image':
        return 'images'
    if media_type == 'media':
        return 'media'
    return 'files'


@content_management_bp.route('/media/upload', methods=['POST'])
@login_required
def upload_rich_text_media():
    """Tải file media sử dụng trong trình soạn thảo WYSIWYG."""

    if current_user.user_role == User.ROLE_FREE:
        return error_response('Tài khoản của bạn không có quyền tải media.', 'FORBIDDEN', 403)

    upload_root = get_runtime_config('UPLOAD_FOLDER', Config.UPLOAD_FOLDER)
    if not upload_root:
        current_app.logger.error('UPLOAD_FOLDER chưa được cấu hình.')
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
    ext = os.path.splitext(filename)[1].lower()
    if ext not in ALLOWED_RICH_TEXT_EXTENSIONS:
        return error_response(f'Định dạng file "{ext}" không được hỗ trợ.', 'BAD_REQUEST', 400)

    media_type = request.form.get('media_type', 'file')
    target_dir = os.path.join(upload_root, 'content', _select_media_subdir(media_type))
    os.makedirs(target_dir, exist_ok=True)

    base_name = os.path.splitext(filename)[0]
    candidate_name = f"{base_name}_{uuid4().hex[:8]}{ext}"
    candidate_path = os.path.join(target_dir, candidate_name)
    while os.path.exists(candidate_path):
        candidate_name = f"{base_name}_{uuid4().hex[:8]}{ext}"
        candidate_path = os.path.join(target_dir, candidate_name)

    try:
        file.save(candidate_path)
    except Exception as exc:  # pragma: no cover - phòng lỗi IO hiếm gặp
        current_app.logger.exception('Không thể lưu file media: %s', exc)
        return error_response('Không thể lưu file media trên máy chủ.', 'SERVER_ERROR', 500)

    relative_path = os.path.relpath(candidate_path, upload_root).replace('\\', '/')
    file_url = url_for('static', filename=relative_path, _external=False)

    return success_response(message='File uploaded successfully', data={'location': file_url, 'filename': candidate_name})


@content_management_bp.route('/')
@login_required
def content_dashboard():
    """
    Hiển thị dashboard tổng quan về nội dung.
    """
    return render_dynamic_template('pages/content_management/index.html')

@content_management_bp.route('/manage_contributors/<int:container_id>', methods=['GET', 'POST'])
@login_required
def manage_contributors(container_id):
    """
    Quản lý người đóng góp cho một LearningContainer cụ thể.
    """
    container = LearningContainer.query.get_or_404(container_id)
    creator = container.creator
    if creator and creator.user_role == User.ROLE_FREE:
        abort(403)

    if current_user.user_role != 'admin' and container.creator_user_id != current_user.user_id:
        abort(403)

    form = ContributorForm()

    if form.validate_on_submit():
        username_to_add = (form.username.data or "").strip()
        permission_level = form.permission_level.data

        if not username_to_add:
            flash('Vui lòng nhập tên người dùng.', 'danger')
            return redirect(url_for('content_management.manage_contributors', container_id=container_id))

        user_to_add = User.query.filter(func.lower(User.username) == username_to_add.lower()).first()

        if not user_to_add:
            flash(f'Không tìm thấy người dùng với tên: {username_to_add}.', 'danger')
        elif user_to_add.user_id == container.creator_user_id:
            flash('Không thể thêm chính người tạo làm người đóng góp.', 'warning')
        elif user_to_add.user_role in {User.ROLE_FREE, User.ROLE_ANONYMOUS}:
            flash('Không thể thêm tài khoản miễn phí hoặc ẩn danh làm người đóng góp.', 'danger')
        else:
            existing_contributor = ContainerContributor.query.filter_by(
                container_id=container_id,
                user_id=user_to_add.user_id
            ).first()

            if existing_contributor:
                existing_contributor.permission_level = permission_level
                db.session.commit()
                flash(f'Cấp độ quyền của {user_to_add.username} đã được cập nhật.', 'info')
            else:
                new_contributor = ContainerContributor(
                    container_id=container_id,
                    user_id=user_to_add.user_id,
                    permission_level=permission_level
                )
                db.session.add(new_contributor)
                db.session.commit()
                flash(f'{user_to_add.username} đã được thêm làm người đóng góp!', 'success')
        
        return redirect(url_for('content_management.manage_contributors', container_id=container_id))

    # Xử lý xóa người đóng góp (giữ nguyên logic cũ)
    if request.method == 'POST' and 'remove_contributor_id' in request.form:
        remove_id = request.form.get('remove_contributor_id')
        try:
            remove_id = int(remove_id)
            contributor_to_remove = ContainerContributor.query.filter_by(
                container_id=container_id,
                user_id=remove_id
            ).first()
            if contributor_to_remove:
                db.session.delete(contributor_to_remove)
                db.session.commit()
                flash(f'Người đóng góp đã bị xóa.', 'success')
            else:
                flash('Không tìm thấy người đóng góp này.', 'danger')
        except ValueError:
            flash('ID người đóng góp không hợp lệ.', 'danger')
        return redirect(url_for('content_management.manage_contributors', container_id=container_id))

    contributors = db.session.query(ContainerContributor, User).join(User).filter(
        ContainerContributor.container_id == container_id
    ).all()

    ineligible_roles = (User.ROLE_FREE, User.ROLE_ANONYMOUS)
    eligible_usernames = (
        User.query
        .filter(~User.user_role.in_(ineligible_roles))
        .order_by(User.username.asc())
        .with_entities(User.username)
        .all()
    )
    username_suggestions = [username for (username,) in eligible_usernames]

    return render_dynamic_template('pages/content_management/manage_contributors.html',
                           container=container,
                           contributors=contributors,
                           form=form,
                           username_suggestions=username_suggestions)

@content_management_bp.route('/api/contributors/<int:container_id>/add', methods=['POST'])
@login_required
def add_contributor_api(container_id):
    container = LearningContainer.query.get_or_404(container_id)
    if current_user.user_role != 'admin' and container.creator_user_id != current_user.user_id:
        return {'success': False, 'message': 'Permission denied'}, 403

    data = request.get_json() or {}
    username = (data.get('username') or "").strip()
    permission_level = data.get('permission_level', 'editor')

    if not username:
        return {'success': False, 'message': 'Vui lòng nhập tên người dùng'}, 400

    user_to_add = User.query.filter(func.lower(User.username) == username.lower()).first()

    if not user_to_add:
        return {'success': False, 'message': f'Không tìm thấy người dùng: {username}'}, 404
    if user_to_add.user_id == container.creator_user_id:
        return {'success': False, 'message': 'Không thể thêm người tạo'}, 400
    if user_to_add.user_role in {User.ROLE_FREE, User.ROLE_ANONYMOUS}:
        return {'success': False, 'message': 'Chỉ dành cho tài khoản trả phí'}, 400

    existing = ContainerContributor.query.filter_by(container_id=container_id, user_id=user_to_add.user_id).first()
    if existing:
        existing.permission_level = permission_level
        msg = f"Đã cập nhật quyền cho {user_to_add.username}"
    else:
        new_c = ContainerContributor(container_id=container_id, user_id=user_to_add.user_id, permission_level=permission_level)
        db.session.add(new_c)
        msg = f"Đã thêm {user_to_add.username}"
    
    db.session.commit()
    return {'success': True, 'message': msg, 'username': user_to_add.username, 'email': user_to_add.email, 'user_id': user_to_add.user_id}

@content_management_bp.route('/api/contributors/<int:container_id>/remove', methods=['POST'])
@login_required
def remove_contributor_api(container_id):
    container = LearningContainer.query.get_or_404(container_id)
    if current_user.user_role != 'admin' and container.creator_user_id != current_user.user_id:
        return {'success': False, 'message': 'Permission denied'}, 403

    data = request.get_json() or {}
    user_id = data.get('user_id')
    contributor = ContainerContributor.query.filter_by(container_id=container_id, user_id=user_id).first()
    if not contributor:
         return {'success': False, 'message': 'Không tìm thấy người đóng góp'}, 404

    db.session.delete(contributor)
    db.session.commit()
    return {'success': True, 'message': 'Đã xóa quyền'}

ALLOWED_RICH_TEXT_EXTENSIONS = {
    '.jpg', '.jpeg', '.png', '.gif', '.webp', '.svg', '.bmp',
    '.mp3', '.wav', '.ogg', '.m4a', '.aac', '.flac',
    '.mp4', '.webm', '.mov', '.mkv', '.avi',
    '.pdf', '.docx', '.pptx', '.xlsx', '.zip', '.rar', '.txt'
}

