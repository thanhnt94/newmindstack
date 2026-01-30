from flask import render_template, request, jsonify, flash, redirect, url_for, abort
from mindstack_app.utils.template_helpers import render_dynamic_template
from flask_login import login_required, current_user
from sqlalchemy import or_

from . import blueprint
# We now use the new Feedback models from kernel
from mindstack_app.models import db, Feedback, LearningItem, LearningContainer, User
from datetime import datetime


@blueprint.route('/')
@login_required
def manage_feedback():
    """
    Mô tả:
        Hiển thị trang quản lý phản hồi.
        Admin sẽ thấy tất cả phản hồi.
        Người dùng thường sẽ thấy những phản hồi họ đã gửi.
    """
    # Phản hồi đã gửi (là những feedback do chính người dùng hiện tại tạo ra)
    sent_feedbacks = Feedback.query.filter_by(user_id=current_user.user_id).order_by(Feedback.created_at.desc()).all()

    if current_user.user_role == 'admin':
        # Admin thấy tất cả feedback
        received_feedbacks = Feedback.query.order_by(Feedback.created_at.desc()).all()
    else:
        # User thường không có khái niệm "nhận" feedback trong hệ thống mới trừ khi họ là Creator (logic này có thể cần điều chỉnh sau)
        # Tạm thời để trống hoặc logic tương tự
        # logic cũ khá phức tạp dựa trên learning item container
        received_feedbacks = [] 

    return render_dynamic_template('pages/feedback/manage_feedback.html',
                            received_feedbacks=received_feedbacks,
                            sent_feedbacks=sent_feedbacks,
                            users=User.query.order_by(User.username).all())


@blueprint.route('/submit', methods=['POST'])
@login_required
def submit_feedback():
    """
    Mô tả:
        Endpoint API để người dùng gửi phản hồi (gắn với item cụ thể hoặc chung).
    """
    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'message': 'Dữ liệu không hợp lệ.'}), 400

    feedback_text = data.get('feedback_text', '').strip()
    item_id = data.get('item_id') # Optional context
    
    if not feedback_text:
        return jsonify({'success': False, 'message': 'Nội dung không được để trống.'}), 400
        
    feedback = Feedback(
        user_id=current_user.user_id,
        content=feedback_text,
        type='CONTENT_ERROR' if item_id else 'OTHER',
        meta_data={'item_id': item_id} if item_id else None
    )
    
    db.session.add(feedback)
    db.session.commit()
    
    # Trigger signal?
    # from mindstack_app.modules.feedback.services.feedback_manager import FeedbackManager
    # FeedbackManager.on_feedback_received(feedback)
    
    return jsonify({'success': True, 'message': 'Cảm ơn! Phản hồi đã được gửi.'}), 200



@blueprint.route('/submit-general', methods=['POST'])
@login_required
def submit_general_feedback():
    """Endpoint để gửi phản hồi chung."""
    # Reusing the unified submit logic or custom logic
    # Here we just alias it or implement similar logic
    return submit_feedback() # Use the robust one above


@blueprint.route('/<int:feedback_id>/resolve', methods=['POST'])
@login_required
def resolve_feedback(feedback_id):
    """
    Mô tả:
        Endpoint để đánh dấu một phản hồi là đã giải quyết.
        Chỉ admin mới có quyền thực sự trong hệ thống mới.
    """
    feedback = Feedback.query.get_or_404(feedback_id)

    # Hệ thống mới tập trung, chỉ Admin xử lý feedback chính thống
    if current_user.user_role != 'admin':
        abort(403)
        
    feedback.status = 'RESOLVED'
    feedback.resolved_by_id = current_user.user_id
    feedback.resolved_at = datetime.utcnow() # Update resolved time
    
    db.session.commit()
    
    flash('Phản hồi đã được đánh dấu là đã giải quyết!', 'success')
    return redirect(url_for('feedback.manage_feedback'))


@blueprint.route('/<int:feedback_id>/ignore', methods=['POST'])
@login_required
def ignore_feedback(feedback_id):
    """
    Mô tả:
        Endpoint để đóng phản hồi mà không giải quyết.
    """
    feedback = Feedback.query.get_or_404(feedback_id)
    
    if current_user.user_role != 'admin':
        abort(403)
        
    feedback.status = 'CLOSED' # Replaced 'wont_fix' with standard 'CLOSED'
    feedback.resolved_by_id = current_user.user_id
    feedback.resolved_at = datetime.utcnow()
    
    db.session.commit()
    
    flash('Phản hồi đã được đóng.', 'info')
    return redirect(url_for('feedback.manage_feedback'))
