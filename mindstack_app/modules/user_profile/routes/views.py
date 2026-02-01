# File: mindstack_app/modules/user_profile/routes/views.py
from flask import render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from mindstack_app.core.extensions import db
from mindstack_app.utils.template_helpers import render_dynamic_template
from ...auth.forms import ProfileEditForm, ChangePasswordForm
from .. import blueprint
from ..services import UserProfileService

@blueprint.before_request
@login_required
def profile_required():
    pass

@blueprint.route('/')
@blueprint.route('/view')
def view_profile():
    from mindstack_app.models import UserBadge
    badges = UserBadge.query.filter_by(user_id=current_user.user_id).join(UserBadge.badge).all()
    
    try:
        from ...telegram_bot.services import generate_connect_link
        telegram_link = generate_connect_link(current_user.user_id)
    except Exception as e:
        telegram_link = '#'
        print(f"Error generating telegram link: {e}")

    return render_dynamic_template('modules/user_profile/profile.html', user=current_user, badges=badges, telegram_link=telegram_link)

@blueprint.route('/edit', methods=['GET', 'POST'])
def edit_profile():
    user = current_user
    form = ProfileEditForm(obj=user)
    
    if form.validate_on_submit():
        user.username = form.username.data
        user.email = form.email.data
        user.timezone = form.timezone.data
        
        if form.avatar.data:
            UserProfileService.update_avatar(user, form.avatar.data)
        
        db.session.commit()
        
        flash('Thông tin profile đã được cập nhật thành công!', 'success')
        return redirect(url_for('user_profile.view_profile'))

    elif request.method == 'GET':
        form.email.data = user.email
        form.timezone.data = user.timezone or 'UTC'

    return render_dynamic_template('modules/user_profile/edit_profile.html', form=form, title='Sửa Profile', user=user)

@blueprint.route('/change-password', methods=['GET', 'POST'])
def change_password():
    form = ChangePasswordForm()
    if form.validate_on_submit():
        current_user.set_password(form.password.data)
        db.session.commit()
        flash('Mật khẩu đã được đổi thành công!', 'success')
        return redirect(url_for('user_profile.view_profile'))

    return render_dynamic_template('modules/user_profile/change_password.html', form=form, title='Đổi mật khẩu')
