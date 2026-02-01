from .services import send_telegram_message
from mindstack_app.models import User, db
from datetime import datetime

def send_daily_study_reminder():
    """Gửi tin nhắn nhắc nhở học tập cho tất cả user đã kết nối Telegram."""
    
    # Lưu ý: Hàm này sẽ được Scheduler gọi trong App Context
    
    users = User.query.filter(User.telegram_chat_id.isnot(None)).all()
    
    print(f"[{datetime.now()}] ⏰ Bắt đầu gửi nhắc nhở học tập...")
    
    count = 0
    for user in users:
        if not user.telegram_chat_id:
            continue
            
        message = (
            f"☀️ Chào buổi sáng <b>{user.username}</b>!\n\n"
            "Đã đến lúc khởi động ngày mới bằng vài thẻ Flashcard hoặc một bài Quiz nhỏ.\n"
            "Hãy truy cập Mindstack để duy trì chuỗi học tập nhé! 🚀\n\n"
            "<i>Chúc bạn một ngày hiệu quả!</i>"
        )
        success = send_telegram_message(user.telegram_chat_id, message)
        if success:
            count += 1
            
    print(f"[{datetime.now()}] ✅ Đã gửi nhắc nhở thành công cho {count}/{len(users)} người dùng.")
