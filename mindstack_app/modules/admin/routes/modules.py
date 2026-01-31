# File: mindstack_app/modules/admin/routes/modules.py
from flask import render_template, abort, request, jsonify
from flask_login import login_required, current_user
from mindstack_app.models import db, User, AppSettings
from mindstack_app.core.module_registry import DEFAULT_MODULES
from .. import blueprint

@blueprint.route('/modules', methods=['GET'])
@login_required
def manage_modules():
    """Hiển thị danh sách các modules và trạng thái bật/tắt."""
    if current_user.user_role != User.ROLE_ADMIN:
        abort(403)

    modules_data = []
    for mod in DEFAULT_MODULES:
        is_core = mod.config_key in ['admin', 'auth', 'landing']
        is_active = AppSettings.get(f"MODULE_ENABLED_{mod.config_key}", True) if not is_core else True
        
        modules_data.append({
            'key': mod.config_key,
            'name': mod.display_name or mod.config_key,
            'import_path': mod.import_path,
            'is_active': is_active,
            'is_core': is_core
        })

    return render_template('admin/manage_modules.html', 
                           modules=modules_data, 
                           active_page='modules')


@blueprint.route('/modules/toggle', methods=['POST'])
@login_required
def toggle_module():
    """API để bật/tắt một module."""
    if current_user.user_role != User.ROLE_ADMIN:
        return jsonify({'success': False, 'message': 'Permission denied'}), 403

    data = request.get_json()
    module_key = data.get('key')
    
    if not module_key:
        return jsonify({'success': False, 'message': 'Missing module key'}), 400

    if module_key in ['admin', 'auth', 'landing']:
        return jsonify({'success': False, 'message': 'Không thể tắt module hệ thống cốt lõi'}), 400

    current_state = AppSettings.get(f"MODULE_ENABLED_{module_key}", True)
    new_state = not current_state
    
    AppSettings.set(f"MODULE_ENABLED_{module_key}", new_state, user_id=current_user.user_id)
    db.session.commit()
    
    return jsonify({
        'success': True, 
        'new_state': new_state,
        'message': f"Đã {'bật' if new_state else 'tắt'} module {module_key}"
    })
