# modules/scoring/events.py
from blinker import Namespace

_signals = Namespace()

# Tín hiệu nội bộ module scoring phát ra
score_awarded = _signals.signal('score_awarded')

def init_events(app):
    """
    Đăng ký các hàm xử lý (handlers) lắng nghe tín hiệu từ các module khác.
    Giúp module scoring độc lập hoàn toàn.
    """
    # Ví dụ: Lắng nghe từ module learning (khi hoàn thành bài học)
    # lesson_completed.connect(handle_lesson_completion)
    pass

def handle_lesson_completion(sender, **extra):
    # Logic cộng điểm khi nhận tín hiệu hoàn thành bài học
    pass
