# File: mindstack_app/modules/learning/practice/routes.py
# Practice Module Routes
# Entry point for flashcard practice - delegates to flashcard engine.

from flask import render_template, request, redirect, url_for, flash, jsonify
from mindstack_app.utils.template_helpers import render_dynamic_template
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
@login_required
def practice_hub():
    """Hub trang chính cho Practice - chọn Flashcard hoặc Quiz."""
    return render_dynamic_template('pages/learning/practice/default/hub.html')


@practice_bp.route('/flashcard')
@practice_bp.route('/flashcard/')
@login_required
def flashcard_dashboard():
    """Dashboard cho chế độ luyện tập flashcard."""
    # Lấy cấu hình button count từ user session
    user_button_count = 3
    if current_user.session_state:
        user_button_count = current_user.session_state.flashcard_button_count

    return render_dynamic_template('pages/learning/practice/default/dashboard.html',
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

    return render_dynamic_template('pages/learning/practice/setup.html',
        selected_sets=selected_sets,
        selected_mode=mode,
        modes=modes,
        user_button_count=user_button_count,
        flashcard_modes=FlashcardLearningConfig.FLASHCARD_MODES,
    )


@practice_bp.route('/flashcard/start', methods=['GET', 'POST'])
@login_required
def flashcard_start():
    """Bắt đầu phiên luyện tập flashcard."""
    data = request.values or {}
    
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
    success, message = FlashcardSessionManager.start_new_flashcard_session(set_ids, mode)
    if success:
        return redirect(url_for('learning.practice.flashcard_session'))
    else:
        flash(message, 'warning')
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
    
    # Get active version
    from mindstack_app.services.template_service import TemplateService
    version = TemplateService.get_active_version()
    template_base_path = f'{version}/pages/learning/flashcard/session'

    # Sử dụng template từ flashcard engine (shared)
    return render_dynamic_template('pages/learning/flashcard/session/index.html',
        user_button_count=user_button_count,
        is_autoplay_session=is_autoplay_session,
        autoplay_mode=autoplay_mode,
        # Context để biết đang ở practice mode
        practice_mode=True,
        # Template base path for includes
        template_base_path=template_base_path,
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


# ============================================
# Quiz Practice Routes
# ============================================

@practice_bp.route('/quiz')
@practice_bp.route('/quiz/')
@login_required
def quiz_dashboard():
    """Dashboard cho chế độ luyện tập Quiz đa bộ."""
    return render_dynamic_template('pages/learning/practice/default/quiz_dashboard.html')


@practice_bp.route('/quiz/start', methods=['GET', 'POST'])
@login_required
def quiz_start():
    """Bắt đầu phiên luyện tập Quiz đa bộ."""
    from ..quiz.individual.logics.session_logic import QuizSessionManager
    
    data = request.values or {}
    
    set_ids_str = data.get('set_ids', '')
    mode = data.get('mode', 'new_only')
    batch_size = data.get('batch_size', 10, type=int)
    
    # Parse set IDs
    if set_ids_str == 'all':
        set_ids = 'all'
    elif set_ids_str:
        try:
            set_ids = [int(s) for s in set_ids_str.split(',') if s]
        except ValueError:
            flash('Định dạng ID bộ quiz không hợp lệ.', 'danger')
            return redirect(url_for('learning.practice.quiz_dashboard'))
    else:
        flash('Vui lòng chọn ít nhất một bộ quiz.', 'warning')
        return redirect(url_for('learning.practice.quiz_dashboard'))
    
    # Bắt đầu session sử dụng quiz engine
    if QuizSessionManager.start_new_quiz_session(set_ids, mode, batch_size):
        return redirect(url_for('learning.quiz_learning.quiz_session'))
    else:
        flash('Không có câu hỏi nào khả dụng để bắt đầu phiên học.', 'warning')
        return redirect(url_for('learning.practice.quiz_dashboard'))


@practice_bp.route('/quiz/api/sets')
@login_required
def api_get_quiz_sets():
    """API lấy danh sách bộ Quiz cho practice."""
    from ..quiz.individual.logics.algorithms import get_filtered_quiz_sets
    
    page = request.args.get('page', 1, type=int)
    search = request.args.get('q', '', type=str)
    search_field = request.args.get('search_field', 'all', type=str)
    current_filter = request.args.get('filter', 'doing', type=str)

    try:
        pagination = get_filtered_quiz_sets(
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
                'question_count': getattr(item, 'question_count', 0),
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


@practice_bp.route('/quiz/api/modes/<set_identifier>')
@login_required
def api_get_quiz_modes(set_identifier):
    """API lấy các chế độ học Quiz với số lượng câu hỏi."""
    from ..quiz.individual.logics.algorithms import get_quiz_mode_counts
    
    try:
        if set_identifier == 'all':
            modes = get_quiz_mode_counts(current_user.user_id, 'all')
        else:
            set_ids = [int(s) for s in set_identifier.split(',') if s]
            if len(set_ids) == 1:
                modes = get_quiz_mode_counts(current_user.user_id, set_ids[0])
            else:
                modes = get_quiz_mode_counts(current_user.user_id, set_ids)
        
        return jsonify({'success': True, 'modes': modes})
    except ValueError:
        return jsonify({'success': False, 'message': 'ID bộ quiz không hợp lệ.'}), 400
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


@practice_bp.route('/quiz/api/check_session')
@login_required
def api_check_quiz_session():
    """API kiểm tra xem có phiên Quiz đang hoạt động không."""
    from ..quiz.individual.logics.session_logic import QuizSessionManager
    
    session_data = QuizSessionManager.get_session_status()
    if session_data:
        return jsonify({
            'success': True,
            'has_session': True,
            'session_info': {
                'mode': session_data.get('mode', ''),
                'total_items': session_data.get('total_items_in_session', 0),
                'answered': session_data.get('current_question_index', 0),
                'correct': session_data.get('correct_answers', 0),
                'incorrect': session_data.get('incorrect_answers', 0),
            }
        })
    return jsonify({'success': True, 'has_session': False})


@practice_bp.route('/quiz/api/clear_session', methods=['POST'])
@login_required
def api_clear_quiz_session():
    """API xóa phiên Quiz hiện tại."""
    from ..quiz.individual.logics.session_logic import QuizSessionManager
    
    QuizSessionManager.end_quiz_session()
    return jsonify({'success': True, 'message': 'Đã xóa phiên học cũ.'})
