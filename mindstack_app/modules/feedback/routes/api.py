from flask import request, jsonify
from flask_login import login_required, current_user
from mindstack_app.core.extensions import db
from ..models import Feedback
from .. import blueprint

@blueprint.route('/submit', methods=['POST'])
@login_required
def submit_feedback():
    """
    Endpoint API để người dùng gửi phản hồi.
    """
    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'message': 'Dữ liệu không hợp lệ.'}), 400

    feedback_text = data.get('feedback_text', '').strip()
    item_id = data.get('item_id')
    
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
    
    return jsonify({'success': True, 'message': 'Cảm ơn! Phản hồi đã được gửi.'}), 200

@blueprint.route('/submit-general', methods=['POST'])
@login_required
def submit_general_feedback():
    """Endpoint để gửi phản hồi chung."""
    return submit_feedback()
