# File: mindstack_app/modules/quiz/routes/individual_views.py
from flask import render_template, request, redirect, url_for, flash, session, current_app
from mindstack_app.utils.template_helpers import render_dynamic_template
from flask_login import login_required, current_user
from mindstack_app.models import LearningContainer, db, UserGoal
from .. import blueprint
from ..logics.session_logic import QuizSessionManager
from ..logics.algorithms import get_quiz_mode_counts, get_filtered_quiz_sets
from ..config import QuizModuleDefaultConfig
import json

@blueprint.route('/dashboard')
@login_required
def dashboard():
    """Hiển thị trang chính để chọn bộ câu hỏi và chế độ học Quiz."""
    search_query = request.args.get('q', '', type=str)
    search_field = request.args.get('search_field', 'all', type=str)
    current_filter = request.args.get('filter', 'doing', type=str)
    quiz_type = request.args.get('quiz_type', 'individual', type=str)

    pref_batch = current_user.last_preferences.get('quiz_question_count') if current_user.last_preferences else None
    
    if pref_batch:
        user_default_batch_size = pref_batch
    elif current_user.session_state and current_user.session_state.current_quiz_batch_size is not None:
        user_default_batch_size = current_user.session_state.current_quiz_batch_size
    else:
        user_default_batch_size = QuizModuleDefaultConfig.QUIZ_DEFAULT_BATCH_SIZE

    quiz_set_search_options = {
        'title': 'Tiêu đề', 'description': 'Mô tả', 'tags': 'Thẻ'
    }

    template_vars = {
        'search_query': search_query,
        'search_field': search_field,
        'quiz_set_search_options': quiz_set_search_options,
        'current_filter': current_filter,
        'user_default_batch_size': user_default_batch_size,
        'quiz_type': quiz_type
    }
    return render_dynamic_template('pages/learning/quiz/dashboard/index.html', **template_vars)


@blueprint.route('/set/<int:set_id>')
@login_required
def set_detail(set_id):
    """Render the wizard-style Quiz setup page."""
    container = LearningContainer.query.get_or_404(set_id)
    
    pref_batch = current_user.last_preferences.get('quiz_question_count') if current_user.last_preferences else None
    
    if pref_batch:
        user_default_batch_size = pref_batch
    elif current_user.session_state and current_user.session_state.current_quiz_batch_size is not None:
        user_default_batch_size = current_user.session_state.current_quiz_batch_size
    else:
        user_default_batch_size = QuizModuleDefaultConfig.QUIZ_DEFAULT_BATCH_SIZE

    modes = get_quiz_mode_counts(current_user.user_id, set_id)

    template_vars = {
        'container': container,
        'modes': modes,
        'user_default_batch_size': user_default_batch_size
    }
    return render_dynamic_template('pages/learning/quiz/individual/setup/index.html', **template_vars)


@blueprint.route('/get_quiz_modes_partial/all', methods=['GET'])
@login_required
def get_quiz_modes_partial_all():
    selected_mode = request.args.get('selected_mode', None, type=str)
    pref_batch = current_user.last_preferences.get('quiz_question_count') if current_user.last_preferences else None
    
    if pref_batch:
        user_default_batch_size = pref_batch
    elif current_user.session_state and current_user.session_state.current_quiz_batch_size is not None:
        user_default_batch_size = current_user.session_state.current_quiz_batch_size
    else:
        user_default_batch_size = QuizModuleDefaultConfig.QUIZ_DEFAULT_BATCH_SIZE

    modes = get_quiz_mode_counts(current_user.user_id, 'all')
    return render_dynamic_template('pages/learning/quiz/individual/setup/_modes_list.html',
        modes=modes,
        selected_set_id='all',
        selected_quiz_mode_id=selected_mode,
        user_default_batch_size=user_default_batch_size
    )


