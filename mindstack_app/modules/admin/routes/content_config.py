from flask import render_template, request, flash, redirect, url_for, jsonify
from flask_login import login_required, current_user
from mindstack_app.models import User, AppSettings, db
from mindstack_app.core.defaults import DEFAULT_APP_CONFIGS
from .. import blueprint

def _get_setting_obj(key, description, data_type='int'):
    """Helper to build setting object for template."""
    # Fetch from DB first, then Default
    val = AppSettings.get(key, DEFAULT_APP_CONFIGS.get(key))
    default_val = DEFAULT_APP_CONFIGS.get(key)
    
    return {
        'key': key,
        'description': description,
        'data_type': data_type,
        'value': val,
        'default': default_val
    }

@blueprint.route('/content-config', methods=['GET'])
@login_required
def content_config_page():
    """
    Page to manage GENERAL content settings (Uploads, Access).
    Scoring has moved to 'scoring' module.
    FSRS has moved to 'fsrs' module.
    """
    if current_user.user_role != User.ROLE_ADMIN:
        flash('Permission denied', 'danger')
        return redirect(url_for('admin.admin_dashboard'))

    # --- Construct General Settings ---
    general_settings = {
        'uploads': {
            'label': 'Tải lên & Lưu trữ',
            'icon': 'fas fa-cloud-upload-alt',
            'settings': [
                _get_setting_obj('CONTENT_MAX_UPLOAD_SIZE', 'Kích thước file tối đa (MB)', 'int'),
                _get_setting_obj('CONTENT_ALLOWED_EXTENSIONS', 'Định dạng file cho phép', 'string'),
            ]
        },
        'access': {
            'label': 'Quyền truy cập & Chia sẻ',
            'icon': 'fas fa-share-alt',
            'settings': [
                _get_setting_obj('CONTENT_ENABLE_PUBLIC_SHARING', 'Cho phép chia sẻ công khai (Public Sharing)', 'json'),
            ]
        }
    }

    return render_template('admin/content_config.html', 
                           general_settings=general_settings,
                           active_page='content_config')

@blueprint.route('/content-config/save-general', methods=['POST'])
@login_required
def save_general_config():
    if current_user.user_role != User.ROLE_ADMIN:
        return jsonify({'success': False, 'message': 'Permission denied'}), 403
    
    data = request.get_json()
    settings = data.get('settings', {})
    
    try:
        for key, val in settings.items():
            AppSettings.set(key, val, category='content') 
        db.session.commit()
        return jsonify({'success': True, 'message': 'Đã lưu cấu hình chung.'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

@blueprint.route('/content-config/reset-general', methods=['POST'])
@login_required
def reset_general_config():
    if current_user.user_role != User.ROLE_ADMIN:
        return jsonify({'success': False, 'message': 'Permission denied'}), 403
        
    keys_to_reset = ['CONTENT_MAX_UPLOAD_SIZE', 'CONTENT_ALLOWED_EXTENSIONS', 'CONTENT_ENABLE_PUBLIC_SHARING']
    
    try:
        for k in keys_to_reset:
            setting = AppSettings.query.get(k)
            if setting:
                db.session.delete(setting)
        db.session.commit()
        return jsonify({'success': True, 'message': 'Đã khôi phục mặc định chung.'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500
