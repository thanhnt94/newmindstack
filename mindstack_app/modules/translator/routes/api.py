from flask import request
from flask_login import login_required, current_user
from mindstack_app.core.error_handlers import error_response, success_response
from ..services import TranslatorService
from .. import blueprint

@blueprint.route('/api/translate', methods=['POST'])
@login_required
def translate():
    """
    API to translate text.
    """
    data = request.get_json()
    if not data or 'text' not in data:
        return error_response('Missing text', 'BAD_REQUEST', 400)

    text = data['text']
    if len(text) > 1000:
        return error_response('Text too long', 'BAD_REQUEST', 400)

    source = data.get('source', 'auto')
    target = data.get('target', 'vi')
    user_id = current_user.user_id
    
    result = TranslatorService.translate_text(text, source, target, user_id=user_id)
    
    if result:
        return success_response(data={'translated': result, 'source': source, 'original': text})
    else:
        return error_response('Translation failed', 'SERVER_ERROR', 500)

@blueprint.route('/api/history', methods=['GET'])
@login_required
def get_history():
    """Fetch recent translation history (JSON)."""
    history = TranslatorService.get_user_history(current_user.user_id)
    return success_response(data=[h.to_dict() for h in history])
