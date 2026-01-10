from flask import request
from flask_login import login_required
from . import translator_bp
from .services import TranslatorService
from ...core.error_handlers import error_response, success_response

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

    # Detect if Japanese or English (basic heuristic if needed, or rely on auto)
    # The user mentioned English/Japanese -> Vietnamese
    
    result = TranslatorService.translate_text(text, source, target)
    
    if result:
        return success_response(data={'translated': result, 'source': source, 'original': text})
    else:
        return error_response('Translation failed', 'SERVER_ERROR', 500)
