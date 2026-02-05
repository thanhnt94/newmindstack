from typing import Dict, Any, List
from flask import url_for
from mindstack_app.modules.goals.view_helpers import build_goal_progress
from mindstack_app.modules.gamification import interface as gamification_interface
from mindstack_app.modules.fsrs import interface as fsrs_interface
from mindstack_app.modules.stats import interface as stats_interface
from mindstack_app.modules.goals import interface as goals_interface

class DashboardService:
    @staticmethod
    def get_dashboard_data(user_id: int) -> Dict[str, Any]:
        """Fetch and aggregate all data for the user dashboard."""
        
        # 1. Fetch Stats (Summaries, Activity Counts, Score Logs)
        stats_data = stats_interface.get_dashboard_activity(user_id)
        
        # Extract from aggregated stats
        summaries = stats_data.get('summaries', {})
        flashcard_summary = summaries.get('flashcard', {})
        quiz_summary = summaries.get('quiz', {})
        course_summary = summaries.get('course', {})
        
        # 2. Fetch Due Counts from FSRS (Source of Truth for Scheduling)
        due_counts = fsrs_interface.get_due_counts(user_id)
        
        # Override due counts in summaries with FSRS real-time data
        flashcard_summary['due'] = due_counts.get('flashcard', 0)
        # Assuming quiz items scheduled by FSRS are counted here if needed
        # quiz_summary['due'] = due_counts.get('quiz', 0) 
        
        # 3. Fetch Gamification Status
        user_progress = gamification_interface.get_user_progress(user_id)
        # We might want to inject this into context if view uses it, 
        # but the current dict keys don't seem to have a dedicated slot for it.
        # Let's add it or just ensure 'score_overview' works.
        
        # 4. Score Overview
        score_data = stats_data.get('score_data', {})
        weekly_active_days = stats_data.get('active_days', 0)
        
        score_overview = {
            'today': score_data.get('today', 0),
            'week': score_data.get('week', 0),
            'total': score_data.get('total', 0),
            'active_days': weekly_active_days
        }

        # 5. Motivation message
        todays_counts = stats_data.get('todays_counts', {})
        flashcard_reviews_today = todays_counts.get('flashcard', 0)
        quiz_attempts_today = todays_counts.get('quiz', 0)
        
        motivation_message = DashboardService._generate_motivation_message(
            flashcard_reviews_today, 
            quiz_attempts_today, 
            score_data.get('today', 0)
        )

        # 6. Shortcut Actions
        shortcut_actions = DashboardService._get_shortcut_actions(
            flashcard_summary, 
            quiz_summary, 
            course_summary
        )

        # 7. Goals
        goals = goals_interface.get_user_goals(user_id)
        goal_progress = build_goal_progress(goals)

        return {
            'flashcard_summary': flashcard_summary,
            'quiz_summary': quiz_summary,
            'course_summary': course_summary,
            'score_overview': score_overview,
            'motivation_message': motivation_message,
            'shortcut_actions': shortcut_actions,
            'goal_progress': goal_progress,
            'gamification': user_progress # Add this in case template uses it
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
        if flashcard_summary.get('due', 0) > 0:
            actions.append({
                'title': 'Ôn flashcard đến hạn',
                'description': f"{flashcard_summary['due']} thẻ đang chờ bạn.",
                'icon': 'bolt',
                'url': url_for('vocabulary.dashboard'),
            })
        if quiz_summary.get('learning', 0) > 0:
                    actions.append({
                        'title': 'Tiếp tục luyện quiz',
                        'description': f"Bạn còn {quiz_summary['learning']} câu hỏi ở trạng thái đang học.",
                        'icon': 'circle-question',
                        'url': url_for('quiz.dashboard'),
                    })
        
        if course_summary.get('in_progress_lessons', 0) > 0:
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
                'url': url_for('vocabulary.dashboard'),
            })
        return actions
