# File: quiz/individual/routes/main.py
# MỤC ĐÍCH: Session routes - render HTML templates
# Refactored from routes.py

from flask import render_template, request, redirect, url_for, flash, session, current_app, jsonify
from flask_login import login_required, current_user
from sqlalchemy import or_

from . import quiz_learning_bp
from ..logics.session_logic import QuizSessionManager
from ..logics.algorithms import get_quiz_mode_counts, get_filtered_quiz_sets
from ..config import QuizLearningConfig
from mindstack_app.models import LearningContainer, LearningItem, User, UserContainerState
import json


@quiz_learning_bp.route('/quiz/dashboard')
@login_required
def dashboard():
    """Hiển thị trang chính để chọn bộ câu hỏi và chế độ học Quiz."""
    search_query = request.args.get('q', '', type=str)
    search_field = request.args.get('search_field', 'all', type=str)
    current_filter = request.args.get('filter', 'doing', type=str)
    quiz_type = request.args.get('quiz_type', 'individual', type=str)

    # Logic xác định batch size mặc định: Preference > Session > Config
    pref_batch = current_user.last_preferences.get('quiz_question_count') if current_user.last_preferences else None
    
    if pref_batch:
        user_default_batch_size = pref_batch
    elif current_user.session_state and current_user.session_state.current_quiz_batch_size is not None:
        user_default_batch_size = current_user.session_state.current_quiz_batch_size
    else:
        user_default_batch_size = QuizLearningConfig.QUIZ_DEFAULT_BATCH_SIZE

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
    return render_template('v3/pages/learning/quiz/dashboard/default/index.html', **template_vars)


@quiz_learning_bp.route('/get_quiz_modes_partial/all', methods=['GET'])
@login_required
def get_quiz_modes_partial_all():
    """Trả về partial HTML chứa các chế độ học và số lượng câu hỏi tương ứng cho TẤT CẢ các bộ Quiz."""
    selected_mode = request.args.get('selected_mode', None, type=str)
    # Logic xác định batch size mặc định: Preference > Session > Config
    pref_batch = current_user.last_preferences.get('quiz_question_count') if current_user.last_preferences else None
    
    if pref_batch:
        user_default_batch_size = pref_batch
    elif current_user.session_state and current_user.session_state.current_quiz_batch_size is not None:
        user_default_batch_size = current_user.session_state.current_quiz_batch_size
    else:
        user_default_batch_size = QuizLearningConfig.QUIZ_DEFAULT_BATCH_SIZE

    modes = get_quiz_mode_counts(current_user.user_id, 'all')
    return render_template(
        'v3/pages/learning/quiz/individual/setup/default/_modes_list.html',
        modes=modes,
        selected_set_id='all',
        selected_quiz_mode_id=selected_mode,
        user_default_batch_size=user_default_batch_size
    )


@quiz_learning_bp.route('/get_quiz_modes_partial/multi/<string:set_ids_str>', methods=['GET'])
@login_required
def get_quiz_modes_partial_multi(set_ids_str):
    """Trả về partial HTML chứa các chế độ học và số lượng câu hỏi tương ứng cho NHIỀU bộ Quiz."""
    selected_mode = request.args.get('selected_mode', None, type=str)
    # Logic xác định batch size mặc định: Preference > Session > Config
    pref_batch = current_user.last_preferences.get('quiz_question_count') if current_user.last_preferences else None
    
    if pref_batch:
        user_default_batch_size = pref_batch
    elif current_user.session_state and current_user.session_state.current_quiz_batch_size is not None:
        user_default_batch_size = current_user.session_state.current_quiz_batch_size
    else:
        user_default_batch_size = QuizLearningConfig.QUIZ_DEFAULT_BATCH_SIZE

    try:
        set_ids = [int(s) for s in set_ids_str.split(',') if s]
        modes = get_quiz_mode_counts(current_user.user_id, set_ids)
    except ValueError:
        return '<p class="text-red-500 text-center">Lỗi: Định dạng ID bộ quiz không hợp lệ.</p>', 400

    return render_template(
        'v3/pages/learning/quiz/individual/setup/default/_modes_list.html',
        modes=modes,
        selected_set_id='multi',
        selected_quiz_mode_id=selected_mode,
        user_default_batch_size=user_default_batch_size
    )


