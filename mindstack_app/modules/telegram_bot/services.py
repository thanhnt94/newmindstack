import requests
from mindstack_app.models import AppSettings, User, db

def get_bot_token():
    return AppSettings.get('telegram_bot_token')

def send_telegram_message(chat_id, text):
    token = get_bot_token()
    if not token:
        print("Telegram Bot Token not found in AppSettings.")
        return False
    
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        'chat_id': chat_id,
        'text': text,
        'parse_mode': 'HTML'
    }
    try:
        response = requests.post(url, json=payload, timeout=10)
        if not response.ok:
            print(f"Telegram API Error: {response.text}")
        return response.ok
    except Exception as e:
        print(f"Error sending telegram: {e}")
        return False

from flask import current_app
from itsdangerous import URLSafeTimedSerializer

def get_serializer():
    return URLSafeTimedSerializer(current_app.config['SECRET_KEY'])

def get_bot_username():
    return AppSettings.get('telegram_bot_username', 'MindStackBot')

def generate_connect_link(user_id):
    s = get_serializer()
    token = s.dumps(user_id, salt='telegram-connect')
    bot_name = get_bot_username()
    return f"https://t.me/{bot_name}?start={token}"

def process_update(update):
    """Xử lý update từ Webhook Telegram"""
    message = update.get('message')
    if not message:
        return
    
    chat_id = message.get('chat', {}).get('id')
    text = message.get('text', '').strip()
    
    if text.startswith('/start'):
        # Cú pháp: /start <token>
        parts = text.split()
        if len(parts) > 1:
            token = parts[1]
            try:
                s = get_serializer()
                user_id = s.loads(token, salt='telegram-connect', max_age=3600) # Valid for 1 hour
                
                user = User.query.get(user_id)
                if user:
                    user.telegram_chat_id = str(chat_id)
                    db.session.commit()
                    send_telegram_message(chat_id, f"✅ Xin chào <b>{user.username}</b>!\nBạn đã kết nối thành công với Mindstack.\nTôi sẽ gửi thông báo học tập cho bạn tại đây.")
                else:
                    send_telegram_message(chat_id, "❌ Không tìm thấy user.")
            except Exception as e:
                send_telegram_message(chat_id, "❌ Link kết nối không hợp lệ hoặc đã hết hạn (chỉ có hiệu lực trong 1 giờ).")
        else:
            send_telegram_message(chat_id, "👋 Chào bạn! Hãy nhấn vào nút 'Kết nối Telegram' trên website Mindstack để bắt đầu.")
