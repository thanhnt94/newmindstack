# File: mindstack_app/modules/admin/routes/settings.py
from flask import render_template, redirect, url_for, flash, request, current_app, jsonify
from flask_login import login_required, current_user
from sqlalchemy.orm.attributes import flag_modified
from mindstack_app.models import (
    db, AppSettings, User, LearningContainer, UserContainerState, LearningProgress,
    Note, ScoreLog, Feedback as UserFeedback, LearningItem
)
from .. import blueprint
from ..services.settings_service import (
    CORE_SETTING_KEYS,
    CORE_SETTING_FIELDS,
    SETTING_CATEGORY_LABELS,
    is_sensitive_setting,
    get_core_settings,
    get_grouped_core_settings,
    categorize_settings,
    refresh_runtime_settings,
    log_setting_change,
    parse_setting_value,
    validate_setting_value
)

@blueprint.route('/settings', methods=['GET', 'POST'])
def manage_system_settings():
    """
    Mô tả: Quản lý các cài đặt hệ thống.
    """
    maintenance_mode = AppSettings.get('MAINTENANCE_MODE', False)
    maintenance_end_time = AppSettings.get('MAINTENANCE_END_TIME', '')
        
    telegram_token_setting = AppSettings.query.get('telegram_bot_token')

    raw_settings = AppSettings.query.order_by(AppSettings.key.asc()).all()
    
    def _is_gamification_setting(key: str) -> bool:
        key_upper = key.upper()
        return (
            key_upper.startswith('FLASHCARD_') or
            key_upper.startswith('QUIZ_') or
            key_upper.startswith('COURSE_') or
            key_upper.startswith('VOCAB_') or
            key_upper.startswith('DAILY_LOGIN') or
            'SCORE' in key_upper or
            'BONUS' in key_upper or
            'POINTS' in key_upper
        )
    
    settings = [
        setting
        for setting in raw_settings
        if not is_sensitive_setting(setting.key) 
           and setting.key not in CORE_SETTING_KEYS 
           and setting.key != 'telegram_bot_token'
           and not _is_gamification_setting(setting.key)
    ]
    data_type_options = ['string', 'int', 'bool', 'path', 'json']
    category_order = ['paths']

    users = User.query.order_by(User.username.asc()).all()
    quiz_sets = (
        LearningContainer.query.filter_by(container_type='QUIZ_SET')
        .order_by(LearningContainer.title.asc())
        .all()
    )

    return render_template(
        'admin/system_settings.html',
        maintenance_mode=maintenance_mode,
        telegram_token_setting=telegram_token_setting,
        core_settings=get_core_settings(),
        grouped_core_settings=get_grouped_core_settings(),
        settings_by_category=categorize_settings(settings),
        category_order=category_order,
        category_labels=SETTING_CATEGORY_LABELS,
        data_type_options=data_type_options,
        users=users,
        quiz_sets=quiz_sets,
        maintenance_end_time=maintenance_end_time
    )

@blueprint.route('/settings', methods=['POST'])
def save_maintenance_mode():
    """Lưu chế độ bảo trì."""
    maintenance_mode = 'maintenance_mode' in request.form
    maintenance_end_time = request.form.get('maintenance_end_time', '')

    try:
        AppSettings.set('MAINTENANCE_MODE', maintenance_mode, category='system', description='Chế độ bảo trì')
        AppSettings.set('MAINTENANCE_END_TIME', maintenance_end_time, category='system', description='Thời gian kết thúc bảo trì')
        db.session.commit()
        
        refresh_runtime_settings()
        flash('Cài đặt hệ thống đã được cập nhật thành công!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Lỗi cập nhật: {str(e)}', 'danger')
        
    return redirect(url_for('admin.manage_system_settings'))


