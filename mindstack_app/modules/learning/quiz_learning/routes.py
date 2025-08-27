# File: mindstack_app/modules/learning/quiz_learning/routes.py
# Phiên bản: 1.57
# Mục đích: Định nghĩa các routes và logic cho module học Quiz.
# ĐÃ THÊM: Logic cập nhật trường 'last_accessed' trong UserContainerState khi người dùng gửi đáp án.

from flask import Blueprint, render_template, request, jsonify, abort, current_app, redirect, url_for, flash, session
from flask_login import login_required, current_user
import traceback
from .algorithms import get_new_only_items, get_reviewed_items, get_hard_items, get_filtered_quiz_sets, get_quiz_mode_counts
from .session_manager import QuizSessionManager
from .config import QuizLearningConfig
from ....models import db, User, UserContainerState, LearningContainer
from sqlalchemy.sql import func # THÊM MỚI: Import func để lấy thời gian hiện tại


quiz_learning_bp = Blueprint('quiz_learning', __name__,
                             template_folder='templates')


@quiz_learning_bp.route('/quiz_learning_dashboard')
@login_required
def quiz_learning_dashboard():
    """
    Hiển thị trang chính để chọn bộ câu hỏi và chế độ học Quiz.
    """
    search_query = request.args.get('q', '', type=str)
    search_field = request.args.get('search_field', 'all', type=str)
    current_filter = request.args.get('filter', 'doing', type=str)

    user_default_batch_size = current_user.current_quiz_batch_size if current_user.current_quiz_batch_size is not None else QuizLearningConfig.QUIZ_DEFAULT_BATCH_SIZE

    quiz_set_search_options = {
        'title': 'Tiêu đề', 'description': 'Mô tả', 'tags': 'Thẻ'
    }
    
    template_vars = {
        'search_query': search_query, 
        'search_field': search_field,
        'quiz_set_search_options': quiz_set_search_options, 
        'current_filter': current_filter,
        'user_default_batch_size': user_default_batch_size
    }
    return render_template('quiz_learning_dashboard.html', **template_vars)

@quiz_learning_bp.route('/get_quiz_modes_partial/all', methods=['GET'])
@login_required
def get_quiz_modes_partial_all():
    """
    Trả về partial HTML chứa các chế độ học và số lượng câu hỏi tương ứng cho TẤT CẢ các bộ Quiz.
    """
    selected_mode = request.args.get('selected_mode', None, type=str)
    user_default_batch_size = current_user.current_quiz_batch_size if current_user.current_quiz_batch_size is not None else QuizLearningConfig.QUIZ_DEFAULT_BATCH_SIZE

    modes = get_quiz_mode_counts(current_user.user_id, 'all')
    return render_template('_quiz_modes_selection.html', 
                           modes=modes, 
                           selected_set_id='all',
                           selected_quiz_mode_id=selected_mode,
                           user_default_batch_size=user_default_batch_size
                           )

@quiz_learning_bp.route('/get_quiz_modes_partial/<int:set_id>', methods=['GET'])
@login_required
def get_quiz_modes_partial_by_id(set_id):
    """
    Trả về partial HTML chứa các chế độ học và số lượng câu hỏi tương ứng cho một bộ Quiz cụ thể.
    """
    selected_mode = request.args.get('selected_mode', None, type=str)
    user_default_batch_size = current_user.current_quiz_batch_size if current_user.current_quiz_batch_size is not None else QuizLearningConfig.QUIZ_DEFAULT_BATCH_SIZE

    modes = get_quiz_mode_counts(current_user.user_id, set_id)
    return render_template('_quiz_modes_selection.html', 
                           modes=modes, 
                           selected_set_id=str(set_id),
                           selected_quiz_mode_id=selected_mode,
                           user_default_batch_size=user_default_batch_size
                           )

@quiz_learning_bp.route('/start_quiz_session/all/<string:mode>/<int:batch_size>', methods=['GET'])
@login_required
def start_quiz_session_all(mode, batch_size):
    """
    Bắt đầu một phiên học Quiz cho TẤT CẢ các bộ câu hỏi với chế độ và kích thước nhóm câu đã chọn.
    """
    if QuizSessionManager.start_new_quiz_session('all', mode, batch_size):
        return redirect(url_for('learning.quiz_learning.quiz_session'))
    else:
        flash('Không có câu hỏi nào để bắt đầu phiên học với các lựa chọn này.', 'warning')
        return redirect(url_for('learning.quiz_learning.quiz_learning_dashboard'))

@quiz_learning_bp.route('/start_quiz_session/<int:set_id>/<string:mode>/<int:batch_size>', methods=['GET'])
@login_required
def start_quiz_session_by_id(set_id, mode, batch_size):
    """
    Bắt đầu một phiên học Quiz cho một bộ câu hỏi cụ thể với chế độ và kích thước nhóm câu đã chọn.
    """
    if QuizSessionManager.start_new_quiz_session(set_id, mode, batch_size):
        return redirect(url_for('learning.quiz_learning.quiz_session'))
    else:
        flash('Không có câu hỏi nào để bắt đầu phiên học với các lựa chọn này.', 'warning')
        return redirect(url_for('learning.quiz_learning.quiz_learning_dashboard'))

