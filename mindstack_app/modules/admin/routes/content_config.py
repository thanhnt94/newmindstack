from flask import render_template, request, flash, redirect, url_for
from flask_login import login_required, current_user
from mindstack_app.models import User, AppSettings, db
from sqlalchemy.orm.attributes import flag_modified
from .. import blueprint

@blueprint.route('/content-config', methods=['GET'])
@login_required
def content_config_page():
    """
    Page to manage content-related settings.
    """
    if current_user.user_role != User.ROLE_ADMIN:
        flash('Permission denied', 'danger')
        return redirect(url_for('admin.admin_dashboard'))

    # Retrieve current settings or defaults
    settings = {
        'CONTENT_MAX_UPLOAD_SIZE': AppSettings.get('CONTENT_MAX_UPLOAD_SIZE', 10),
        'CONTENT_ALLOWED_EXTENSIONS': AppSettings.get('CONTENT_ALLOWED_EXTENSIONS', 'jpg,png,mp3'),
        'CONTENT_ENABLE_PUBLIC_SHARING': AppSettings.get('CONTENT_ENABLE_PUBLIC_SHARING', False)
    }

    return render_template('admin/content_config.html', 
                           settings=settings,
                           active_page='content_config')

@blueprint.route('/content-config/save', methods=['POST'])
@login_required
def save_content_config():
    """
    Save content settings.
    """
    if current_user.user_role != User.ROLE_ADMIN:
        flash('Permission denied', 'danger')
        return redirect(url_for('admin.admin_dashboard'))

    try:
        AppSettings.set('CONTENT_MAX_UPLOAD_SIZE', int(request.form.get('CONTENT_MAX_UPLOAD_SIZE', 10)), category='content')
        AppSettings.set('CONTENT_ALLOWED_EXTENSIONS', request.form.get('CONTENT_ALLOWED_EXTENSIONS', ''), category='content')
        AppSettings.set('CONTENT_ENABLE_PUBLIC_SHARING', 'CONTENT_ENABLE_PUBLIC_SHARING' in request.form, category='content')
        
        db.session.commit()
        flash('Content configuration saved successfully.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error saving settings: {str(e)}', 'danger')

    return redirect(url_for('admin.content_config_page'))
