from flask import render_template, request, flash, redirect, url_for, abort
from flask_login import login_required, current_user
from mindstack_app.utils.template_helpers import render_dynamic_template
from mindstack_app.models import User
from ..models import Feedback
from ..services.feedback_service import FeedbackService
from .. import blueprint

@blueprint.route('/')
@login_required
def manage_feedback():
    """
    Hiển thị trang quản lý phản hồi.
    """
    sent_feedbacks = Feedback.query.filter_by(user_id=current_user.user_id).order_by(Feedback.created_at.desc()).all()

    if current_user.user_role == 'admin':
        received_feedbacks = Feedback.query.order_by(Feedback.created_at.desc()).all()
    else:
        received_feedbacks = [] 

    return render_dynamic_template('pages/feedback/manage_feedback.html',
                            received_feedbacks=received_feedbacks,
                            sent_feedbacks=sent_feedbacks,
                            users=User.query.order_by(User.username).all())

@blueprint.route('/<int:feedback_id>/resolve', methods=['POST'])
@login_required
def resolve_feedback(feedback_id):
    if current_user.user_role != 'admin':
        abort(403)
        
    if FeedbackService.resolve_feedback(feedback_id, current_user.user_id):
        flash('Phản hồi đã được đánh dấu là đã giải quyết!', 'success')
    else:
        flash('Không tìm thấy phản hồi.', 'danger')
        
    return redirect(url_for('feedback.manage_feedback'))

@blueprint.route('/<int:feedback_id>/ignore', methods=['POST'])
@login_required
def ignore_feedback(feedback_id):
    if current_user.user_role != 'admin':
        abort(403)
        
    if FeedbackService.close_feedback(feedback_id, current_user.user_id):
        flash('Phản hồi đã được đóng.', 'info')
    else:
        flash('Không tìm thấy phản hồi.', 'danger')
        
    return redirect(url_for('feedback.manage_feedback'))
