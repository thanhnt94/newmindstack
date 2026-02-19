# modules/scoring/services/scoring_config_service.py
from typing import Dict, Any
from mindstack_app.models import AppSettings, db
from ..config import ScoringDefaultConfig

class ScoringConfigService:
    """
    Service to manage scoring configurations.
    Handles fallback logic between Database and Default Config.
    """

    @staticmethod
    def get_config(key: str) -> int:
        """Get a single config value."""
        # 1. Try DB
        db_val = AppSettings.get(key)
        if db_val is not None:
            return db_val
            
        # 2. Try Fallback
        return getattr(ScoringDefaultConfig, key, 0)

    @staticmethod
    def get_all_configs() -> Dict[str, Dict[str, Any]]:
        """
        Get all scoring configs grouped for UI.
        Returns a structured dictionary ready for the View.
        """
        def _item(key, desc):
            return {
                'key': key,
                'value': ScoringConfigService.get_config(key),
                'default': getattr(ScoringDefaultConfig, key, 0),
                'description': desc,
                'type': 'int'
            }

        return {
            'flashcard': {
                'title': 'Flashcard & SRS',
                'icon': 'fas fa-clone',
                'desc': 'Điểm số cho việc học thẻ ghi nhớ và thuật toán lặp lại.',
                'items': [
                    _item('SCORE_FSRS_AGAIN', 'Quên (Again)'),
                    _item('SCORE_FSRS_HARD', 'Khó (Hard)'),
                    _item('SCORE_FSRS_GOOD', 'Tốt (Good)'),
                    _item('SCORE_FSRS_EASY', 'Dễ (Easy)'),
                ]
            },
            'quiz': {
                'title': 'Quiz & Assessment',
                'icon': 'fas fa-question-circle',
                'desc': 'Thưởng điểm khi làm bài kiểm tra.',
                'items': [
                    _item('QUIZ_CORRECT_BONUS', 'Trả lời đúng 1 câu'),
                    _item('QUIZ_FIRST_TIME_BONUS', 'Thưởng hoàn thành lần đầu'),
                ]
            },
            'vocab_games': {
                'title': 'Vocabulary Minigames',
                'icon': 'fas fa-gamepad',
                'desc': 'Điểm thưởng cho các chế độ chơi từ vựng.',
                'items': [
                    _item('VOCAB_MCQ_CORRECT_BONUS', 'Trắc nghiệm (MCQ)'),
                    _item('VOCAB_TYPING_CORRECT_BONUS', 'Gõ từ (Typing)'),
                    _item('VOCAB_MATCHING_CORRECT_BONUS', 'Ghép thẻ (Matching)'),
                    _item('VOCAB_LISTENING_CORRECT_BONUS', 'Nghe chép (Listening)'),
                    _item('VOCAB_SPEED_CORRECT_BONUS', 'Tốc độ (Speed Review)'),
                ]
            },
            'engagement': {
                'title': 'Engagement & Streaks',
                'icon': 'fas fa-fire',
                'desc': 'Khuyến khích người dùng quay lại hàng ngày.',
                'items': [
                    _item('DAILY_LOGIN_SCORE', 'Đăng nhập hàng ngày'),
                    _item('DAILY_GOAL_SCORE', 'Hoàn thành mục tiêu ngày'),
                    _item('SCORING_STREAK_BONUS_VALUE', 'Giá trị thưởng Streak'),
                    _item('SCORING_STREAK_BONUS_MODULO', 'Mốc thưởng Streak (ngày)'),
                ]
            },
            'multipliers': {
                'title': 'Bonuses & Multipliers',
                'icon': 'fas fa-percentage',
                'desc': 'Cấu hình các hệ số thưởng dựa trên độ khó và chuỗi.',
                'items': [
                    _item('SCORING_DIFFICULTY_WEIGHT', 'Trọng số độ khó (Thấp = Thưởng cao hơn)'),
                    _item('SCORING_STREAK_THRESHOLD', 'Chuỗi tối thiểu để nhận thưởng'),
                    _item('SCORING_STREAK_CAP', 'Giới hạn điểm thưởng chuỗi tối đa'),
                ]
            },
            'course': {
                'title': 'Course Progress',
                'icon': 'fas fa-book-open',
                'desc': 'Tiến độ hoàn thành khóa học.',
                'items': [
                    _item('COURSE_LESSON_COMPLETION_SCORE', 'Hoàn thành 1 bài học'),
                    _item('COURSE_COMPLETION_SCORE', 'Hoàn thành khóa học'),
                ]
            }
        }

    @staticmethod
    def update_configs(settings_dict: Dict[str, Any]) -> None:
        """
        Update multiple settings at once.
        """
        for key, val in settings_dict.items():
            # Validation logic
            try:
                val = int(val)
            except (ValueError, TypeError):
                val = 0 
            
            # Use AppSettings model directly or via its helper
            AppSettings.set(key, val, category='scoring')
        
        db.session.commit()