@blueprint.route('/settings/telegram-token', methods=['POST'])
def save_telegram_token():
    """Lưu Telegram Bot Token."""
    token_value = (request.form.get('value') or '').strip()
    
    setting = AppSettings.query.get('telegram_bot_token')
    old_value = setting.value if setting else None

    if setting:
        setting.value = token_value
        setting.data_type = 'string'
        flag_modified(setting, 'value')
    else:
        setting = AppSettings(
            key='telegram_bot_token',
            value=token_value,
            category='telegram',
            data_type='string',
            description='Telegram Bot API Token để gửi tin nhắn nhắc nhở.'
        )
        db.session.add(setting)
    
    db.session.commit()
    log_setting_change(
        "update", key="telegram_bot_token", old_value=old_value, new_value=token_value
    )
    refresh_runtime_settings()
    flash('Telegram Bot Token đã được lưu thành công!', 'success')
    return redirect(url_for('admin.manage_system_settings'))


@blueprint.route('/settings/core', methods=['POST'])
def update_core_settings():
    """Cập nhật nhanh các cấu hình vận hành quan trọng."""
    updated_count = 0
    pending_logs: list[tuple[str, object, object]] = []

    for field in CORE_SETTING_FIELDS:
        key = field["key"]
        data_type = str(field.get("data_type", "string")).lower()
        description = field.get("description")
        raw_value = request.form.get(key)

        if raw_value is None:
            continue

        try:
            parsed_value = parse_setting_value(raw_value, data_type, key=key)
            validate_setting_value(parsed_value, data_type, key=key)
        except ValueError as exc:
            flash(str(exc), 'danger')
            return redirect(url_for('admin.manage_system_settings'))

        setting = AppSettings.query.get(key)
        old_value = setting.value if setting else None

        if setting:
            setting.value = parsed_value
            setting.data_type = data_type
            setting.description = description
            flag_modified(setting, 'value')
        else:
            setting = AppSettings(
                key=key,
                value=parsed_value,
                category='system',
                data_type=data_type,
                description=description,
            )
            db.session.add(setting)

        pending_logs.append((key, old_value, parsed_value))
        updated_count += 1

    if updated_count:
        db.session.commit()
        for key, old_value, parsed_value in pending_logs:
            log_setting_change("update", key=key, old_value=old_value, new_value=parsed_value)
        refresh_runtime_settings()
        flash('Đã lưu cấu hình vận hành.', 'success')
    else:
        flash('Không có thay đổi nào được ghi nhận.', 'info')

    return redirect(url_for('admin.manage_system_settings'))


@blueprint.route('/settings/create', methods=['POST'])
def create_system_setting():
    key = (request.form.get('key') or '').strip().upper()
    value = request.form.get('value')
    data_type = (request.form.get('data_type') or 'string').lower()
    description = (request.form.get('description') or '').strip() or None

    if not key:
        flash('Khóa cấu hình không được bỏ trống.', 'danger')
        return redirect(url_for('admin.manage_system_settings'))

    if is_sensitive_setting(key):
        flash('Khóa cấu hình này được bảo vệ.', 'warning')
        return redirect(url_for('admin.manage_system_settings'))

    if AppSettings.query.get(key):
        flash('Khóa cấu hình đã tồn tại.', 'warning')
        return redirect(url_for('admin.manage_system_settings'))

    try:
        parsed_value = parse_setting_value(value, data_type, key=key)
        validate_setting_value(parsed_value, data_type, key=key)
    except ValueError as exc:
        flash(str(exc), 'danger')
        return redirect(url_for('admin.manage_system_settings'))

    setting = AppSettings(key=key, value=parsed_value, category='system', data_type=data_type, description=description)
    db.session.add(setting)
    db.session.commit()

    log_setting_change("create", key=key, old_value=None, new_value=parsed_value)
    refresh_runtime_settings()
    flash('Đã thêm cấu hình mới thành công.', 'success')
    return redirect(url_for('admin.manage_system_settings'))


