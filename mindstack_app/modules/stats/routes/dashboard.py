from flask import render_template, request
from mindstack_app.utils.template_helpers import render_dynamic_template
from flask_login import login_required, current_user
from sqlalchemy import func
from datetime import datetime, timedelta, date

from mindstack_app.models import db, ScoreLog, LearningProgress, LearningContainer, LearningItem
from .. import stats_bp
from ..services.metrics import (
    get_user_container_options,
    ITEM_TYPE_LABELS
)

@stats_bp.route('/')
@login_required
def dashboard():
    """
    Route chính để hiển thị trang dashboard thống kê.
    """
    from mindstack_app.services.learning_metrics_service import LearningMetricsService

    initial_sort_by = request.args.get('sort_by', 'total_score')
    initial_timeframe = request.args.get('timeframe', 'all_time')

    # [REPLACE] Use service for leaderboard
    leaderboard_data = LearningMetricsService.get_leaderboard(
        sort_by=initial_sort_by, 
        timeframe=initial_timeframe or 'all_time',
        viewer_user=current_user
    )
    
    # [REPLACE] Use service for main summary
    # Note: Service returns a comprehensive dict. We map it to 'dashboard_data' keys.
    summary = LearningMetricsService.get_user_learning_summary(current_user.user_id)
    
    fc = summary['flashcard']
    qz = summary['quiz']
    co = summary['course']
    
    # Calculate derived metrics that might be expecting specific keys
    # Old key: 'learned_distinct_overall' -> fc['total']
    # Old key: 'learned_sets_count' -> Not in summary currently? 
    # Wait, I missed 'sets_count' in flashcard summary in service? 
    # Let's check service. I put 'sets_started' in quiz/course but maybe missed flashcard sets.
    # Actually, looking at service implementation: 
    # _get_flashcard_metrics currently returns: total, mastered, learning, new, hard, reviewing, due, completion_percent, correct_total, incorrect_total, attempt_total, accuracy_percent, avg_streak, best_streak.
    # It DOES NOT return 'sets_count'. 
    # I should add it or calculate it here separately using the old helper if needed, 
    # OR better yet, update the service to include it.
    # For now to keep this atomic, I will calculate it here or fetch it if crucial.
    # But wait, 'learned_sets_count' is displayed on the UI.
    # I will allow a small ad-hoc query here or simple '0' if I want to rush, but better to add it to service.
    # Actually, let's look at `metrics.get_user_container_options` - that gets the LIST of sets.
    # I can just count that list!
    
    flashcard_sets_list = get_user_container_options(
        current_user.user_id,
        'FLASHCARD_SET',
        LearningProgress.MODE_FLASHCARD,
        'last_reviewed',
        item_type='FLASHCARD',
    )
    flashcard_sets_count = len(flashcard_sets_list)

    # Re-map service output to template expected keys
    dashboard_data = {
        'flashcard_score': 0, # TODO: Service doesn't break down score by mode yet in summary, but 'get_score_breakdown' does time based.
                              # 'get_learning_activity_breakdown' (which I implemented as get_score_breakdown?) 
                              # Wait, I implemented 'get_todays_activity_counts'.
                              # I missed 'score by type' in my service implementation plan?
                              # The dashboard uses individual scores like 'flashcard_score'.
                              # Inspecting service... I did NOT implement 'get_score_by_type'.
                              # I will calculate it here or accept 0 for now? No, user wants data.
                              # I will add a quick query here using the same logic as before for now, 
                              # or add it to service in next step. For refactoring safety, let's keep the raw query for *just* the breakdown if needed,
                              # OR utilize 'get_recent_activity' logic? No.
                              # Let's assume for this specific refactor I will map what I have.
        'learned_distinct_overall': fc['total'],
        'learned_sets_count': flashcard_sets_count,
        'flashcard_accuracy_percent': fc['accuracy_percent'],
        'flashcard_attempt_total': fc['attempt_total'],
        'flashcard_correct_total': fc['correct_total'],
        'flashcard_incorrect_total': fc['incorrect_total'],
        'flashcard_mastered_count': fc['mastered'],
        'flashcard_avg_streak_overall': fc['avg_streak'],
        'flashcard_best_streak_overall': fc['best_streak'],
        
        'quiz_score': 0, # Placeholder
        'questions_answered_count': qz['total_questions_encountered'],
        'quiz_sets_started_count': qz['sets_started'],
        'quiz_accuracy_percent': qz['accuracy_percent'],
        'quiz_attempt_total': qz['attempt_total'],
        'quiz_correct_total': qz['correct_total'],
        'quiz_incorrect_total': qz['incorrect_total'],
        'quiz_mastered_count': qz['mastered'],
        'quiz_avg_streak_overall': qz['avg_streak'],
        'quiz_best_streak_overall': qz['best_streak'],
        
        'courses_started_count': co['courses_started'],
        'lessons_completed_count': co['completed_lessons'],
        'courses_in_progress_count': co['in_progress_lessons'],
        'course_avg_completion_percent': co['avg_completion'],
        'course_last_progress': co['last_progress'].isoformat() if co['last_progress'] else None,
        
        'total_score_all_time': summary['total_score'],
        'total_activity_entries': summary['total_entries'],
        'active_days': summary['active_days'],
        'average_daily_score': round(summary['total_score'] / summary['active_days'], 1) if summary['active_days'] else 0,
        
        'total_score_last_30_days': 0, # Service doesn't provide this yet
        'average_daily_score_recent': 0, # Service doesn't provide this yet
        'last_activity': summary['last_activity'].isoformat() if summary['last_activity'] else None,
        'current_learning_streak': summary['current_streak'],
        'longest_learning_streak': summary['longest_streak'],
    }
    
    # [FIX MISSING METRICS] 
    # To properly fill gaps (score breakdown, 30 day score), we perform a supplementary query 
    # essentially mimicking what `get_activity_breakdown` or similar did, but cleaner.
    # OR even better, we rely on `get_recent_activity` for the list.
    
    # Let's fill the gaps with the Activity Breakdown helper I put in service?
    # Wait, I implemented `get_todays_activity_counts` but not the generic `get_activity_breakdown(timeframe)` I promised in the plan.
    # My plan said "Implement get_learning_activity_breakdown (by item type)".
    # In the code step for service, I implemented `get_todays_activity_counts` and `get_week_activity_counts`.
    # I did NOT implement the generic one. I should have. 
    # I will add it to the service now via a separate tool call to be clean, 
    # then come back to this file. 
    # Wait, I can't interrupt replace_file_content.
    # I will stub them here with 0 and then immediately update the service.
    # Actually, the user will see 0s. 
    # Better: I will use the old logic for the missing pieces TEMPORARILY in this route (or re-use the functions from metrics.py if they are still there - yes they are).
    # `get_activity_breakdown` is in `services/metrics.py`. I can still import it!
    # So I will use `LearningMetricsService` for the big stuff, and existing helpers for the stuff I haven't migrated yet.
    
    from ..services.metrics import (
        get_activity_breakdown,
        get_score_trend_series # Still needed for charts? Yes likely via AJAX, but maybe not on main load?
                               # Actually `dashboard.html` usually loads charts via API, but `dashboard_data` needs the scalar values.
    )
    
    # activity_breakdown = get_activity_breakdown(current_user.user_id, 'all_time') 
    # buckets = activity_breakdown['buckets'] ...
    # This seems safer than showing 0.
    
    # Let's execute the old breakdown to get the scores.
    breakdown = get_activity_breakdown(current_user.user_id, 'all_time')
    for bucket in breakdown['buckets']:
        if bucket['item_type'] == 'FLASHCARD':
            dashboard_data['flashcard_score'] = bucket['score']
        elif bucket['item_type'] == 'QUIZ_MCQ':
            dashboard_data['quiz_score'] = bucket['score']

    # 30 day score
    breakdown_30 = get_activity_breakdown(current_user.user_id, '30d')
    dashboard_data['total_score_last_30_days'] = breakdown_30['total_score']
    # Avg recent
    # Approximate based on 30 days
    dashboard_data['average_daily_score_recent'] = round(breakdown_30['total_score'] / 30, 1) if breakdown_30['total_score'] else 0

    recent_activity = LearningMetricsService.get_recent_activity(current_user.user_id)
    recent_sessions = LearningMetricsService.get_recent_sessions(current_user.user_id)

    flashcard_sets = flashcard_sets_list # reused from above
    quiz_sets = get_user_container_options(
        current_user.user_id,
        'QUIZ_SET',
        LearningProgress.MODE_QUIZ,
        'last_reviewed',
        item_type='QUIZ_MCQ',
    )
    course_sets = get_user_container_options(
        current_user.user_id,
        'COURSE',
        LearningProgress.MODE_COURSE,
        'last_reviewed',
        item_type='LESSON',
    )

    return render_dynamic_template('pages/analytics/dashboard.html',
        leaderboard_data=leaderboard_data,
        dashboard_data=dashboard_data,
        current_sort_by=initial_sort_by,
        current_timeframe=initial_timeframe,
        flashcard_sets=flashcard_sets,
        quiz_sets=quiz_sets,
        course_sets=course_sets,
        recent_activity=recent_activity,
        recent_sessions=recent_sessions,
    )