@blueprint.route('/get_quiz_modes_partial/multi/<string:set_ids_str>', methods=['GET'])
@login_required
def get_quiz_modes_partial_multi(set_ids_str):
    selected_mode = request.args.get('selected_mode', None, type=str)
    pref_batch = current_user.last_preferences.get('quiz_question_count') if current_user.last_preferences else None
    
    if pref_batch:
        user_default_batch_size = pref_batch
    elif current_user.session_state and current_user.session_state.current_quiz_batch_size is not None:
        user_default_batch_size = current_user.session_state.current_quiz_batch_size
    else:
        user_default_batch_size = QuizModuleDefaultConfig.QUIZ_DEFAULT_BATCH_SIZE

    try:
        set_ids = [int(s) for s in set_ids_str.split(',') if s]
        modes = get_quiz_mode_counts(current_user.user_id, set_ids)
    except ValueError:
        return '<p class="text-red-500 text-center">Lỗi: Định dạng ID bộ quiz không hợp lệ.</p>', 400

    return render_dynamic_template('pages/learning/quiz/individual/setup/_modes_list.html',
        modes=modes,
        selected_set_id='multi',
        selected_quiz_mode_id=selected_mode,
        user_default_batch_size=user_default_batch_size
    )


@blueprint.route('/get_quiz_modes_partial/<int:set_id>', methods=['GET'])
@login_required
def get_quiz_modes_partial_by_id(set_id):
    selected_mode = request.args.get('selected_mode', None, type=str)
    pref_batch = current_user.last_preferences.get('quiz_question_count') if current_user.last_preferences else None
    
    if pref_batch:
        user_default_batch_size = pref_batch
    elif current_user.session_state and current_user.session_state.current_quiz_batch_size is not None:
        user_default_batch_size = current_user.session_state.current_quiz_batch_size
    else:
        user_default_batch_size = QuizModuleDefaultConfig.QUIZ_DEFAULT_BATCH_SIZE

    modes = get_quiz_mode_counts(current_user.user_id, set_id)

    return render_dynamic_template('pages/learning/quiz/individual/setup/_modes_list.html',
        modes=modes,
        selected_set_id=str(set_id),
        selected_quiz_mode_id=selected_mode,
        user_default_batch_size=user_default_batch_size
    )


@blueprint.route('/get_quiz_custom_options/<int:set_id>')
@login_required
def get_quiz_custom_options(set_id):
    container = LearningContainer.query.get_or_404(set_id)
    
    from ..engine.core import QuizEngine
    available_columns = QuizEngine.get_available_content_keys(set_id)
    
    return render_dynamic_template('pages/learning/quiz/individual/setup/_quiz_custom_options.html',
        container=container,
        available_columns=available_columns
    )


@blueprint.route('/start_quiz_session/all/<string:mode>', methods=['GET'])
@login_required
def start_quiz_session_all(mode):
    set_ids = 'all'
    session_size = request.args.get('session_size', type=int) or request.args.get('batch_size', type=int)
    turn_size = request.args.get('turn_size', type=int, default=1)

    if not session_size:
        flash('Lỗi: Thiếu kích thước phiên học.', 'danger')
        return redirect(url_for('quiz.dashboard'))

    success, message, session_id = QuizSessionManager.start_new_quiz_session(set_ids, mode, session_size, turn_size)
    
    if success:
        if session_id:
            return redirect(url_for('quiz.quiz_session', session_id=session_id))
        else:
            return redirect(url_for('quiz.quiz_session'))
    else:
        flash(message or 'Không có bộ quiz nào khả dụng để bắt đầu phiên học.', 'warning')
        return redirect(url_for('quiz.dashboard'))


@blueprint.route('/start_quiz_session/multi/<string:mode>', methods=['GET'])
@login_required
def start_quiz_session_multi(mode):
    set_ids_str = request.args.get('set_ids')
    session_size = request.args.get('session_size', type=int) or request.args.get('batch_size', type=int)
    turn_size = request.args.get('turn_size', type=int, default=1)

    if not set_ids_str or not session_size:
        flash('Lỗi: Thiếu thông tin bộ câu hỏi hoặc kích thước phiên.', 'danger')
        return redirect(url_for('quiz.dashboard'))

    try:
        set_ids = [int(s) for s in set_ids_str.split(',') if s]
    except ValueError:
        flash('Lỗi: Định dạng ID bộ quiz không hợp lệ.', 'danger')
        return redirect(url_for('quiz.dashboard'))

    success, message, session_id = QuizSessionManager.start_new_quiz_session(set_ids, mode, session_size, turn_size)
    
    if success:
        if session_id:
            return redirect(url_for('quiz.quiz_session', session_id=session_id))
        else:
            return redirect(url_for('quiz.quiz_session'))
    else:
        flash(message or 'Không có bộ quiz nào khả dụng để bắt đầu phiên học.', 'warning')
        return redirect(url_for('quiz.dashboard'))


