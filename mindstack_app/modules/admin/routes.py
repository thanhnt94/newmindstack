# File: Mindstack/web/mindstack_app/modules/admin/routes.py
# Version: 2.2
# Mục đích: Chứa các route và logic cho bảng điều khiển admin tổng quan.
# ĐÃ THÊM: Route mới để quản lý các tác vụ nền.

from flask import render_template, redirect, url_for, flash, abort, jsonify, request
from flask_login import login_required, current_user
from sqlalchemy import or_
from ...models import db, User, LearningContainer, LearningItem, ApiKey, BackgroundTask
from datetime import datetime, timedelta
import asyncio

# THÊM MỚI: Import AudioService
from ..learning.flashcard_learning.audio_service import AudioService
audio_service = AudioService()

from . import admin_bp # Vẫn cần dòng này để các decorator như @admin_bp.route hoạt động chính xác.

# Middleware để kiểm tra quyền admin cho toàn bộ Blueprint admin
@admin_bp.before_request 
@login_required 
def admin_required():
    if not current_user.is_authenticated or current_user.user_role != 'admin':
        flash('Bạn không có quyền truy cập khu vực quản trị.', 'danger')
        abort(403) 

@admin_bp.route('/')
@admin_bp.route('/dashboard')
def admin_dashboard():
    # Lấy các chỉ số thống kê
    total_users = db.session.query(User).count()
    users_last_24h = db.session.query(User).filter(User.last_seen >= (datetime.utcnow() - timedelta(hours=24))).count()
    
    total_containers = db.session.query(LearningContainer).count()
    total_items = db.session.query(LearningItem).count()
    
    active_api_keys = db.session.query(ApiKey).filter_by(is_active=True, is_exhausted=False).count()
    exhausted_api_keys = db.session.query(ApiKey).filter_by(is_exhausted=True).count()
    
    # Tạo một dictionary chứa các dữ liệu thống kê
    stats_data = {
        'total_users': total_users,
        'users_last_24h': users_last_24h,
        'total_containers': total_containers,
        'total_items': total_items,
        'active_api_keys': active_api_keys,
        'exhausted_api_keys': exhausted_api_keys
    }

    return render_template('dashboard.html', stats_data=stats_data)

@admin_bp.route('/tasks')
def manage_background_tasks():
    """
    Mô tả: Hiển thị trang quản lý các tác vụ nền.
    """
    tasks = BackgroundTask.query.all()
    if not tasks:
        # Nếu chưa có tác vụ nào, tạo các tác vụ mặc định
        task1 = BackgroundTask(task_name='generate_audio_cache', message='Sẵn sàng', is_enabled=True)
        task2 = BackgroundTask(task_name='clean_audio_cache', message='Sẵn sàng', is_enabled=True)
        db.session.add_all([task1, task2])
        db.session.commit()
        tasks = BackgroundTask.query.all()
        
    return render_template('background_tasks.html', tasks=tasks)

@admin_bp.route('/tasks/toggle/<int:task_id>', methods=['POST'])
def toggle_task(task_id):
    """
    Mô tả: Bật/tắt một tác vụ nền.
    """
    task = BackgroundTask.query.get_or_404(task_id)
    task.is_enabled = not task.is_enabled
    db.session.commit()
    return jsonify({'success': True, 'is_enabled': task.is_enabled})

@admin_bp.route('/tasks/start/<int:task_id>', methods=['POST'])
def start_task(task_id):
    """
    Mô tả: Bắt đầu một tác vụ nền.
    """
    task = BackgroundTask.query.get_or_404(task_id)
    if task.status != 'running' and task.is_enabled:
        task.status = 'running'
        task.message = 'Đang khởi chạy...'
        db.session.commit()
        
        # Chạy tác vụ trong một thread hoặc process riêng
        if task.task_name == 'generate_audio_cache':
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(audio_service.generate_cache_for_all_cards(task))
        elif task.task_name == 'clean_audio_cache':
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(audio_service.clean_orphan_audio_cache(task))
            
    return jsonify({'success': True})

@admin_bp.route('/tasks/stop/<int:task_id>', methods=['POST'])
def stop_task(task_id):
    """
    Mô tả: Dừng một tác vụ nền đang chạy.
    """
    task = BackgroundTask.query.get_or_404(task_id)
    if task.status == 'running':
        task.stop_requested = True
        db.session.commit()
        return jsonify({'success': True, 'message': 'Yêu cầu dừng đã được gửi.'})
    return jsonify({'success': False, 'message': 'Tác vụ không chạy.'})