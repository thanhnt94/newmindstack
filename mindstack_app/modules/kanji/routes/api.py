from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user

kanji_api_bp = Blueprint('kanji_api', __name__, url_prefix='/api/kanji')


@kanji_api_bp.route('/directory')
@login_required
def api_get_directory():
    from ..interface import KanjiInterface
    directory_data = KanjiInterface.get_directory()
    return jsonify(directory_data)

@kanji_api_bp.route('/<char>/details')
@login_required
def api_get_details(char):
    from ..interface import KanjiInterface
    details = KanjiInterface.get_details(char)
    if details:
        decompositions = KanjiInterface.get_decompositions(char)
        details['decompositions'] = decompositions
        
        # Translate mnemonic dynamically if exists
        try:
            hint = details.get('mnemonic_hint')
            if hint:
                from deep_translator import GoogleTranslator
                translator = GoogleTranslator(source='en', target='vi')
                # Lowercase to trick Google Translate into translating English proper nouns
                hint_vi = translator.translate(hint.lower())
                if hint_vi:
                    hint_vi = hint_vi[0].upper() + hint_vi[1:]
                details['mnemonic_hint_vi'] = hint_vi
        except Exception as e:
            pass

    # Record search in user history
    try:
        from ..services.kanji_history_service import KanjiHistoryService
        entry = KanjiHistoryService.record_search(current_user.user_id, char)
        if entry:
            details = details or {}
            details['user_stats'] = {
                'search_count': entry.search_count,
                'first_searched_at': entry.first_searched_at.isoformat() + 'Z' if entry.first_searched_at else None,
                'last_searched_at': entry.last_searched_at.isoformat() + 'Z' if entry.last_searched_at else None,
                'note': entry.note,
            }
    except Exception:
        pass

    return {"details": details}


@kanji_api_bp.route('/<char>/similar')
def api_get_similar(char):
    from ..interface import KanjiInterface
    results = KanjiInterface.get_similar_kanji(char)
    return {"results": results}


@kanji_api_bp.route('/<char>/components')
def api_get_components(char):
    from ..interface import KanjiInterface
    components = KanjiInterface.get_components(char)
    return {"components": components}


# ── User History ────────────────────────────────────────────

@kanji_api_bp.route('/history')
@login_required
def api_get_history():
    """Return the user's Kanji search history."""
    from ..services.kanji_history_service import KanjiHistoryService
    limit = request.args.get('limit', 50, type=int)
    entries = KanjiHistoryService.get_user_history(current_user.user_id, limit=limit)
    return jsonify([e.to_dict() for e in entries])


@kanji_api_bp.route('/history/<char>', methods=['DELETE'])
@login_required
def api_delete_history(char):
    """Remove a Kanji from the user's search history."""
    from ..services.kanji_history_service import KanjiHistoryService
    success = KanjiHistoryService.delete_history_entry(current_user.user_id, char)
    if success:
        return jsonify({'status': 'ok'})
    return jsonify({'status': 'not_found'}), 404


# ── User Notes ──────────────────────────────────────────────

@kanji_api_bp.route('/<char>/note', methods=['GET'])
@login_required
def api_get_note(char):
    """Get the user's personal note for a Kanji."""
    from ..services.kanji_history_service import KanjiHistoryService
    note = KanjiHistoryService.get_note(current_user.user_id, char)
    return jsonify({'kanji': char, 'note': note})


@kanji_api_bp.route('/<char>/note', methods=['POST'])
@login_required
def api_save_note(char):
    """Save or update the user's personal note for a Kanji."""
    from ..services.kanji_history_service import KanjiHistoryService
    data = request.get_json(silent=True) or {}
    note = data.get('note', '')
    entry = KanjiHistoryService.update_note(current_user.user_id, char, note)
    if entry:
        return jsonify({'status': 'ok', 'note': entry.note})
    return jsonify({'status': 'error'}), 500
