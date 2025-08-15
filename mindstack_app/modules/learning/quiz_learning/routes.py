# File: newmindstack/mindstack_app/modules/learning/quiz_learning/routes.py
# Phiên bản: 1.44
# Mục đích: Định nghĩa các routes và logic cho module học Quiz.
# ĐÃ SỬA: Hỗ trợ làm bài theo nhóm câu hỏi.
# ĐÃ SỬA: Endpoint get_question đổi thành get_question_batch.
# ĐÃ SỬA: Endpoint submit_answer đổi thành submit_answer_batch.
# ĐÃ SỬA: Đổi tên tham số session_size thành batch_size trong các route bắt đầu phiên học.
# ĐÃ SỬA: Truyền batch_size vào QuizSessionManager.start_new_quiz_session.

from flask import Blueprint, render_template, request, jsonify, abort, current_app, redirect, url_for, flash
from flask_login import login_required, current_user
from sqlalchemy import or_
from ....models import db, LearningContainer, LearningItem, UserProgress, ContainerContributor
from ....utils.pagination import get_pagination_data
from ....utils.search import apply_search_filter
from sqlalchemy.sql import func
import traceback
from .algorithms import get_new_only_items, get_reviewed_items, get_hard_items
from .session_manager import QuizSessionManager

quiz_learning_bp = Blueprint('quiz_learning', __name__,
                             template_folder='templates')

DEFAULT_ITEMS_PER_PAGE = 12 

def _calculate_and_render_quiz_modes(set_identifier, selected_quiz_mode_id=None):
    """
    Tính toán và render các chế độ học Quiz cùng với số lượng câu hỏi tương ứng.
    """
    # None để lấy tất cả các câu phù hợp, không giới hạn bởi session_size ở đây
    new_items_count = len(get_new_only_items(current_user.user_id, set_identifier, None))
    reviewed_items_count = len(get_reviewed_items(current_user.user_id, set_identifier, None))
    hard_items_count = len(get_hard_items(current_user.user_id, set_identifier, None))

    modes = [
        {'id': 'new_only', 'name': 'Chỉ làm mới', 'count': new_items_count},
        {'id': 'due_only', 'name': 'Ôn tập câu đã làm', 'count': reviewed_items_count},
        {'id': 'hard_only', 'name': 'Ôn tập câu khó', 'count': hard_items_count},
    ]
    return render_template('_quiz_modes_selection.html', 
                           modes=modes, 
                           selected_set_id=str(set_identifier),
                           selected_quiz_mode_id=selected_quiz_mode_id
                           )

@quiz_learning_bp.route('/quiz_learning_dashboard')
@login_required
def quiz_learning_dashboard():
    """
    Hiển thị trang chính để chọn bộ câu hỏi và chế độ học Quiz.
    """
    search_query = request.args.get('q', '', type=str)
    search_field = request.args.get('search_field', 'all', type=str)
    current_filter = request.args.get('filter', 'doing', type=str)

    quiz_set_search_options = {
        'title': 'Tiêu đề', 'description': 'Mô tả', 'tags': 'Thẻ'
    }
    
    template_vars = {
        'search_query': search_query, 'search_field': search_field,
        'quiz_set_search_options': quiz_set_search_options, 'current_filter': current_filter
    }
    return render_template('quiz_learning_dashboard.html', **template_vars)

@quiz_learning_bp.route('/get_quiz_modes_partial/all', methods=['GET'])
@login_required
def get_quiz_modes_partial_all():
    """
    Trả về partial HTML chứa các chế độ học và số lượng câu hỏi tương ứng cho TẤT CẢ các bộ Quiz.
    """
    selected_mode = request.args.get('selected_mode', None, type=str)
    return _calculate_and_render_quiz_modes('all', selected_quiz_mode_id=selected_mode)

@quiz_learning_bp.route('/get_quiz_modes_partial/<int:set_id>', methods=['GET'])
@login_required
def get_quiz_modes_partial_by_id(set_id):
    """
    Trả về partial HTML chứa các chế độ học và số lượng câu hỏi tương ứng cho một bộ Quiz cụ thể.
    """
    selected_mode = request.args.get('selected_mode', None, type=str)
    return _calculate_and_render_quiz_modes(set_id, selected_quiz_mode_id=selected_mode)

