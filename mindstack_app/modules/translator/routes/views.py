from datetime import datetime
from sqlalchemy import func
from flask_login import login_required, current_user
from mindstack_app.utils.template_helpers import render_dynamic_template
from ..services import TranslatorService
from ..models import TranslationHistory
from .. import blueprint

@blueprint.route('/history', methods=['GET'])
@login_required
def history_page():
    """Render dedicated translation history page."""
    history = TranslatorService.get_user_history(current_user.user_id, limit=200)
    
    today = datetime.utcnow().date()
    today_count = TranslationHistory.query.filter(
        TranslationHistory.user_id == current_user.user_id,
        func.date(TranslationHistory.created_at) == today
    ).count()

    return render_dynamic_template(
        'pages/translator/history.html',
        history=history,
        today_count=today_count
    )
