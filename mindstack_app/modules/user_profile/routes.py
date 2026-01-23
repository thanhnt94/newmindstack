# File: Mindstack/web/mindstack_app/modules/user_profile/routes.py
# Version: 1.0
# Mục đích: Chứa các route và logic cho việc quản lý profile cá nhân của người dùng.

from flask import render_template, redirect, url_for, flash, request
from mindstack_app.utils.template_helpers import render_dynamic_template
from flask_login import login_required, current_user

# Import Blueprint từ __init__.py của module này
from . import user_profile_bp 

from ...models import User # Import model User từ cấp trên (đi lên 2 cấp)
from ...db_instance import db
from ...modules.auth.forms import ProfileEditForm, ChangePasswordForm # Import specific forms

# Middleware để đảm bảo người dùng đã đăng nhập cho toàn bộ Blueprint user_profile
@user_profile_bp.before_request
@login_required # Đảm bảo người dùng đã đăng nhập
def profile_required():
    # Không cần kiểm tra quyền admin ở đây, chỉ cần đã đăng nhập
    pass

# Route để xem profile cá nhân
@user_profile_bp.route('/')
@user_profile_bp.route('/view')
def view_profile():
    # current_user đã có sẵn nhờ Flask-Login
    # current_user đã có sẵn nhờ Flask-Login
    from mindstack_app.models import UserBadge
    badges = UserBadge.query.filter_by(user_id=current_user.user_id).join(UserBadge.badge).all()
    
    # Telegram Link
    try:
        from ...modules.telegram_bot.services import generate_connect_link
        telegram_link = generate_connect_link(current_user.user_id)
    except Exception as e:
        telegram_link = '#'
        print(f"Error generating telegram link: {e}")

    return render_dynamic_template('pages/user_profile/profile.html', user=current_user, badges=badges, telegram_link=telegram_link)

import os
from werkzeug.utils import secure_filename
from flask import current_app

# Route để chỉnh sửa profile cá nhân
@user_profile_bp.route('/edit', methods=['GET', 'POST'])
def edit_profile():
    user = current_user
    form = ProfileEditForm(obj=user)
    
    if form.validate_on_submit():
        from .services import UserProfileService
        
        user.username = form.username.data
        user.email = form.email.data
        user.timezone = form.timezone.data
        
        # Xử lý upload avatar qua Service
        if form.avatar.data:
            UserProfileService.update_avatar(user, form.avatar.data)
        
        db.session.commit()
        
        # Fire profile info update signal via service (cleaner)
        # Or we can let service handle all updates.
        # For now, routes does simple fields update + commit, service does file handling.
        # But wait, UserProfileService.update_profile_info logic exists too.
        # Let's pivot to use update_profile_info later if we want total purity.
        # For now, let's stick to cleaning up the noisy file upload part.
        
        flash('Thông tin profile đã được cập nhật thành công!', 'success')
        return redirect(url_for('user_profile.view_profile'))

    # Nếu là GET request, điền dữ liệu người dùng vào form
    elif request.method == 'GET':
        form.email.data = user.email
        form.timezone.data = user.timezone or 'UTC'

    return render_dynamic_template('pages/user_profile/edit_profile.html', form=form, title='Sửa Profile', user=user)

# Route để đổi mật khẩu
@user_profile_bp.route('/change-password', methods=['GET', 'POST'])
def change_password():
    form = ChangePasswordForm()
    if form.validate_on_submit():
        current_user.set_password(form.password.data)
        db.session.commit()
        flash('Mật khẩu đã được đổi thành công!', 'success')
        return redirect(url_for('user_profile.view_profile'))

    return render_dynamic_template('pages/user_profile/change_password.html', form=form, title='Đổi mật khẩu')

# Route API để lấy và lưu preferences
@user_profile_bp.route('/api/preferences', methods=['GET', 'POST'])
def manage_preferences():
    if request.method == 'POST':
        try:
            data = request.get_json()
            if not data:
                return {'success': False, 'message': 'No data provided'}, 400
            
            # Cập nhật preferences
            current_user.last_preferences = data
            
            # Nếu có flashcard_button_count, cập nhật luôn vào session state (nếu cần thiết cho tương thích ngược)
            if 'flashcard_button_count' in data:
                # Logic này có thể tùy chỉnh tùy theo model
                pass
                
            db.session.commit()
            return {'success': True, 'message': 'Preferences saved successfully'}
        except Exception as e:
            db.session.rollback()
            return {'success': False, 'message': str(e)}, 500
            
    # GET request
    prefs = current_user.last_preferences or {}
    
    # Đảm bảo các giá trị mặc định nếu chưa có
    default_prefs = {
        'flashcard_button_count': 4,
        'flashcard_show_image': True,
        'flashcard_autoplay_audio': True,
        'flashcard_show_stats': True,
        'quiz_question_count': 10,
        'auto_load_preferences': True
    }
    
    # Merge defaults với existing prefs
    final_prefs = {**default_prefs, **prefs}
    
    return {'success': True, 'data': final_prefs}