@quiz_learning_bp.route('/quiz_session')
@login_required
def quiz_session():
    """
    Hiển thị giao diện làm bài Quiz.
    """
    if 'quiz_session' not in session:
        flash('Không có phiên học Quiz nào đang hoạt động. Vui lòng chọn bộ Quiz để bắt đầu.', 'info')
        return redirect(url_for('learning.quiz_learning.quiz_learning_dashboard'))
    return render_template('quiz_session.html')

@quiz_learning_bp.route('/get_question_batch', methods=['GET'])
@login_required
def get_question_batch():
    """
    Trả về dữ liệu nhóm câu hỏi tiếp theo trong phiên học hiện tại.
    Dữ liệu câu hỏi đã bao gồm URL media tuyệt đối từ session_manager.
    """
    current_app.logger.debug("--- Bắt đầu get_question_batch ---")
    if 'quiz_session' not in session:
        current_app.logger.warning("Phiên học không hợp lệ hoặc đã kết thúc khi gọi get_question_batch.")
        return jsonify({'message': 'Phiên học không hợp lệ hoặc đã kết thúc.'}), 404

    session_manager = QuizSessionManager.from_dict(session['quiz_session'])
    batch_size = session_manager.batch_size
    try:
        question_batch = session_manager.get_next_batch(batch_size)
        session['quiz_session'] = session_manager.to_dict()
        
        if question_batch is None:
            session_manager.end_quiz_session()
            current_app.logger.info(f"Phiên học Quiz cho người dùng {current_user.user_id} đã kết thúc do hết câu hỏi.")
            current_app.logger.debug("--- Kết thúc get_question_batch (Hết câu hỏi) ---")
            return jsonify({'message': 'Bạn đã hoàn thành tất cả các câu hỏi trong phiên học này!'}), 404
        
        question_batch['session_correct_answers'] = session_manager.correct_answers
        question_batch['session_total_answered'] = session_manager.correct_answers + session_manager.incorrect_answers

        current_app.logger.debug("--- Kết thúc get_question_batch (Thành công) ---")
        return jsonify(question_batch)

    except Exception as e:
        current_app.logger.error(f"LỖI NGHIÊM TRỌNG khi lấy nhóm câu hỏi: {e}", exc_info=True)
        current_app.logger.debug("--- Kết thúc get_question_batch (LỖI) ---")
        return jsonify({'message': f'Lỗi khi tải câu hỏi: {str(e)}'}), 500

@quiz_learning_bp.route('/submit_answer_batch', methods=['POST'])
@login_required
def submit_answer_batch():
    """
    Nhận một danh sách các câu trả lời của người dùng, xử lý và cập nhật tiến độ.
    Đã THÊM: Cập nhật last_accessed của UserContainerState.
    """
    current_app.logger.debug("--- Bắt đầu submit_answer_batch ---")
    data = request.get_json()
    answers = data.get('answers')

    if not answers or not isinstance(answers, list):
        current_app.logger.warning("Dữ liệu đáp án không hợp lệ khi submit_answer_batch.")
        return jsonify({'error': 'Dữ liệu đáp án không hợp lệ.'}), 400

    if 'quiz_session' not in session:
        current_app.logger.warning("Không tìm thấy phiên học trong session khi submit_answer_batch.")
        return jsonify({'message': 'Phiên học không hợp lệ hoặc đã kết thúc.'}), 400

    session_manager = QuizSessionManager.from_dict(session['quiz_session'])
    if not session_manager:
        current_app.logger.warning("Không tìm thấy SessionManager khi submit_answer_batch.")
        return jsonify({'message': 'Phiên học không hợp lệ hoặc đã kết thúc.'}), 400
    
    # THÊM MỚI: Cập nhật last_accessed cho bộ quiz hiện tại
    quiz_set_id = session_manager.set_id
    if quiz_set_id != 'all':
        try:
            user_container_state = UserContainerState.query.filter_by(
                user_id=current_user.user_id,
                container_id=quiz_set_id
            ).first()
            if not user_container_state:
                user_container_state = UserContainerState(
                    user_id=current_user.user_id,
                    container_id=quiz_set_id,
                    is_archived=False,
                    is_favorite=False
                )
                db.session.add(user_container_state)
            
            # last_accessed sẽ tự động cập nhật nhờ onupdate=func.now() trong models.py
            db.session.commit()
            print(f">>> ROUTES: Đã cập nhật last_accessed cho bộ quiz {quiz_set_id} <<<")
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Lỗi khi cập nhật last_accessed cho bộ quiz {quiz_set_id}: {e}", exc_info=True)


    results = session_manager.process_answer_batch(answers)
    if 'error' in results:
        current_app.logger.error(f"Lỗi trong quá trình process_answer_batch: {results.get('error')}")
        return jsonify(results), 400
    
    session['quiz_session'] = session_manager.to_dict()

    response_data = {
        'results': results,
        'session_correct_answers': session_manager.correct_answers,
        'session_total_answered': session_manager.correct_answers + session_manager.incorrect_answers
    }

    current_app.logger.debug("--- Kết thúc submit_answer_batch (Thành công) ---")
    return jsonify(response_data)

