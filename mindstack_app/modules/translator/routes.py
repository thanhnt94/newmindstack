from datetime import datetime
from sqlalchemy import func
from flask import request, jsonify
from flask_login import login_required, current_user
from . import translator_bp
from .services import TranslatorService
from ...core.error_handlers import error_response, success_response
from ...utils.template_helpers import render_dynamic_template
from mindstack_app.models import db, TranslationHistory

@translator_bp.route('/api/translate', methods=['POST'])
@login_required
def translate():
    """
    API to translate text.
    Body: { "text": "...", "source": "auto", "target": "vi" }
    """
    data = request.get_json()
    if not data or 'text' not in data:
        return error_response('Missing text', 'BAD_REQUEST', 400)

    text = data['text']
    if len(text) > 1000: # Simple limit
        return error_response('Text too long', 'BAD_REQUEST', 400)

    source = data.get('source', 'auto')
    target = data.get('target', 'vi')

    # Detect context - usually we want to record who translated what
    user_id = current_user.user_id
    
    result = TranslatorService.translate_text(text, source, target, user_id=user_id)
    
    if result:
        return success_response(data={'translated': result, 'source': source, 'original': text})
    else:
        return error_response('Translation failed', 'SERVER_ERROR', 500)

@translator_bp.route('/history', methods=['GET'])
@login_required
def history_page():
    """Render dedicated translation history page."""
    # Fetch all history for stats
    history = TranslatorService.get_user_history(current_user.user_id, limit=200)
    
    # Calculate today's count
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

@translator_bp.route('/api/history', methods=['GET'])
@login_required
def get_history():
    """Fetch recent translation history (JSON)."""
    history = TranslatorService.get_user_history(current_user.user_id)
    return success_response(data=[h.to_dict() for h in history])
