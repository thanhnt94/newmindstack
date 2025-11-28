from flask import request, jsonify
from . import telegram_bot_bp
from .services import process_update, send_telegram_message
from ...models import User

@telegram_bot_bp.route('/webhook', methods=['POST'])
def webhook():
    """Endpoint nhận Webhook từ Telegram."""
    update = request.get_json()
    if update:
        process_update(update)
    return 'OK', 200

@telegram_bot_bp.route('/test-send/<username>', methods=['GET'])
def test_send(username):
    """Test gửi tin nhắn cho user cụ thể."""
    user = User.query.filter_by(username=username).first()
    if not user:
        return jsonify({'error': 'User not found'}), 404
        
    if not user.telegram_chat_id:
        return jsonify({'error': f'User {username} chưa kết nối Telegram (chưa có chat_id)'}), 400
    
    success = send_telegram_message(user.telegram_chat_id, "🔔 Đây là tin nhắn test từ Mindstack! Chúc bạn học tốt.")
    return jsonify({'success': success})