@quiz_learning_bp.route('/end_session', methods=['POST'])
@login_required
def end_session():
    """
    Kết thúc phiên học Quiz hiện tại.
    """
    current_app.logger.debug("--- Bắt đầu end_session ---")
    result = QuizSessionManager.end_quiz_session()
    current_app.logger.info(f"Phiên học Quiz cho người dùng {current_user.user_id} đã kết thúc theo yêu cầu. Kết quả: {result.get('message')}")
    current_app.logger.debug("--- Kết thúc end_session ---")
    return jsonify(result)

@quiz_learning_bp.route('/save_quiz_settings', methods=['POST'])
@login_required
def save_quiz_settings():
    """
    Lưu cài đặt số câu hỏi mặc định trong một phiên học Quiz của người dùng.
    """
    data = request.get_json()
    batch_size = data.get('batch_size')

    if batch_size is None or not isinstance(batch_size, int) or batch_size <= 0:
        flash('Kích thước nhóm câu hỏi không hợp lệ.', 'danger')
        return jsonify({'success': False, 'message': 'Kích thước nhóm câu hỏi không hợp lệ.'}), 400

    try:
        user = User.query.get(current_user.user_id)
        if user:
            user.current_quiz_batch_size = batch_size
            db.session.commit()
            flash('Cài đặt số câu hỏi mặc định đã được lưu.', 'success')
            return jsonify({'success': True, 'message': 'Cài đặt số câu hỏi mặc định đã được lưu.'})
        else:
            flash('Không tìm thấy người dùng.', 'danger')
            return jsonify({'success': False, 'message': 'Không tìm thấy người dùng.'}), 404
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Lỗi khi lưu cài đặt quiz của người dùng: {e}", exc_info=True)
        flash('Đã xảy ra lỗi khi lưu cài đặt.', 'danger')
        return jsonify({'success': False, 'message': 'Đã xảy ra lỗi khi lưu cài đặt.'}), 500

@quiz_learning_bp.route('/get_quiz_sets_partial', methods=['GET'])
@login_required
def get_quiz_sets_partial():
    """
    Trả về partial HTML chứa danh sách các bộ Quiz, có hỗ trợ tìm kiếm và phân trang.
    """
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
        return render_template('_quiz_sets_selection.html', **template_vars)

    except Exception as e:
        print(f">>> PYTHON LỖI: Đã xảy ra lỗi trong get_quiz_sets_partial: {e}")
        print(traceback.format_exc())
        current_app.logger.error(f"LỖI NGHIÊM TRỌNG khi tải danh sách bộ Quiz qua AJAX: {e}", exc_info=True)
        current_app.logger.debug("<<< Kết thúc thực thi get_quiz_sets_partial (LỖI) >>>")
        return '<p class="text-red-500 text-center py-4">Đã xảy ra lỗi khi tải danh sách bộ câu hỏi. Vui lòng thử lại.</p>', 500


@quiz_learning_bp.route('/toggle_archive/<int:set_id>', methods=['POST'])
@login_required
def toggle_archive(set_id):
    """
    Xử lý yêu cầu archive hoặc unarchive một bộ quiz.
    """
    try:
        # Tìm bản ghi UserContainerState hiện có
        user_container_state = UserContainerState.query.filter_by(
            user_id=current_user.user_id,
            container_id=set_id
        ).first()

        is_currently_archived = False
        if user_container_state:
            # Nếu bản ghi đã tồn tại, cập nhật trạng thái archive
            user_container_state.is_archived = not user_container_state.is_archived
            is_currently_archived = user_container_state.is_archived
        else:
            # Nếu bản ghi chưa tồn tại, tạo bản ghi mới và archive nó
            user_container_state = UserContainerState(
                user_id=current_user.user_id,
                container_id=set_id,
                is_archived=True,
                is_favorite=False # Mặc định là False
            )
            db.session.add(user_container_state)
            is_currently_archived = True

        db.session.commit()
        
        status_text = "đã được lưu trữ." if is_currently_archived else "đã được bỏ lưu trữ."
        flash(f'Bộ quiz "{set_id}" {status_text}', 'success')

        return jsonify({'success': True, 'is_archived': is_currently_archived, 'message': f'Bộ quiz {status_text}'})

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Lỗi khi toggle archive cho bộ quiz {set_id}: {e}", exc_info=True)
        return jsonify({'success': False, 'message': 'Đã xảy ra lỗi khi thay đổi trạng thái lưu trữ.'}), 500