@quiz_learning_bp.route('/get_quiz_modes_partial/<int:set_id>', methods=['GET'])
@login_required
def get_quiz_modes_partial_by_id(set_id):
    """Trả về partial HTML chứa các chế độ học và số lượng câu hỏi tương ứng cho một bộ Quiz cụ thể."""
    selected_mode = request.args.get('selected_mode', None, type=str)
    # Logic xác định batch size mặc định: Preference > Session > Config
    pref_batch = current_user.last_preferences.get('quiz_question_count') if current_user.last_preferences else None
    
    if pref_batch:
        user_default_batch_size = pref_batch
    elif current_user.session_state and current_user.session_state.current_quiz_batch_size is not None:
        user_default_batch_size = current_user.session_state.current_quiz_batch_size
    else:
        user_default_batch_size = QuizLearningConfig.QUIZ_DEFAULT_BATCH_SIZE

    modes = get_quiz_mode_counts(current_user.user_id, set_id)

    return render_template(
        'v3/pages/learning/quiz/individual/setup/default/_modes_list.html',
        modes=modes,
        selected_set_id=str(set_id),
        selected_quiz_mode_id=selected_mode,
        user_default_batch_size=user_default_batch_size
    )


@quiz_learning_bp.route('/get_quiz_custom_options/<int:set_id>')
@login_required
def get_quiz_custom_options(set_id):
    """Render the Custom Options partial for customizing question pairs."""
    container = LearningContainer.query.get_or_404(set_id)
    
    # Check simple access (Read access)
    # Ideally should use comprehensive permission check, but basic ownership/public check for now
    if not container.is_public and container.creator_user_id != current_user.user_id:
        # Check if contributor logic needed? For now allow if can view set.
        pass

    from ...engine import QuizEngine
    available_columns = QuizEngine.get_available_content_keys(set_id)
    
    return render_template(
        'v3/pages/learning/quiz/individual/setup/default/_quiz_custom_options.html',
        container=container,
        available_columns=available_columns
    )


@quiz_learning_bp.route('/start_quiz_session/all/<string:mode>', methods=['GET'])
@login_required
def start_quiz_session_all(mode):
    """Bắt đầu một phiên học Quiz cho TẤT CẢ các bộ câu hỏi với chế độ và kích thước nhóm câu đã chọn."""
    set_ids = 'all'
    batch_size = request.args.get('batch_size', type=int)

    if not batch_size:
        flash('Lỗi: Thiếu kích thước nhóm câu hỏi.', 'danger')
        return redirect(url_for('learning.quiz_learning.dashboard'))

    if QuizSessionManager.start_new_quiz_session(set_ids, mode, batch_size):
        return redirect(url_for('learning.quiz_learning.quiz_session'))
    else:
        flash('Không có bộ quiz nào khả dụng để bắt đầu phiên học.', 'warning')
        return redirect(url_for('learning.quiz_learning.dashboard'))


@quiz_learning_bp.route('/start_quiz_session/multi/<string:mode>', methods=['GET'])
@login_required
def start_quiz_session_multi(mode):
    """Bắt đầu một phiên học Quiz cho nhiều bộ câu hỏi với chế độ và kích thước nhóm câu đã chọn."""
    set_ids_str = request.args.get('set_ids')
    batch_size = request.args.get('batch_size', type=int)

    if not set_ids_str or not batch_size:
        flash('Lỗi: Thiếu thông tin bộ câu hỏi hoặc kích thước nhóm.', 'danger')
        return redirect(url_for('learning.quiz_learning.dashboard'))

    try:
        set_ids = [int(s) for s in set_ids_str.split(',') if s]
    except ValueError:
        flash('Lỗi: Định dạng ID bộ quiz không hợp lệ.', 'danger')
        return redirect(url_for('learning.quiz_learning.dashboard'))

    if QuizSessionManager.start_new_quiz_session(set_ids, mode, batch_size):
        return redirect(url_for('learning.quiz_learning.quiz_session'))
    else:
        flash('Không có bộ quiz nào khả dụng để bắt đầu phiên học.', 'warning')
        return redirect(url_for('learning.quiz_learning.dashboard'))


