import requests
from ...models import SystemSetting, User, db

def get_bot_token():
    setting = SystemSetting.query.filter_by(key='telegram_bot_token').first()
    return setting.value if setting else None

def send_telegram_message(chat_id, text):
    token = get_bot_token()
    if not token:
        print("Telegram Bot Token not found in SystemSettings.")
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

def process_update(update):
    """Xử lý update từ Webhook Telegram"""
    message = update.get('message')
    if not message:
        return
    
    chat_id = message.get('chat', {}).get('id')
    text = message.get('text', '').strip()
    
    if text.startswith('/start'):
        # Cú pháp: /start <username>
        # Ví dụ: /start admin
        parts = text.split()
        if len(parts) > 1:
            username = parts[1]
            user = User.query.filter_by(username=username).first()
            if user:
                user.telegram_chat_id = str(chat_id)
                db.session.commit()
                send_telegram_message(chat_id, f"✅ Xin chào <b>{user.username}</b>!\nBạn đã kết nối thành công với Mindstack.\nTôi sẽ nhắc nhở bạn học tập vào lúc <b>07:00</b> mỗi sáng.")
            else:
                send_telegram_message(chat_id, "❌ Không tìm thấy username này trong hệ thống Mindstack.")
        else:
             send_telegram_message(chat_id, "👋 Chào bạn! Để kết nối tài khoản, vui lòng gửi lệnh:\n\n<code>/start username_cua_ban</code>")