@blueprint.route('/settings/<string:setting_key>/update', methods=['POST'])
def update_system_setting(setting_key):
    setting = AppSettings.query.get_or_404(setting_key)

    if is_sensitive_setting(setting.key):
        flash('Khóa cấu hình này được bảo vệ.', 'danger')
        return redirect(url_for('admin.manage_system_settings'))

    data_type = (request.form.get('data_type') or setting.data_type or 'string').lower()
    description = (request.form.get('description') or '').strip() or None
    raw_value = request.form.get('value')

    try:
        parsed_value = parse_setting_value(raw_value, data_type, key=setting.key)
        validate_setting_value(parsed_value, data_type, key=setting.key)
    except ValueError as exc:
        flash(str(exc), 'danger')
        return redirect(url_for('admin.manage_system_settings'))

    setting.data_type = data_type
    setting.description = description
    old_value = setting.value
    setting.value = parsed_value
    flag_modified(setting, 'value')

    db.session.commit()
    log_setting_change(
        "update", key=setting.key, old_value=old_value, new_value=parsed_value
    )
    refresh_runtime_settings()
    flash('Đã cập nhật cấu hình thành công.', 'success')
    return redirect(url_for('admin.manage_system_settings'))


@blueprint.route('/settings/<string:setting_key>/delete', methods=['POST'])
def delete_system_setting(setting_key):
    setting = AppSettings.query.get_or_404(setting_key)

    if is_sensitive_setting(setting.key):
        flash('Không thể xóa khóa cấu hình được bảo vệ.', 'danger')
        return redirect(url_for('admin.manage_system_settings'))

    old_value = setting.value
    db.session.delete(setting)
    db.session.commit()

    current_app.config.pop(setting.key, None)
    log_setting_change("delete", key=setting.key, old_value=old_value, new_value=None)
    refresh_runtime_settings()

    flash('Đã xóa cấu hình.', 'info')
    return redirect(url_for('admin.manage_system_settings'))


@blueprint.route('/settings/reset-progress', methods=['POST'])
def reset_learning_progress():
    reset_scope = (request.form.get('reset_scope') or '').strip()
    confirmation = (request.form.get('confirmation') or '').strip()

    if reset_scope == 'user':
        user_id_raw = request.form.get('user_id')
        if not user_id_raw:
            flash('Vui lòng chọn người dùng.', 'warning')
            return redirect(url_for('admin.manage_system_settings'))

        try:
            user_id = int(user_id_raw)
        except (TypeError, ValueError):
            flash('ID người dùng không hợp lệ.', 'danger')
            return redirect(url_for('admin.manage_system_settings'))

        user = User.query.get(user_id)
        if not user:
            flash('Không tìm thấy người dùng.', 'danger')
            return redirect(url_for('admin.manage_system_settings'))

        expected_confirmation = f"RESET USER {user.username}"
        if confirmation != expected_confirmation:
            flash(f"Xác nhận sai. Cần nhập: '{expected_confirmation}'", 'warning')
            return redirect(url_for('admin.manage_system_settings'))

        # Reset logic
        UserContainerState.query.filter_by(user_id=user.user_id).delete(synchronize_session=False)
        LearningProgress.query.filter_by(user_id=user.user_id).delete(synchronize_session=False)
        Note.query.filter_by(user_id=user.user_id).delete(synchronize_session=False)
        UserFeedback.query.filter_by(user_id=user.user_id).delete(synchronize_session=False)
        ScoreLog.query.filter_by(user_id=user.user_id).delete(synchronize_session=False)

        user.total_score = 0
        db.session.commit()
        flash(f"Đã đặt lại tiến độ của {user.username}.", 'success')
        return redirect(url_for('admin.manage_system_settings'))

    if reset_scope == 'container':
        container_id_raw = request.form.get('container_id')
        if not container_id_raw:
            flash('Vui lòng chọn bộ câu hỏi.', 'warning')
            return redirect(url_for('admin.manage_system_settings'))

        try:
            container_id = int(container_id_raw)
        except (TypeError, ValueError):
            flash('ID không hợp lệ.', 'danger')
            return redirect(url_for('admin.manage_system_settings'))

        container = LearningContainer.query.get(container_id)
        if not container:
            flash('Không tìm thấy bộ câu hỏi.', 'danger')
            return redirect(url_for('admin.manage_system_settings'))

        expected_confirmation = f"RESET CONTAINER {container.container_id}"
        if confirmation != expected_confirmation:
            flash(f"Xác nhận sai. Cần nhập: '{expected_confirmation}'", 'warning')
            return redirect(url_for('admin.manage_system_settings'))

        item_subquery = db.session.query(LearningItem.item_id).filter(LearningItem.container_id == container.container_id).subquery()

        LearningProgress.query.filter(LearningProgress.item_id.in_(item_subquery)).delete(synchronize_session=False)
        Note.query.filter(
            (Note.reference_type == 'item') & Note.reference_id.in_(item_subquery) |
            (Note.reference_type == 'container') & (Note.reference_id == container.container_id)
        ).delete(synchronize_session=False)
        UserFeedback.query.filter(UserFeedback.item_id.in_(item_subquery)).delete(synchronize_session=False)
        ScoreLog.query.filter(ScoreLog.item_id.in_(item_subquery)).delete(synchronize_session=False)
        UserContainerState.query.filter_by(container_id=container.container_id).delete(synchronize_session=False)

        db.session.commit()
        flash(f"Đã đặt lại tiến độ cho bộ '{container.title}'.", 'success')
        return redirect(url_for('admin.manage_system_settings'))

    flash('Phạm vi không hợp lệ.', 'danger')
    return redirect(url_for('admin.manage_system_settings'))


