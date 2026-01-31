# File: mindstack_app/modules/admin/routes/dashboard.py
from flask import render_template
from sqlalchemy import nullslast
from datetime import datetime, timedelta
from mindstack_app.models import db, User, LearningContainer, LearningItem, ApiKey, BackgroundTask
from .. import blueprint
from ..context_processors import build_admin_sidebar_metrics

@blueprint.route('/')
@blueprint.route('/dashboard')
def admin_dashboard():
    """
    Mô tả: Hiển thị trang dashboard admin tổng quan.
    """
    total_users = db.session.query(User).count()
    users_last_24h = db.session.query(User).filter(User.last_seen >= (datetime.utcnow() - timedelta(hours=24))).count()
    
    total_containers = db.session.query(LearningContainer).count()
    total_items = db.session.query(LearningItem).count()
    
    active_api_keys = db.session.query(ApiKey).filter_by(is_active=True, is_exhausted=False).count()
    exhausted_api_keys = db.session.query(ApiKey).filter_by(is_exhausted=True).count()
    
    stats_data = {
        'total_users': total_users,
        'users_last_24h': users_last_24h,
        'total_containers': total_containers,
        'total_items': total_items,
        'active_api_keys': active_api_keys,
        'exhausted_api_keys': exhausted_api_keys
    }

    recent_users = (
        User.query.filter(User.last_seen.isnot(None))
        .order_by(User.last_seen.desc())
        .limit(5)
        .all()
    )

    recent_containers = (
        LearningContainer.query.order_by(LearningContainer.created_at.desc())
        .limit(5)
        .all()
    )

    recent_tasks = (
        BackgroundTask.query.order_by(nullslast(BackgroundTask.last_updated.desc()))
        .limit(4)
        .all()
    )

    overview_metrics = build_admin_sidebar_metrics()

    return render_template(
        'admin/dashboard.html',
        stats_data=stats_data,
        recent_users=recent_users,
        recent_containers=recent_containers,
        recent_tasks=recent_tasks,
        overview_metrics=overview_metrics,
    )