@quiz_learning_bp.route('/start_quiz_session/<int:set_id>/<string:mode>', methods=['GET'])
@login_required
def start_quiz_session_by_id(set_id, mode):
    """Bắt đầu một phiên học Quiz cho một bộ câu hỏi cụ thể với chế độ và kích thước nhóm câu đã chọn."""
    batch_size = request.args.get('batch_size', type=int)
    
    custom_pairs_str = request.args.get('custom_pairs')
    custom_pairs = None
    if custom_pairs_str:
        try:
            custom_pairs = json.loads(custom_pairs_str)
        except:
            current_app.logger.warning("Failed to parse custom_pairs JSON")
            pass

    if not batch_size:
        flash('Lỗi: Thiếu kích thước nhóm câu hỏi.', 'danger')
        return redirect(url_for('learning.quiz_learning.dashboard'))

    if QuizSessionManager.start_new_quiz_session(set_id, mode, batch_size, custom_pairs=custom_pairs):
        return redirect(url_for('learning.quiz_learning.quiz_session'))
    else:
        flash('Không có câu hỏi nào để bắt đầu phiên học với các lựa chọn này.', 'warning')
        return redirect(url_for('learning.quiz_learning.dashboard'))


@quiz_learning_bp.route('/quiz_session')
@login_required
def quiz_session():
    """Hiển thị giao diện làm bài Quiz."""
    if 'quiz_session' not in session:
        flash('Không có phiên học Quiz nào đang hoạt động. Vui lòng chọn bộ Quiz để bắt đầu.', 'info')
        return redirect(url_for('learning.quiz_learning.dashboard'))

    try:
        session_manager = QuizSessionManager.from_dict(session['quiz_session'])
        batch_size = session_manager.batch_size if session_manager else None
        current_app.logger.debug(f"Quiz session batch_size: {batch_size} (type: {type(batch_size)})")
        
        # Robust check for batch size 1
        is_single_mode = False
        if session_manager and batch_size is not None:
            try:
                if int(batch_size) == 1:
                    is_single_mode = True
            except (ValueError, TypeError):
                pass

        if is_single_mode:
            return render_template('v3/pages/learning/quiz/individual/session/default/_session_single.html')
        else:
            return render_template('v3/pages/learning/quiz/individual/session/default/_session_batch.html')
    except Exception as e:
        current_app.logger.error(f"Error loading quiz session: {e}", exc_info=True)
        # DEBUG: Return error directly to see what failed
        return f"<h3>Lỗi tải phiên học:</h3><pre>{str(e)}</pre><p>Vui lòng quay lại Dashboard và thử lại.</p>", 500


@quiz_learning_bp.route('/get_quiz_sets_partial', methods=['GET'])
@login_required
def get_quiz_sets_partial():
    """Trả về partial HTML chứa danh sách các bộ Quiz, có hỗ trợ tìm kiếm và phân trang."""
    import traceback
    
    current_app.logger.debug(">>> Bắt đầu thực thi get_quiz_sets_partial <<<")
    page = request.args.get('page', 1, type=int)
    search_query = request.args.get('q', '', type=str)
    search_field = request.args.get('search_field', 'all', type=str)
    current_filter = request.args.get('filter', 'doing', type=str)

    try:
        pagination = get_filtered_quiz_sets(
            user_id=current_user.user_id,
            search_query=search_query,
            search_field=search_field,
            current_filter=current_filter,
            page=page,
            per_page=current_app.config['ITEMS_PER_PAGE']
        )
        quiz_sets = pagination.items

        template_vars = {
            'quiz_sets': quiz_sets,
            'pagination': pagination,
            'search_query': search_query,
            'search_field': search_field,
            'search_options_display': {
                'title': 'Tiêu đề', 'description': 'Mô tả', 'tags': 'Thẻ'
            },
            'current_filter': current_filter
        }

        current_app.logger.debug("<<< Kết thúc thực thi get_quiz_sets_partial (Thành công) >>>")
        return render_template('v3/pages/learning/quiz/individual/setup/default/_sets_list.html', **template_vars)

    except Exception as e:
        print(f">>> PYTHON LỖI: Đã xảy ra lỗi trong get_quiz_sets_partial: {e}")
        print(traceback.format_exc())
        current_app.logger.error(f"LỖI NGHIÊM TRỌNG khi tải danh sách bộ Quiz qua AJAX: {e}", exc_info=True)
        current_app.logger.debug("<<< Kết thúc thực thi get_quiz_sets_partial (LỖI) >>>")
        return '<p class="text-red-500 text-center py-4">Đã xảy ra lỗi khi tải danh sách bộ câu hỏi. Vui lòng thử lại.</p>', 500


