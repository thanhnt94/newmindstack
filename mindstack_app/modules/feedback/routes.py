# File: Mindstack/web/mindstack_app/modules/feedback/routes.py
# Version: 1.0
# Mục đích: Chứa các route và logic cho việc quản lý feedback.

from flask import render_template, request, jsonify, flash, redirect, url_for, abort
from flask_login import login_required, current_user
from sqlalchemy import or_

from . import feedback_bp
from ...models import db, Feedback, LearningItem, LearningContainer
from datetime import datetime

# Route để hiển thị trang quản lý feedback (dành cho admin hoặc chủ sở hữu)
@feedback_bp.route('/')
@login_required
def manage_feedback():
    if current_user.user_role == 'admin':
        # Admin thấy tất cả feedback
        feedbacks = Feedback.query.order_by(Feedback.created_at.desc()).all()
    else:
        # User chỉ thấy feedback liên quan đến nội dung của họ
        feedbacks = Feedback.query.filter(or_(
            Feedback.container.has(author_id=current_user.id),
            Feedback.item.has(container=LearningContainer.author_id==current_user.id)
        )).order_by(Feedback.created_at.desc()).all()
    
    return render_template('feedback/manage_feedback.html', feedbacks=feedbacks)

# Route để người dùng gửi feedback
@feedback_bp.route('/submit', methods=['POST'])
@login_required
def submit_feedback():
    data = request.json
    item_id = data.get('item_id')
    container_id = data.get('container_id')
    feedback_text = data.get('feedback_text')

    if not feedback_text:
        return jsonify({'success': False, 'message': 'Nội dung feedback không được để trống.'}), 400
        
    feedback = Feedback(
        user_id=current_user.id,
        item_id=item_id if item_id else None,
        container_id=container_id if container_id else None,
        feedback_text=feedback_text
    )
    db.session.add(feedback)
    db.session.commit()
    
    return jsonify({'success': True, 'message': 'Cảm ơn bạn! Feedback của bạn đã được gửi thành công.'}), 200

# Route để xử lý feedback (đánh dấu đã giải quyết)
@feedback_bp.route('/<int:feedback_id>/resolve', methods=['POST'])
@login_required
def resolve_feedback(feedback_id):
    feedback = Feedback.query.get_or_404(feedback_id)
    
    # Kiểm tra quyền: Chỉ admin hoặc chủ sở hữu nội dung mới được phép
    if current_user.user_role != 'admin' and feedback.container.author_id != current_user.id:
        abort(403)
        
    feedback.status = 'resolved'
    feedback.resolved_by_id = current_user.id
    feedback.resolved_at = datetime.utcnow()
    
    db.session.commit()
    flash('Feedback đã được đánh dấu là đã giải quyết!', 'success')
    return redirect(url_for('feedback.manage_feedback'))

# Route để xử lý feedback (đánh dấu bỏ qua)
@feedback_bp.route('/<int:feedback_id>/ignore', methods=['POST'])
@login_required
def ignore_feedback(feedback_id):
    feedback = Feedback.query.get_or_404(feedback_id)
    
    # Kiểm tra quyền: Chỉ admin hoặc chủ sở hữu nội dung mới được phép
    if current_user.user_role != 'admin' and feedback.container.author_id != current_user.id:
        abort(403)
        
    feedback.status = 'ignored'
    feedback.resolved_by_id = current_user.id # Người bỏ qua cũng được xem là người đã "xử lý"
    feedback.resolved_at = datetime.utcnow()
    
    db.session.commit()
    flash('Feedback đã được đánh dấu là bị bỏ qua.', 'info')
    return redirect(url_for('feedback.manage_feedback'))