@blueprint.route('/settings/browse-directories', methods=['GET'])
@login_required
def browse_directories_api():
    """
    API to browse server directories.
    Query Params:
        path: current path to list (default: root)
    """
    import os
    if current_user.user_role != User.ROLE_ADMIN:
        return jsonify({'success': False, 'message': 'Permission denied'}), 403

    current_path = request.args.get('path', 'C:\\')
    
    # Basic security check to prevent traversing up too far if needed (optional for admin)
    # if '..' in current_path:
    #     return jsonify({'success': False, 'message': 'Invalid path'}), 400

    if not os.path.exists(current_path) or not os.path.isdir(current_path):
        return jsonify({'success': False, 'message': 'Path not found'}), 404

    try:
        items = []
        with os.scandir(current_path) as it:
            for entry in it:
                if entry.is_dir():
                    items.append({
                        'name': entry.name,
                        'path': entry.path,
                        'type': 'directory'
                    })
        
        # Sort by name
        items.sort(key=lambda x: x['name'].lower())
        
        # Add parent directory option if not at root
        parent_path = os.path.dirname(current_path)
        if parent_path and parent_path != current_path:
             items.insert(0, {
                'name': '..',
                'path': parent_path,
                'type': 'directory'
            })

        return jsonify({
            'success': True,
            'current_path': current_path,
            'items': items
        })

    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


@blueprint.route('/settings/create-directory', methods=['POST'])
@login_required
def create_directory_api():
    """
    API to create a new directory.
    JSON Body:
        parent_path: parent path
        folder_name: new folder name
    """
    import os
    if current_user.user_role != User.ROLE_ADMIN:
        return jsonify({'success': False, 'message': 'Permission denied'}), 403

    data = request.get_json()
    if not data:
         return jsonify({'success': False, 'message': 'No data provided'}), 400

    parent_path = data.get('parent_path')
    folder_name = data.get('folder_name')

    if not parent_path or not folder_name:
        return jsonify({'success': False, 'message': 'Missing path or name'}), 400

    new_path = os.path.join(parent_path, folder_name)

    if os.path.exists(new_path):
        return jsonify({'success': False, 'message': 'Directory already exists'}), 400

    try:
        os.makedirs(new_path)
        return jsonify({
            'success': True,
            'message': 'Directory created successfully',
            'path': new_path
        })
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500
