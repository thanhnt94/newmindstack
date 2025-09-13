# File: mindstack_app/modules/admin/api_key_management/routes.py
# Phiên bản: 1.0
# Mục đích: Chứa các route và logic cho việc quản lý API keys.

from flask import abort, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from . import api_key_management_bp
from .forms import ApiKeyForm
from ....models import db, ApiKey

@api_key_management_bp.before_request
@login_required
def admin_required():
    """
    Mô tả: Middleware để đảm bảo chỉ có admin mới truy cập được module này.
    """
    if current_user.user_role != 'admin':
        flash('Bạn không có quyền truy cập trang này.', 'danger')
        abort(403)

@api_key_management_bp.route('/')
def list_api_keys():
    """
    Mô tả: Hiển thị danh sách tất cả API key.
    """
    keys = ApiKey.query.order_by(ApiKey.key_id.asc()).all()
    return render_template('api_keys.html', keys=keys)

@api_key_management_bp.route('/add', methods=['GET', 'POST'])
def add_api_key():
    """
    Mô tả: Thêm một API key mới.
    """
    form = ApiKeyForm()
    if form.validate_on_submit():
        new_key = ApiKey(
            key_value=form.key_value.data,
            notes=form.notes.data,
            is_active=form.is_active.data,
            is_exhausted=False # Mới thêm thì chưa cạn kiệt
        )
        db.session.add(new_key)
        db.session.commit()
        flash('Đã thêm API key mới thành công!', 'success')
        return redirect(url_for('.list_api_keys'))
    return render_template('add_edit_api_key.html', form=form, title='Thêm API Key mới')

@api_key_management_bp.route('/edit/<int:key_id>', methods=['GET', 'POST'])
def edit_api_key(key_id):
    """
    Mô tả: Chỉnh sửa một API key đã có.
    """
    key = ApiKey.query.get_or_404(key_id)
    form = ApiKeyForm(obj=key)
    if form.validate_on_submit():
        key.key_value = form.key_value.data
        key.notes = form.notes.data
        key.is_active = form.is_active.data
        key.is_exhausted = form.is_exhausted.data
        db.session.commit()
        flash('Đã cập nhật thông tin API key!', 'success')
        return redirect(url_for('.list_api_keys'))
    return render_template('add_edit_api_key.html', form=form, title='Chỉnh sửa API Key')

@api_key_management_bp.route('/delete/<int:key_id>', methods=['POST'])
def delete_api_key(key_id):
    """
    Mô tả: Xóa một API key.
    """
    key = ApiKey.query.get_or_404(key_id)
    db.session.delete(key)
    db.session.commit()
    flash('Đã xóa API key thành công.', 'success')
    return redirect(url_for('.list_api_keys'))