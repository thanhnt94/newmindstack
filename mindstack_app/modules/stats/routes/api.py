from flask import jsonify, request, current_app
from flask_login import login_required, current_user
from datetime import datetime, timedelta
from sqlalchemy import func

from mindstack_app.models import db, ScoreLog
from .. import stats_bp
from ..services.metrics import (
    get_score_trend_series,
    get_activity_breakdown,
    get_flashcard_activity_series,
    get_quiz_activity_series,
    get_course_activity_series,
    get_flashcard_set_metrics,
    get_quiz_set_metrics,
    get_course_metrics,
    paginate_flashcard_items,
    paginate_quiz_items,
    paginate_course_items,
    sanitize_pagination_args
)
from mindstack_app.modules.learning.services.learning_metrics_service import LearningMetricsService


@stats_bp.route('/api/leaderboard-data')
@login_required
def get_leaderboard_data_api():
    """API endpoint để tải lại dữ liệu bảng xếp hạng một cách động."""
    sort_by = request.args.get('sort_by', 'total_score')
    timeframe = request.args.get('timeframe', 'all_time')
    data = LearningMetricsService.get_leaderboard(
        sort_by=sort_by, 
        timeframe=timeframe, 
        viewer_user=current_user
    )
    return jsonify({'success': True, 'data': data})


@stats_bp.route('/api/heatmap-data')
@login_required
def get_heatmap_data_api():
    """API endpoint để cung cấp dữ liệu cho biểu đồ heatmap."""
    one_year_ago = datetime.utcnow() - timedelta(days=365)
    activity = db.session.query(
        func.date(ScoreLog.timestamp).label('date'),
        func.count(ScoreLog.log_id).label('count')
    ).filter(
        ScoreLog.user_id == current_user.user_id,
        ScoreLog.timestamp >= one_year_ago
    ).group_by(func.date(ScoreLog.timestamp)).all()
    
    heatmap_data = {int(datetime.combine(row.date, datetime.min.time()).timestamp()): row.count for row in activity}
    return jsonify(heatmap_data)


from ..logics.chart_utils import prepare_chartjs_config, get_color_for_dataset

@stats_bp.route('/api/score-trend')
@login_required
def get_score_trend_api():
    timeframe = request.args.get('timeframe', '30d')
    data = get_score_trend_series(current_user.user_id, timeframe=timeframe)
    
    # Transform to Chart.js Config
    series = data.get('series', [])
    labels = [datetime.fromisoformat(d['date']).strftime('%d/%m') for d in series]
    values = [d['total_score'] for d in series]
    
    config = prepare_chartjs_config(
        labels=labels,
        datasets=[{
            'label': 'Điểm số tích lũy',
            'data': values,
            'borderColor': get_color_for_dataset(0),
            'backgroundColor': get_color_for_dataset(0, 0.1),
            'fill': True,
            'tension': 0.4
        }],
        chart_type='line',
        options={
            'plugins':{
                'title': {'display': True, 'text': f'Xu hướng điểm số ({timeframe})'}
            }
        }
    )
    
    return jsonify({
        'success': True, 
        'data': data,
        'chart_config': config
    })


@stats_bp.route('/api/activity-breakdown')
@login_required
def get_activity_breakdown_api():
    timeframe = request.args.get('timeframe', '30d')
    data = get_activity_breakdown(current_user.user_id, timeframe=timeframe)
    return jsonify({'success': True, 'data': data})


@stats_bp.route('/api/flashcard-activity')
@login_required
def get_flashcard_activity_api():
    container_id = request.args.get('container_id', type=int)
    timeframe = request.args.get('timeframe', '30d')
    if not container_id:
        return jsonify({'success': False, 'message': 'Thiếu container_id'}), 400

    data = get_flashcard_activity_series(current_user.user_id, container_id, timeframe=timeframe)
    return jsonify({'success': True, 'data': data})


