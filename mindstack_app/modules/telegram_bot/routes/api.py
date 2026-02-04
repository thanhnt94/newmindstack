# File: mindstack_app/modules/telegram_bot/routes/api.py
from flask import request
from .. import blueprint
from ..services import process_update, send_telegram_message
from mindstack_app.models import User
from mindstack_app.core.error_handlers import error_response, success_response

@blueprint.route('/webhook', methods=['POST'])
def webhook():
    """Endpoint nhận Webhook từ Telegram."""
    update = request.get_json()
    if update:
        process_update(update)
    return 'OK', 200

@blueprint.route('/test-send/<username>', methods=['GET'])
def test_send(username):
    """Test gửi tin nhắn cho user cụ thể."""
    user = User.query.filter_by(username=username).first()
    if not user:
        return error_response('User not found', 'NOT_FOUND', 404)
        
    if not user.telegram_chat_id:
        return error_response(f'User {username} chưa kết nối Telegram (chưa có chat_id)', 'BAD_REQUEST', 400)
    
    success = send_telegram_message(user.telegram_chat_id, "🔔 Đây là tin nhắn test từ Mindstack! Chúc bạn học tốt.")
    return success_response(data={'success': success})
