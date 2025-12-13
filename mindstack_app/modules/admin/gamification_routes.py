from flask import render_template, request, redirect, url_for, flash, current_app
from flask_login import login_required, current_user
from . import admin_bp
from ...modules.gamification.models import Badge
from ...models import db

@admin_bp.route('/gamification/badges')
@login_required
def list_badges():
    """Hiển thị danh sách huy hiệu."""
    if current_user.user_role != 'admin':
        flash('Bạn không có quyền truy cập.', 'error')
        return redirect(url_for('dashboard'))
        
    badges = Badge.query.order_by(Badge.created_at.desc()).all()
    return render_template('admin_gamification/badges_list.html', badges=badges)

@admin_bp.route('/gamification/badges/new', methods=['GET', 'POST'])
@login_required
def create_badge():
    """Tạo huy hiệu mới."""
    if current_user.user_role != 'admin':
        return redirect(url_for('dashboard'))

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
            return redirect(url_for('admin.list_badges'))
        except Exception as e:
            db.session.rollback()
            flash(f'Lỗi: {str(e)}', 'error')

    return render_template('admin_gamification/badge_form.html', badge=None)

@admin_bp.route('/gamification/badges/<int:badge_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_badge(badge_id):
    """Sửa huy hiệu."""
    if current_user.user_role != 'admin':
        return redirect(url_for('dashboard'))
        
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
            return redirect(url_for('admin.list_badges'))
        except Exception as e:
            db.session.rollback()
            flash(f'Lỗi: {str(e)}', 'error')
            
    return render_template('admin_gamification/badge_form.html', badge=badge)

@admin_bp.route('/gamification/badges/<int:badge_id>/delete', methods=['POST'])
@login_required
def delete_badge(badge_id):
    """Xóa huy hiệu."""
    if current_user.user_role != 'admin':
        return redirect(url_for('dashboard'))
    
    badge = Badge.query.get_or_404(badge_id)
    try:
        db.session.delete(badge)
        db.session.commit()
        flash('Đã xóa huy hiệu.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Lỗi: {str(e)}', 'error')
        
    return redirect(url_for('admin.list_badges'))
