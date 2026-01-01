# File: mindstack_app/modules/learning/practice/routes.py
# Practice Module Routes
# Entry point for flashcard practice - delegates to flashcard engine.

from flask import render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user

from . import practice_bp

# Import từ flashcard engine
from ..flashcard.engine import (
    FlashcardSessionManager,
    FlashcardLearningConfig,
    get_flashcard_mode_counts,
    get_filtered_flashcard_sets,
    get_accessible_flashcard_set_ids,
)


@practice_bp.route('/')
@practice_bp.route('/flashcard')
@login_required
def flashcard_dashboard():
    """Dashboard cho chế độ luyện tập flashcard."""
    # Lấy cấu hình button count từ user session
    user_button_count = 3
    if current_user.session_state:
        user_button_count = current_user.session_state.flashcard_button_count

    return render_template(
        'v3/pages/learning/practice/default/dashboard.html',
        user_button_count=user_button_count,
        flashcard_modes=FlashcardLearningConfig.FLASHCARD_MODES,
    )


@practice_bp.route('/flashcard/setup')
@login_required
def flashcard_setup():
    """Trang thiết lập trước khi bắt đầu phiên luyện tập."""
    set_ids = request.args.get('sets', '')
    mode = request.args.get('mode', 'mixed_srs')
    
    user_button_count = 3
    if current_user.session_state:
        user_button_count = current_user.session_state.flashcard_button_count

    # Parse set IDs
    selected_sets = []
    if set_ids:
        try:
            selected_sets = [int(s) for s in set_ids.split(',') if s]
        except ValueError:
            flash('Định dạng ID bộ thẻ không hợp lệ.', 'danger')
            return redirect(url_for('learning.practice.flashcard_dashboard'))

    # Lấy các chế độ với số lượng thẻ
    set_identifier = selected_sets[0] if len(selected_sets) == 1 else selected_sets if selected_sets else 'all'
    modes = get_flashcard_mode_counts(current_user.user_id, set_identifier)

    return render_template(
        'v3/pages/learning/practice/default/setup.html',
        selected_sets=selected_sets,
        selected_mode=mode,
        modes=modes,
        user_button_count=user_button_count,
        flashcard_modes=FlashcardLearningConfig.FLASHCARD_MODES,
    )


@practice_bp.route('/flashcard/start', methods=['POST'])
@login_required
def flashcard_start():
    """Bắt đầu phiên luyện tập flashcard."""
    data = request.form or request.get_json() or {}
    
    set_ids_str = data.get('set_ids', '')
    mode = data.get('mode', 'mixed_srs')
    
    # Parse set IDs
    if set_ids_str == 'all':
        set_ids = 'all'
    elif set_ids_str:
        try:
            set_ids = [int(s) for s in set_ids_str.split(',') if s]
        except ValueError:
            flash('Định dạng ID bộ thẻ không hợp lệ.', 'danger')
            return redirect(url_for('learning.practice.flashcard_dashboard'))
    else:
        flash('Vui lòng chọn ít nhất một bộ thẻ.', 'warning')
        return redirect(url_for('learning.practice.flashcard_dashboard'))
    
    # Bắt đầu session sử dụng flashcard engine
    if FlashcardSessionManager.start_new_flashcard_session(set_ids, mode):
        return redirect(url_for('learning.practice.flashcard_session'))
    else:
        flash('Không có thẻ nào khả dụng để bắt đầu phiên học.', 'warning')
        return redirect(url_for('learning.practice.flashcard_dashboard'))


@practice_bp.route('/flashcard/session')
@login_required
def flashcard_session():
    """Hiển thị giao diện luyện tập flashcard."""
    from flask import session
    
    if 'flashcard_session' not in session:
        flash('Không có phiên luyện tập nào đang hoạt động.', 'info')
        return redirect(url_for('learning.practice.flashcard_dashboard'))

    user_button_count = 3
    if current_user.session_state:
        user_button_count = current_user.session_state.flashcard_button_count

    session_data = session.get('flashcard_session', {})
    session_mode = session_data.get('mode')
    is_autoplay_session = session_mode in ('autoplay_all', 'autoplay_learned')
    autoplay_mode = session_mode if is_autoplay_session else ''

    # Sử dụng template từ flashcard engine (shared)
    return render_template(
        'flashcard/individual/session/index.html',
        user_button_count=user_button_count,
        is_autoplay_session=is_autoplay_session,
        autoplay_mode=autoplay_mode,
        # Context để biết đang ở practice mode
        practice_mode=True,
    )


@practice_bp.route('/flashcard/api/sets')
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


@practice_bp.route('/flashcard/api/modes/<set_identifier>')
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
