# File: mindstack_app/modules/vocab_flashcard/routes/api.py
from flask import request, jsonify
from flask_login import login_required, current_user
from . import api_bp as blueprint
from ..engine.algorithms import get_filtered_flashcard_sets, get_flashcard_mode_counts

@blueprint.route('/api/sets')
@login_required
def api_get_sets():
    """API lấy danh sách bộ thẻ cho practice."""
    page = request.args.get('page', 1, type=int)
    search = request.args.get('q', '', type=str)
    search_field = request.args.get('search_field', 'all', type=str)
    current_filter = request.args.get('filter', 'doing', type=str)

    try:
        pagination = get_filtered_flashcard_sets(
            user_id=current_user.user_id,
            search_query=search,
            search_field=search_field,
            current_filter=current_filter,
            page=page,
            per_page=12
        )

        sets = []
        for item in pagination.items:
            sets.append({
                'id': item.container_id,
                'title': item.title,
                'description': item.description or '',
                'cover_image': item.cover_image,
                'total_items': getattr(item, 'total_items', 0),
                'completion_percentage': getattr(item, 'completion_percentage', 0),
                'item_count_display': getattr(item, 'item_count_display', '0 / 0'),
            })

        return jsonify({
            'success': True,
            'sets': sets,
            'has_next': pagination.has_next,
            'has_prev': pagination.has_prev,
            'page': page,
            'total': pagination.total,
        })
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


@blueprint.route('/api/modes/<set_identifier>')
@login_required
def api_get_modes(set_identifier):
    """API lấy các chế độ học với số lượng thẻ."""
    try:
        if set_identifier == 'all':
            modes = get_flashcard_mode_counts(current_user.user_id, 'all')
        else:
            set_ids = [int(s) for s in set_identifier.split(',') if s]
            if len(set_ids) == 1:
                modes = get_flashcard_mode_counts(current_user.user_id, set_ids[0])
            else:
                modes = get_flashcard_mode_counts(current_user.user_id, set_ids)
        
        return jsonify({'success': True, 'modes': modes})
    except ValueError:
        return jsonify({'success': False, 'message': 'ID bộ thẻ không hợp lệ.'}), 400
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500
