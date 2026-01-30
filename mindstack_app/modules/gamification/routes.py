"""
Gamification Routes
Routes quản trị cho hệ thống điểm số và huy hiệu.
"""
from flask import render_template, request, redirect, url_for, flash, current_app
from flask_login import login_required, current_user
from . import blueprint
from mindstack_app.models import Badge
from mindstack_app.models import db, AppSettings
from mindstack_app.core.extensions import csrf_protect


@blueprint.route('/points')
@login_required
def gamification_points():
    """Hiển thị trang cấu hình điểm số."""
    if current_user.user_role != 'admin':
        flash('Bạn không có quyền truy cập.', 'error')
        return redirect(url_for('dashboard.dashboard'))
    
    from mindstack_app.core.defaults import DEFAULT_APP_CONFIGS
    return render_template('admin/admin_gamification/points_settings.html', 
                          active_tab='points', 
                          config=current_app.config, 
                          defaults=DEFAULT_APP_CONFIGS,
                          active_page='badges')


@blueprint.route('/points/update', methods=['POST'])
@login_required
@csrf_protect.exempt
def update_gamification_points():
    """Cập nhật các giá trị cấu hình điểm số."""
    if current_user.user_role != 'admin':
        return redirect(url_for('dashboard.dashboard'))
    
    try:
        updated_count = 0
        for key, value in request.form.items():
            # Chỉ xử lý các key viết hoa (convention cho config)
            if not key.isupper():
                continue
            
            # Tìm setting trong DB
            setting = AppSettings.query.get(key)
            if setting:
                # Basic type conversion based on inferred type or try int
                if setting.data_type == 'int':
                    try:
                        setting.value = int(value)
                    except ValueError:
                        setting.value = 0  # Fallback
                elif setting.data_type == 'bool':
                    setting.value = (value.lower() in ['true', '1', 'on'])
                else:
                    setting.value = value
                
                updated_count += 1
            else:
                current_app.logger.warning(f"Setting key {key} not found in DB during update.")

        db.session.commit()
        
        # Reload config ngay lập tức
        if 'config_service' in current_app.extensions:
            current_app.extensions['config_service'].load_settings(force=True)

        flash(f'Đã cập nhật {updated_count} cấu hình điểm số.', 'success')
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error updating gamification points: {e}")
        flash('Có lỗi xảy ra khi lưu cấu hình.', 'error')

    return redirect(url_for('gamification.gamification_points'))


@blueprint.route('/badges')
@login_required
def list_badges():
    """Hiển thị danh sách huy hiệu."""
    if current_user.user_role != 'admin':
        flash('Bạn không có quyền truy cập.', 'error')
        return redirect(url_for('dashboard.dashboard'))
        
    badges = Badge.query.order_by(Badge.created_at.desc()).all()
    return render_template('admin/admin_gamification/badges_list.html', badges=badges, active_tab='badges', active_page='badges')


@blueprint.route('/badges/new', methods=['GET', 'POST'])
@login_required
def create_badge():
    """Tạo huy hiệu mới."""
    if current_user.user_role != 'admin':
        return redirect(url_for('dashboard.dashboard'))

    if request.method == 'POST':
        try:
            name = request.form.get('name')
            condition_type = request.form.get('condition_type')
            condition_value = int(request.form.get('condition_value', 0))
            reward_points = int(request.form.get('reward_points', 0))
            
            badge = Badge(
                name=name,
                description=request.form.get('description'),
                icon_class=request.form.get('icon_class', 'fas fa-medal'),
                condition_type=condition_type,
                condition_value=condition_value,
                reward_points=reward_points,
                is_active=bool(request.form.get('is_active'))
            )
            db.session.add(badge)
            db.session.commit()
            flash('Tạo huy hiệu thành công!', 'success')
            return redirect(url_for('gamification.list_badges'))
        except Exception as e:
            db.session.rollback()
            flash(f'Lỗi: {str(e)}', 'error')

    return render_template('admin/admin_gamification/badge_form.html', badge=None)


@blueprint.route('/badges/<int:badge_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_badge(badge_id):
    """Sửa huy hiệu."""
    if current_user.user_role != 'admin':
        return redirect(url_for('dashboard.dashboard'))
        
    badge = Badge.query.get_or_404(badge_id)
    
    if request.method == 'POST':
        try:
            badge.name = request.form.get('name')
            badge.description = request.form.get('description')
            badge.icon_class = request.form.get('icon_class')
            badge.condition_type = request.form.get('condition_type')
            badge.condition_value = int(request.form.get('condition_value', 0))
            badge.reward_points = int(request.form.get('reward_points', 0))
            badge.is_active = bool(request.form.get('is_active'))
            
            db.session.commit()
            flash('Cập nhật huy hiệu thành công!', 'success')
            return redirect(url_for('gamification.list_badges'))
        except Exception as e:
            db.session.rollback()
            flash(f'Lỗi: {str(e)}', 'error')
            
    return render_template('admin/admin_gamification/badge_form.html', badge=badge)


@blueprint.route('/badges/<int:badge_id>/delete', methods=['POST'])
@login_required
def delete_badge(badge_id):
    """Xóa huy hiệu."""
    if current_user.user_role != 'admin':
        return redirect(url_for('dashboard.dashboard'))
    
    badge = Badge.query.get_or_404(badge_id)
    try:
        db.session.delete(badge)
        db.session.commit()
        flash('Đã xóa huy hiệu.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Lỗi: {str(e)}', 'error')
        
    return redirect(url_for('gamification.list_badges'))