@blueprint.route('/start_quiz_session/<int:set_id>/<string:mode>', methods=['GET'])
@login_required
def start_quiz_session_by_id(set_id, mode):
    session_size = request.args.get('session_size', type=int) or request.args.get('batch_size', type=int)
    turn_size = request.args.get('turn_size', type=int, default=1)
    
    custom_pairs_str = request.args.get('custom_pairs')
    custom_pairs = None
    if custom_pairs_str:
        try:
            custom_pairs = json.loads(custom_pairs_str)
        except:
            current_app.logger.warning("Failed to parse custom_pairs JSON")
            pass

    if not session_size:
        flash('Lỗi: Thiếu kích thước phiên học.', 'danger')
        return redirect(url_for('quiz.dashboard'))

    try:
        if current_user.last_preferences is None:
            current_user.last_preferences = {}
        current_user.last_preferences = {**current_user.last_preferences, 'quiz_question_count': session_size, 'quiz_turn_size': turn_size}
        db.session.commit()
    except Exception as e:
        current_app.logger.warning(f"Failed to save quiz batch size preference: {e}")

    success, message, session_id = QuizSessionManager.start_new_quiz_session(set_id, mode, session_size, turn_size, custom_pairs=custom_pairs)
    
    if success:
        if session_id:
            return redirect(url_for('quiz.quiz_session', session_id=session_id))
        else:
             return redirect(url_for('quiz.quiz_session'))
    else:
        flash(message or 'Không có câu hỏi nào để bắt đầu phiên học với các lựa chọn này.', 'warning')
        return redirect(url_for('quiz.dashboard'))


@blueprint.route('/session')
@login_required
def quiz_active_session_redirect():
    from mindstack_app.modules.flashcard.services.session_service import LearningSessionService
    active_db_session = LearningSessionService.get_active_session(current_user.user_id, learning_mode='quiz')
    if active_db_session:
        return redirect(url_for('quiz.quiz_session', session_id=active_db_session.session_id))
    else:
        flash('Không có phiên học Quiz nào đang hoạt động. Vui lòng chọn bộ Quiz để bắt đầu.', 'info')
        return redirect(url_for('quiz.dashboard'))


@blueprint.route('/session/<int:session_id>')
@login_required
def quiz_session(session_id):
    """Hiển thị giao diện làm bài Quiz."""
    current_session_data = session.get('quiz_session')
    should_reload = False
    
    if not current_session_data:
        should_reload = True
    elif current_session_data.get('db_session_id') != session_id:
        should_reload = True
        
    if should_reload:
        from mindstack_app.modules.flashcard.services.session_service import LearningSessionService
        db_session = LearningSessionService.get_session_by_id(session_id)
        
        if not db_session or db_session.user_id != current_user.user_id:
             flash('Phiên học không tồn tại hoặc bạn không có quyền truy cập.', 'danger')
             return redirect(url_for('quiz.dashboard'))
             
        if db_session.end_time:
             flash('Phiên học này đã kết thúc.', 'info')
             return redirect(url_for('quiz.dashboard'))

        session_manager = QuizSessionManager(
            user_id=db_session.user_id,
            set_id=db_session.set_id_data,
            mode=db_session.mode_config_id,
            batch_size=1,
            total_items_in_session=db_session.total_items,
            processed_item_ids=db_session.processed_item_ids or [],
            correct_answers=db_session.correct_count,
            incorrect_answers=db_session.incorrect_count,
            start_time=db_session.start_time.isoformat() if db_session.start_time else None,
            common_pre_question_text_global=None, 
            db_session_id=db_session.session_id
        )
        if current_user.session_state and current_user.session_state.current_quiz_batch_size:
            session_manager.batch_size = current_user.session_state.current_quiz_batch_size
        
        session['quiz_session'] = session_manager.to_dict()
        session.modified = True

    try:
        session_manager = QuizSessionManager.from_dict(session['quiz_session'])
        
        from mindstack_app.services.template_service import TemplateService
        if TemplateService.get_active_version() == 'aura_mobile':
             return render_dynamic_template('pages/learning/quiz/individual/session/index.html')

        return render_dynamic_template('pages/learning/quiz/individual/session/index.html')
    except Exception as e:
        current_app.logger.error(f"Error loading quiz session: {e}", exc_info=True)
        return f"<h3>Lỗi tải phiên học:</h3><pre>{str(e)}</pre><p>Vui lòng quay lại Dashboard và thử lại.</p>", 500