# Đổi tên tham số session_size thành batch_size
@quiz_learning_bp.route('/start_quiz_session/all/<string:mode>/<int:batch_size>', methods=['GET'])
@login_required
def start_quiz_session_all(mode, batch_size):
    """
    Bắt đầu một phiên học Quiz cho TẤT CẢ các bộ câu hỏi với chế độ và kích thước nhóm câu đã chọn.
    """
    if QuizSessionManager.start_new_quiz_session('all', mode, batch_size): # Truyền batch_size
        return redirect(url_for('learning.quiz_learning.quiz_session'))
    else:
        flash('Không có câu hỏi nào để bắt đầu phiên học với các lựa chọn này.', 'warning')
        return redirect(url_for('learning.quiz_learning.quiz_learning_dashboard'))

# Đổi tên tham số session_size thành batch_size
@quiz_learning_bp.route('/start_quiz_session/<int:set_id>/<string:mode>/<int:batch_size>', methods=['GET'])
@login_required
def start_quiz_session_by_id(set_id, mode, batch_size):
    """
    Bắt đầu một phiên học Quiz cho một bộ câu hỏi cụ thể với chế độ và kích thước nhóm câu đã chọn.
    """
    if QuizSessionManager.start_new_quiz_session(set_id, mode, batch_size): # Truyền batch_size
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
    if not QuizSessionManager.get_session_status():
        flash('Không có phiên học Quiz nào đang hoạt động. Vui lòng chọn bộ Quiz để bắt đầu.', 'info')
        return redirect(url_for('learning.quiz_learning.quiz_learning_dashboard'))
    return render_template('quiz_session.html')

@quiz_learning_bp.route('/get_question_batch', methods=['GET'])
@login_required
def get_question_batch():
    """
    Trả về dữ liệu nhóm câu hỏi tiếp theo trong phiên học hiện tại.
    """
    batch_data = QuizSessionManager.get_current_question_batch()
    if batch_data:
        return jsonify(batch_data)
    else:
        return jsonify({'message': 'Phiên học đã kết thúc hoặc không có câu hỏi nào còn lại.'}), 404

@quiz_learning_bp.route('/submit_answer_batch', methods=['POST'])
@login_required
def submit_answer_batch():
    """
    Nhận một danh sách các câu trả lời của người dùng, xử lý và cập nhật tiến độ.
    """
    data = request.get_json()
    answers = data.get('answers')

    if not answers or not isinstance(answers, list):
        return jsonify({'error': 'Dữ liệu đáp án không hợp lệ.'}), 400

    results = QuizSessionManager.process_answer_batch(answers)
    if 'error' in results:
        return jsonify(results), 400
    return jsonify(results)

@quiz_learning_bp.route('/end_session', methods=['POST'])
@login_required
def end_session():
    """
    Kết thúc phiên học Quiz hiện tại.
    """
    result = QuizSessionManager.end_quiz_session()
    return jsonify(result)