# ============================================
# API Endpoints (JSON - giống Vocabulary)
# ============================================

@quiz_learning_bp.route('/api/sets')
@login_required
def api_get_quiz_sets():
    """API to get quiz sets with search and category filter (like Vocabulary)."""
    search = request.args.get('q', '').strip()
    category = request.args.get('category', 'my')  # my, learning, explore
    page = request.args.get('page', 1, type=int)
    per_page = 10
    
    # Query quiz sets
    query = LearningContainer.query.filter(
        LearningContainer.container_type == 'QUIZ_SET'
    )
    
    # Category filter
    if category == 'my':
        # Sets created by user
        query = query.filter(LearningContainer.creator_user_id == current_user.user_id)
    elif category == 'learning':
        # Sets user is currently learning (has UserContainerState)
        learning_ids = [
            ucs.container_id for ucs in 
            UserContainerState.query.filter_by(
                user_id=current_user.user_id,
                is_archived=False
            ).all()
        ]
        # Also filter to only QUIZ_SET within those IDs
        query = query.filter(LearningContainer.container_id.in_(learning_ids))
    elif category == 'explore':
        # Public sets not created by user
        query = query.filter(
            LearningContainer.is_public == True,
            LearningContainer.creator_user_id != current_user.user_id
        )
    
    # Search filter
    if search:
        query = query.filter(
            or_(
                LearningContainer.title.ilike(f'%{search}%'),
                LearningContainer.description.ilike(f'%{search}%')
            )
        )
    
    # Order by last accessed or created
    query = query.order_by(LearningContainer.created_at.desc())
    
    # Paginate
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    
    # Build response
    sets = []
    for c in pagination.items:
        question_count = LearningItem.query.filter(
            LearningItem.container_id == c.container_id,
            LearningItem.item_type.in_(['QUESTION', 'FLASHCARD', 'QUIZ_MCQ'])
        ).count()
        
        # Get creator info
        creator = User.query.get(c.creator_user_id)
        
        sets.append({
            'id': c.container_id,
            'title': c.title,
            'description': c.description or '',
            'cover_image': c.cover_image,
            'question_count': question_count,
            'creator_name': creator.username if creator else 'Unknown',
            'is_public': c.is_public,
        })
    
    return jsonify({
        'success': True,
        'sets': sets,
        'has_next': pagination.has_next,
        'has_prev': pagination.has_prev,
        'page': page,
        'total': pagination.total
    })


@quiz_learning_bp.route('/api/set/<int:set_id>')
@login_required
def api_get_quiz_set_detail(set_id):
    """API to get detailed info about a quiz set."""
    container = LearningContainer.query.get_or_404(set_id)
    
    question_count = LearningItem.query.filter(
        LearningItem.container_id == container.container_id,
        LearningItem.item_type.in_(['QUESTION', 'FLASHCARD', 'QUIZ_MCQ'])
    ).count()
    
    # Get creator
    creator = User.query.get(container.creator_user_id)
    
    # Get modes with counts
    modes = get_quiz_mode_counts(current_user.user_id, set_id)
    
    return jsonify({
        'success': True,
        'set': {
            'id': container.container_id,
            'title': container.title,
            'description': container.description or '',
            'cover_image': container.cover_image,
            'question_count': question_count,
            'creator_name': creator.username if creator else 'Unknown',
            'is_public': container.is_public,
        },
        'modes': modes
    })

