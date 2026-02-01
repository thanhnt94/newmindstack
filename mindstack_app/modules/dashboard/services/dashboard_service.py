from typing import Dict, Any, List
from flask import url_for
from mindstack_app.models import UserGoal
from mindstack_app.modules.goals.view_helpers import build_goal_progress
from mindstack_app.modules.learning.services.learning_metrics_service import LearningMetricsService

class DashboardService:
    @staticmethod
    def get_dashboard_data(user_id: int) -> Dict[str, Any]:
        """Fetch and aggregate all data for the user dashboard."""
        
        # 1. Fetch Summaries
        summaries = LearningMetricsService.get_user_learning_summary(user_id)
        flashcard_summary = summaries['flashcard']
        quiz_summary = summaries['quiz']
        course_summary = summaries['course']
        
        # 2. Daily activity counts
        todays_counts = LearningMetricsService.get_todays_activity_counts(user_id)
        flashcard_reviews_today = todays_counts['flashcard']
        quiz_attempts_today = todays_counts['quiz']
        
        # 3. Score Breakdown
        score_data = LearningMetricsService.get_score_breakdown(user_id)
        weekly_active_days = LearningMetricsService.get_weekly_active_days_count(user_id)
        
        score_overview = {
            'today': score_data['today'],
            'week': score_data['week'],
            'total': score_data['total'],
            'active_days': weekly_active_days
        }

        # 4. Motivation message
        motivation_message = DashboardService._generate_motivation_message(
            flashcard_reviews_today, 
            quiz_attempts_today, 
            score_data['today']
        )

        # 5. Shortcut Actions
        shortcut_actions = DashboardService._get_shortcut_actions(
            flashcard_summary, 
            quiz_summary, 
            course_summary
        )

        # 6. Goals
        goals = UserGoal.query.filter_by(user_id=user_id, is_active=True).order_by(UserGoal.created_at.desc()).all()
        goal_progress = build_goal_progress(goals)

        return {
            'flashcard_summary': flashcard_summary,
            'quiz_summary': quiz_summary,
            'course_summary': course_summary,
            'score_overview': score_overview,
            'motivation_message': motivation_message,
            'shortcut_actions': shortcut_actions,
            'goal_progress': goal_progress
        }

    @staticmethod
    def _generate_motivation_message(flashcard_count, quiz_count, score_today) -> str:
        activity_parts = []
        if flashcard_count > 0: activity_parts.append(f"ôn {flashcard_count} thẻ")
        if quiz_count > 0: activity_parts.append(f"làm {quiz_count} câu quiz")
        
        if activity_parts:
            if len(activity_parts) == 1:
                msg = f"Hôm nay bạn đã {activity_parts[0]}."
            else:
                msg = f"Hôm nay bạn đã {', '.join(activity_parts[:-1])} và {activity_parts[-1]}."
            if score_today > 0:
                msg += f" Bạn còn kiếm thêm {score_today} điểm thưởng nữa!"
            return msg
        else:
            return "Hôm nay bạn chưa bắt đầu phiên học nào. Chọn một hoạt động bên dưới để khởi động nhé!"

    @staticmethod
    def _get_shortcut_actions(flashcard_summary, quiz_summary, course_summary) -> List[Dict[str, str]]:
        actions = []
        if flashcard_summary['due'] > 0:
            actions.append({
                'title': 'Ôn flashcard đến hạn',
                'description': f"{flashcard_summary['due']} thẻ đang chờ bạn.",
                'icon': 'bolt',
                'url': url_for('vocab_flashcard.flashcard_dashboard_internal.dashboard'),
            })
        if quiz_summary['learning'] > 0:
                    actions.append({
                        'title': 'Tiếp tục luyện quiz',
                        'description': f"Bạn còn {quiz_summary['learning']} câu hỏi ở trạng thái đang học.",
                        'icon': 'circle-question',
                        'url': url_for('practice.quiz_dashboard'),
                    })
        
        if course_summary['in_progress_lessons'] > 0:
            actions.append({
                'title': 'Hoàn thiện khóa học',
                'description': f"{course_summary['in_progress_lessons']} bài học đang dang dở.",
                'icon': 'graduation-cap',
                'url': url_for('course.course_learning_dashboard'),
            })

        if not actions:
            actions.append({
                'title': 'Khởi động với Flashcard',
                'description': 'Tạo đà học tập với vài thẻ đầu tiên.',
                'icon': 'sparkles',
                'url': url_for('vocab_flashcard.flashcard_dashboard_internal.dashboard'),
            })
        return actions
