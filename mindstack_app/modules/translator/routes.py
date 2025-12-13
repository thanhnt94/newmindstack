from flask import request, jsonify
from flask_login import login_required, current_user
from . import translator_bp
from .services import TranslatorService

@translator_bp.route('/api/translate', methods=['POST'])
@login_required
def translate():
    """
    API to translate text.
    Body: { "text": "...", "source": "auto", "target": "vi" }
    """
    data = request.get_json()
    if not data or 'text' not in data:
        return jsonify({'error': 'Missing text'}), 400

    text = data['text']
    if len(text) > 1000: # Simple limit
        return jsonify({'error': 'Text too long'}), 400

    source = data.get('source', 'auto')
    target = data.get('target', 'vi')

    # Detect if Japanese or English (basic heuristic if needed, or rely on auto)
    # The user mentioned English/Japanese -> Vietnamese
    
    result = TranslatorService.translate_text(text, source, target)
    
    if result:
        return jsonify({'translated': result, 'source': source, 'original': text})
    else:
        return jsonify({'error': 'Translation failed'}), 500
