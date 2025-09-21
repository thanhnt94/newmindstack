# File: Mindstack/web/mindstack_app/modules/feedback/routes.py
# Version: 1.3
# MỤC ĐÍCH: Khắc phục lỗi lưu nội dung feedback trống.
# ĐÃ SỬA: Thêm logic .strip() để loại bỏ khoảng trắng ở đầu và cuối chuỗi feedback trước khi kiểm tra và lưu vào database.

from flask import render_template, request, jsonify, flash, redirect, url_for, abort
from flask_login import login_required, current_user
from sqlalchemy import or_

from . import feedback_bp
from ...models import db, UserFeedback, LearningItem, LearningContainer
from datetime import datetime

# Route để hiển thị trang quản lý feedback (dành cho admin hoặc chủ sở hữu)
@feedback_bp.route('/')
@login_required
def manage_feedback():
    """
    Mô tả:
        Hiển thị trang quản lý phản hồi.
        Admin sẽ thấy tất cả phản hồi.
        Người dùng thường sẽ thấy 2 danh sách riêng biệt:
        - Phản hồi đã nhận: Về các nội dung do họ tạo.
        - Phản hồi đã gửi: Các phản hồi họ đã gửi.
    """
    # Phản hồi đã gửi (là những feedback do chính người dùng hiện tại tạo ra)
    sent_feedbacks = UserFeedback.query.filter_by(user_id=current_user.user_id).order_by(UserFeedback.timestamp.desc()).all()

    if current_user.user_role == 'admin':
        # Admin thấy tất cả feedback
        received_feedbacks = UserFeedback.query.order_by(UserFeedback.timestamp.desc()).all()
    else:
        # User chỉ thấy feedback liên quan đến nội dung của họ
        received_feedbacks = UserFeedback.query.join(LearningItem, UserFeedback.item_id == LearningItem.item_id)\
                                                .join(LearningContainer, LearningItem.container_id == LearningContainer.container_id)\
                                                .filter(LearningContainer.creator_user_id == current_user.user_id)\
                                                .order_by(UserFeedback.timestamp.desc()).all()

    return render_template('feedback/manage_feedback.html', 
                            received_feedbacks=received_feedbacks,
                            sent_feedbacks=sent_feedbacks)

# Route để người dùng gửi feedback
@feedback_bp.route('/submit', methods=['POST'])
@login_required
def submit_feedback():
    """
    Mô tả:
        Endpoint API để người dùng gửi phản hồi.
    """
    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'message': 'Dữ liệu gửi lên không hợp lệ.'}), 400

    item_id = data.get('item_id')
    # SỬA LỖI: Lấy nội dung và dùng .strip() để loại bỏ khoảng trắng thừa
    feedback_text = data.get('feedback_text', '').strip()

    # Kiểm tra lại sau khi đã strip()
    if not feedback_text:
        return jsonify({'success': False, 'message': 'Nội dung feedback không được để trống.'}), 400
        
    feedback = UserFeedback(
        user_id=current_user.user_id,
        item_id=item_id,
        content=feedback_text, # Lưu nội dung đã được làm sạch
        timestamp=datetime.utcnow()
    )
    db.session.add(feedback)
    db.session.commit()
    
    return jsonify({'success': True, 'message': 'Cảm ơn bạn! Phản hồi của bạn đã được gửi thành công.'}), 200

# Route để xử lý feedback (đánh dấu đã giải quyết)
@feedback_bp.route('/<int:feedback_id>/resolve', methods=['POST'])
@login_required
def resolve_feedback(feedback_id):
    """
    Mô tả:
        Endpoint để đánh dấu một phản hồi là đã giải quyết.
        Chỉ admin hoặc người tạo nội dung liên quan mới có quyền.
    """
    feedback = UserFeedback.query.get_or_404(feedback_id)
    
    # Kiểm tra quyền: Chỉ admin hoặc chủ sở hữu nội dung mới được phép
    is_owner = feedback.item and feedback.item.container and feedback.item.container.creator_user_id == current_user.user_id
    if current_user.user_role != 'admin' and not is_owner:
        abort(403)
        
    feedback.status = 'resolved'
    feedback.resolved_by_id = current_user.user_id
    db.session.commit()
    
    flash('Phản hồi đã được đánh dấu là đã giải quyết!', 'success')
    return redirect(url_for('feedback.manage_feedback'))

# Route để xử lý feedback (đánh dấu bỏ qua)
@feedback_bp.route('/<int:feedback_id>/ignore', methods=['POST'])
@login_required
def ignore_feedback(feedback_id):
    """
    Mô tả:
        Endpoint để đánh dấu một phản hồi là đã bỏ qua.
        Chỉ admin hoặc người tạo nội dung liên quan mới có quyền.
    """
    feedback = UserFeedback.query.get_or_404(feedback_id)
    
    # Kiểm tra quyền: Chỉ admin hoặc chủ sở hữu nội dung mới được phép
    is_owner = feedback.item and feedback.item.container and feedback.item.container.creator_user_id == current_user.user_id
    if current_user.user_role != 'admin' and not is_owner:
        abort(403)
        
    feedback.status = 'wont_fix' # Đã đổi từ 'ignored' thành 'wont_fix' để nhất quán với file html
    feedback.resolved_by_id = current_user.user_id
    db.session.commit()
    
    flash('Phản hồi đã được đánh dấu là bị bỏ qua.', 'info')
    return redirect(url_for('feedback.manage_feedback'))