@quiz_learning_bp.route('/get_quiz_sets_partial', methods=['GET'])
@login_required
def get_quiz_sets_partial():
    """
    Trả về partial HTML chứa danh sách các bộ Quiz, có hỗ trợ tìm kiếm và phân trang.
    """
    current_app.logger.debug(">>> Bắt đầu thực thi get_quiz_sets_partial <<<")
    print(">>> PYTHON: Hàm get_quiz_sets_partial đã được gọi! <<<")
    page = request.args.get('page', 1, type=int)
    search_query = request.args.get('q', '', type=str)
    search_field = request.args.get('search_field', 'all', type=str)
    current_filter = request.args.get('filter', 'doing', type=str)

    try:
        base_query = LearningContainer.query.filter_by(container_type='QUIZ_SET')
        current_app.logger.debug(f"Truy vấn cơ sở ban đầu: {base_query}")

        access_conditions = []
        if current_user.user_role != 'admin':
            user_id = current_user.user_id
            access_conditions.append(LearningContainer.creator_user_id == user_id)
            access_conditions.append(LearningContainer.is_public == True)
            
            contributed_sets_ids = db.session.query(ContainerContributor.container_id).filter(
                ContainerContributor.user_id == user_id,
                ContainerContributor.permission_level == 'editor'
            ).all()
            
            if contributed_sets_ids:
                access_conditions.append(LearningContainer.container_id.in_([c.container_id for c in contributed_sets_ids]))

            base_query = base_query.filter(or_(*access_conditions))
            current_app.logger.debug(f"Truy vấn cơ sở sau lọc quyền truy cập cho người dùng {user_id}: {base_query}")
        else:
            current_app.logger.debug("Người dùng là Admin, không áp dụng thêm bộ lọc quyền truy cập.")

        search_field_map = {
            'title': LearningContainer.title, 'description': LearningContainer.description, 'tags': LearningContainer.tags
        }
        
        filtered_query = apply_search_filter(base_query, search_query, search_field_map, search_field)
        current_app.logger.debug(f"Truy vấn sau bộ lọc tìm kiếm: {filtered_query}")

        user_progressed_container_ids_list = db.session.query(LearningItem.container_id).join(UserProgress).filter(
            UserProgress.user_id == current_user.user_id,
            LearningItem.item_type == 'QUIZ_MCQ'
        ).distinct().all()
        
        progressed_ids = [c.container_id for c in user_progressed_container_ids_list]
        current_app.logger.debug(f"ID bộ quiz đã có tiến độ của người dùng ({current_user.user_id}): {progressed_ids}")

        final_query = filtered_query

        if current_filter == 'doing':
            if progressed_ids:
                final_query = final_query.filter(
                    LearningContainer.container_id.in_(progressed_ids)
                )
            else:
                final_query = final_query.filter(False)
            current_app.logger.debug(f"Truy vấn cuối cùng cho bộ lọc 'Đang làm': {final_query}")

        elif current_filter == 'explore':
            final_query = final_query.filter(LearningContainer.is_public == True)
            
            if progressed_ids:
                final_query = final_query.filter(
                    ~LearningContainer.container_id.in_(progressed_ids)
                )
            current_app.logger.debug(f"Truy vấn cuối cùng cho bộ lọc 'Khám phá': {final_query}")
        else:
            current_app.logger.debug(f"Bộ lọc không hợp lệ '{current_filter}', trả về tất cả các bộ có thể truy cập và tìm kiếm được.")

        pagination = get_pagination_data(final_query.order_by(LearningContainer.created_at.desc()), page, per_page=DEFAULT_ITEMS_PER_PAGE)
        quiz_sets = pagination.items
        current_app.logger.debug(f"Số lượng bộ quiz được truy xuất: {len(quiz_sets)}")

        for set_item in quiz_sets:
            if not hasattr(set_item, 'creator') or set_item.creator is None:
                set_item.creator = type('obj', (object,), {'username' : 'Người dùng không xác định'})()

            total_items = db.session.query(LearningItem).filter_by(
                container_id=set_item.container_id,
                item_type='QUIZ_MCQ'
            ).count()
            
            learned_items = db.session.query(UserProgress).filter(
                UserProgress.user_id == current_user.user_id,
                UserProgress.item_id.in_(
                    db.session.query(LearningItem.item_id).filter(
                        LearningItem.container_id == set_item.container_id,
                        LearningItem.item_type == 'QUIZ_MCQ'
                    )
                )
            ).count()
            set_item.item_count = f"{learned_items} / {total_items}"
            set_item.total_items = total_items
            current_app.logger.debug(f"Bộ {set_item.container_id}: {set_item.item_count} câu ({set_item.title})")

        current_app.logger.debug("<<< Kết thúc thực thi get_quiz_sets_partial (Thành công) >>>")
        return render_template('_quiz_sets_selection.html', 
                               quiz_sets=quiz_sets, 
                               pagination=pagination,
                               search_query=search_query,
                               search_field=search_field,
                               search_options=search_field_map,
                               current_filter=current_filter)

    except Exception as e:
        print(f">>> PYTHON LỖI: Đã xảy ra lỗi trong get_quiz_sets_partial: {e}")
        print(traceback.format_exc())
        current_app.logger.error(f"LỖI NGHIÊM TRỌNG khi tải danh sách bộ Quiz qua AJAX: {e}", exc_info=True)
        current_app.logger.debug("<<< Kết thúc thực thi get_quiz_sets_partial (LỖI) >>>")
        return '<p class="text-red-500 text-center py-4">Đã xảy ra lỗi khi tải danh sách bộ câu hỏi. Vui lòng thử lại.</p>', 500