@stats_bp.route('/api/quiz-activity')
@login_required
def get_quiz_activity_api():
    container_id = request.args.get('container_id', type=int)
    timeframe = request.args.get('timeframe', '30d')
    if not container_id:
        return jsonify({'success': False, 'message': 'Thiếu container_id'}), 400

    data = get_quiz_activity_series(current_user.user_id, container_id, timeframe=timeframe)
    return jsonify({'success': True, 'data': data})


@stats_bp.route('/api/course-activity')
@login_required
def get_course_activity_api():
    container_id = request.args.get('container_id', type=int)
    timeframe = request.args.get('timeframe', '30d')
    if not container_id:
        return jsonify({'success': False, 'message': 'Thiếu container_id'}), 400

    data = get_course_activity_series(current_user.user_id, container_id, timeframe=timeframe)
    return jsonify({'success': True, 'data': data})


@stats_bp.route('/api/flashcard-set-metrics')
@login_required
def get_flashcard_set_metrics_api():
    container_id = request.args.get('container_id', type=int)
    status = request.args.get('status')
    page, per_page = sanitize_pagination_args(
        request.args.get('page', 1),
        request.args.get('per_page', 10),
    )
    data = get_flashcard_set_metrics(
        current_user.user_id,
        container_id=container_id,
        status=status,
        page=page,
        per_page=per_page,
    )
    return jsonify({'success': True, 'data': data})


@stats_bp.route('/api/quiz-set-metrics')
@login_required
def get_quiz_set_metrics_api():
    container_id = request.args.get('container_id', type=int)
    status = request.args.get('status')
    page, per_page = sanitize_pagination_args(
        request.args.get('page', 1),
        request.args.get('per_page', 10),
    )
    data = get_quiz_set_metrics(
        current_user.user_id,
        container_id=container_id,
        status=status,
        page=page,
        per_page=per_page,
    )
    return jsonify({'success': True, 'data': data})


@stats_bp.route('/api/course-metrics')
@login_required
def get_course_metrics_api():
    container_id = request.args.get('container_id', type=int)
    status = request.args.get('status')
    page, per_page = sanitize_pagination_args(
        request.args.get('page', 1),
        request.args.get('per_page', 10),
    )
    data = get_course_metrics(
        current_user.user_id,
        container_id=container_id,
        status=status,
        page=page,
        per_page=per_page,
    )
    return jsonify({'success': True, 'data': data})


@stats_bp.route('/api/flashcard-items')
@login_required
def get_flashcard_items_api():
    container_id = request.args.get('container_id', type=int)
    status = request.args.get('status')
    page, per_page = sanitize_pagination_args(
        request.args.get('page', 1),
        request.args.get('per_page', 10),
    )
    data = paginate_flashcard_items(
        current_user.user_id,
        container_id=container_id,
        status=status,
        page=page,
        per_page=per_page,
    )
    return jsonify({'success': True, 'data': data})


@stats_bp.route('/api/quiz-items')
@login_required
def get_quiz_items_api():
    container_id = request.args.get('container_id', type=int)
    status = request.args.get('status')
    page, per_page = sanitize_pagination_args(
        request.args.get('page', 1),
        request.args.get('per_page', 10),
    )
    data = paginate_quiz_items(
        current_user.user_id,
        container_id=container_id,
        status=status,
        page=page,
        per_page=per_page,
    )
    return jsonify({'success': True, 'data': data})


@stats_bp.route('/api/course-items')
@login_required
def get_course_items_api():
    container_id = request.args.get('container_id', type=int)
    status = request.args.get('status')
    page, per_page = sanitize_pagination_args(
        request.args.get('page', 1),
        request.args.get('per_page', 10),
    )
    data = paginate_course_items(
        current_user.user_id,
        container_id=container_id,
        status=status,
        page=page,
        per_page=per_page,
    )
    return jsonify({'success': True, 'data': data})
