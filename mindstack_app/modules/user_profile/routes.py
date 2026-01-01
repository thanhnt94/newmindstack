# File: Mindstack/web/mindstack_app/modules/user_profile/routes.py
# Version: 1.0
# Mục đích: Chứa các route và logic cho việc quản lý profile cá nhân của người dùng.

from flask import render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user

# Import Blueprint từ __init__.py của module này
from . import user_profile_bp 

from ...models import User # Import model User từ cấp trên (đi lên 2 cấp)
from ...db_instance import db
from ...modules.auth.forms import UserForm # Sử dụng lại UserForm cho việc sửa profile

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
    from ...modules.gamification.models import UserBadge
    badges = UserBadge.query.filter_by(user_id=current_user.user_id).join(UserBadge.badge).all()
    
    # Telegram Link
    try:
        from ...modules.telegram_bot.services import generate_connect_link
        telegram_link = generate_connect_link(current_user.user_id)
    except Exception as e:
        telegram_link = '#'
        print(f"Error generating telegram link: {e}")

    return render_template('v3/pages/user_profile/profile.html', user=current_user, badges=badges, telegram_link=telegram_link)

# Route để chỉnh sửa profile cá nhân
@user_profile_bp.route('/edit', methods=['GET', 'POST'])
def edit_profile():
    user = current_user # Người dùng chỉ có thể sửa profile của chính mình
    form = UserForm(obj=user)
    # Gán user object vào form để validate_username có thể sử dụng user_id để loại trừ
    form.user = user 
    
    if form.validate_on_submit():
        user.username = form.username.data
        user.email = form.email.data
        user.timezone = form.timezone.data
        # Không cho phép người dùng tự đổi user_role của mình
        # user.user_role = form.user_role.data
        
        # Chỉ cập nhật mật khẩu nếu người dùng nhập mật khẩu mới
        if form.password.data:
            # Kiểm tra mật khẩu khớp nếu có nhập mật khẩu mới
            if form.password.data != form.password2.data:
                form.password2.errors.append('Mật khẩu không khớp.')
                return render_template('v3/pages/user_profile/edit_profile.html', form=form, title='Sửa Profile', user=user)
            user.set_password(form.password.data)
        
        db.session.commit()
        flash('Thông tin profile đã được cập nhật thành công!', 'success')
        return redirect(url_for('user_profile.view_profile'))
    
    # Nếu là GET request, điền dữ liệu người dùng vào form
    elif request.method == 'GET':
        # Ẩn trường user_role khi người dùng tự sửa profile
        # form.user_role.data = user.user_role
        form.email.data = user.email
        form.timezone.data = user.timezone or 'UTC' # Default to UTC if not set

    return render_template('v3/pages/user_profile/edit_profile.html', form=form, title='Sửa Profile', user=user)

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
