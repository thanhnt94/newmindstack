from flask import request
from flask_login import login_required, current_user
from mindstack_app.utils.template_helpers import render_dynamic_template
from mindstack_app.modules.learning.interface import LearningInterface
from mindstack_app.modules.stats.services.leaderboard_service import LeaderboardService
from mindstack_app.modules.stats.services.metrics import get_user_container_options

from .. import blueprint as stats_bp

@stats_bp.route('/')
@login_required
def dashboard():
    """Trang dashboard thống kê (HTML)."""
    timeframe = request.args.get('timeframe', 'week')
    
    # Lấy dữ liệu bảng xếp hạng từ Service
    leaderboard_data = LeaderboardService.get_leaderboard(
        timeframe=timeframe,
        viewer_user=current_user
    )
    
    # Lấy tổng quan học tập từ LearningMetricsService -> LearningInterface
    summary = LearningInterface.get_user_learning_summary(current_user.user_id)
    
    # Map dữ liệu cho UI (Giữ nguyên cấu trúc cũ để tránh break UI)
    dashboard_data = {
        'total_score_all_time': summary['total_score'],
        'current_learning_streak': summary['current_streak'],
        'longest_learning_streak': summary['longest_streak'],
        'total_score_last_30_days': 0, # Sẽ bổ sung sau
        'average_daily_score_recent': 0,
        'learned_distinct_overall': summary['flashcard']['learned'],
        'flashcard_mastered_count': summary['flashcard']['mastered'],
        'flashcard_sets_started_count': summary['flashcard']['sets_started'],
        'flashcard_accuracy_percent': summary['flashcard']['accuracy_percent'],
        'quiz_questions_done_count': summary['quiz']['learned'],
        'quiz_sets_started_count': summary['quiz']['sets_started'],
        'quiz_mastered_count': summary['quiz']['mastered'],
        'quiz_accuracy_percent': summary['quiz']['accuracy_percent'],
        'courses_in_progress_count': summary['course']['in_progress_lessons'],
        'course_avg_completion_percent': summary['course']['avg_completion'],
    }
    
    # NEW: Merge extended stats
    extended_stats = LearningInterface.get_extended_dashboard_stats(current_user.user_id)
    
    # Calculate 30-day score stats from chart data
    score_history = extended_stats.get('charts', {}).get('datasets', {}).get('scores', [])
    total_30d = sum(score_history) if score_history else 0
    avg_30d = total_30d / len(score_history) if score_history else 0

    dashboard_data.update({
        'total_score_last_30_days': total_30d,
        'average_daily_score_recent': avg_30d
    })
    dashboard_data.update(extended_stats)
    
    recent_activity = LearningInterface.get_recent_activity(current_user.user_id)

    return render_dynamic_template('modules/analytics/dashboard.html',
        leaderboard_data=leaderboard_data,
        dashboard_data=dashboard_data,
        recent_activity=recent_activity,
        current_timeframe=timeframe
    )