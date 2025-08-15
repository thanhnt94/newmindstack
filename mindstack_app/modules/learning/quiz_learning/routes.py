# File: newmindstack/mindstack_app/modules/learning/quiz_learning/routes.py
# Phiên bản: 1.28
# Mục đích: Định nghĩa các routes và logic cho module học Quiz.
# ĐÃ SỬA: Tách rõ ràng các routes get_quiz_modes_partial và start_quiz_session thành _all và _by_id để tránh BuildError.
# ĐÃ SỬA: Đơn giản hóa logic lọc 'doing' và 'explore' trong get_quiz_sets_partial để đảm bảo tải nội dung ban đầu.
# ĐÃ SỬA: Thêm xử lý lỗi vào các hàm để chẩn đoán tốt hơn.

from flask import Blueprint, render_template, request, jsonify, abort, current_app
from flask_login import login_required, current_user
from sqlalchemy import or_
from ....models import db, LearningContainer, LearningItem, UserProgress, ContainerContributor
from ....utils.pagination import get_pagination_data
from ....utils.search import apply_search_filter
from sqlalchemy.sql import func # Import func để sử dụng func.now()

quiz_learning_bp = Blueprint('quiz_learning', __name__,
                             template_folder='templates') # Template folder của riêng quiz_learning

@quiz_learning_bp.route('/quiz_learning_dashboard')
@login_required
def quiz_learning_dashboard():
    """
    Hiển thị trang chính để chọn bộ câu hỏi và chế độ học Quiz.
    Sẽ tải trực tiếp danh sách bộ Quiz cho lần hiển thị đầu tiên.
    """
    page = request.args.get('page', 1, type=int)
    search_query = request.args.get('q', '', type=str)
    search_field = request.args.get('search_field', 'all', type=str)
    current_filter = request.args.get('filter', 'doing', type=str) # Lấy filter từ request
    
    try:
        # Bắt đầu với truy vấn cơ sở cho các bộ Quiz
        # Lấy tất cả các bộ mà người dùng có quyền truy cập (tạo, đóng góp, công khai)
        base_query_accessible = LearningContainer.query.filter_by(container_type='QUIZ_SET')

        if current_user.user_role != 'admin':
            user_id = current_user.user_id
            
            created_sets_query = LearningContainer.query.filter_by(
                creator_user_id=user_id,
                container_type='QUIZ_SET'
            )
            contributed_sets_query = LearningContainer.query.join(ContainerContributor).filter(
                ContainerContributor.user_id == user_id,
                ContainerContributor.permission_level == 'editor',
                LearningContainer.container_type == 'QUIZ_SET'
            )
            public_sets_query = LearningContainer.query.filter_by(
                is_public=True,
                container_type='QUIZ_SET'
            )
            
            base_query_accessible = created_sets_query.union(contributed_sets_query).union(public_sets_query)
        else:
            base_query_accessible = LearningContainer.query.filter_by(container_type='QUIZ_SET')

        # --- ĐƠN GIẢN HÓA LOGIC LỌC 'DOING' VÀ 'EXPLORE' TẠM THỜI ---
        # Để đảm bảo tải được dữ liệu trước, chúng ta sẽ bỏ qua logic lọc phức tạp cho 'doing' và 'explore'
        # và chỉ trả về tất cả các bộ mà người dùng có thể truy cập.
        # Sau khi xác nhận tải được, chúng ta sẽ tinh chỉnh lại.
        final_query = base_query_accessible # Trả về tất cả các bộ truy cập được

        # Ánh xạ các trường có thể tìm kiếm cho Quiz Sets
        quiz_set_search_options = {
            'title': LearningContainer.title,
            'description': LearningContainer.description, 
            'tags': LearningContainer.tags
        }
        
        final_query = apply_search_filter(final_query, search_query, quiz_set_search_options, search_field)

        # Lấy dữ liệu phân trang
        pagination = get_pagination_data(final_query.order_by(LearningContainer.created_at.desc()), page)
        quiz_sets = pagination.items

        # Đếm số lượng câu hỏi trong mỗi bộ và tiến độ học của người dùng
        for set_item in quiz_sets:
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

        template_vars = {
            'quiz_sets': quiz_sets, 
            'pagination': pagination, 
            'search_query': search_query,
            'search_field': search_field,
            'search_options': quiz_set_search_options,
            'current_filter': current_filter
        }
        return render_template('quiz_learning_dashboard.html', **template_vars)
    except Exception as e:
        current_app.logger.error(f"Lỗi khi tải danh sách bộ Quiz cho dashboard: {e}", exc_info=True)
        return render_template('quiz_learning_dashboard.html', 
                               quiz_sets=[],
                               pagination=None,
                               search_query='',
                               search_field='all',
                               search_options={},
                               current_filter='doing',
                               error_message="Không thể tải danh sách bộ câu hỏi. Vui lòng thử lại hoặc liên hệ quản trị viên.")


# Route cho trường hợp set_id là 'all'
@quiz_learning_bp.route('/get_quiz_modes_partial/all', methods=['GET'])
@login_required
def get_quiz_modes_partial_all(): # Endpoint: learning.quiz_learning.get_quiz_modes_partial_all
    """
    Trả về partial HTML chứa các chế độ học và số lượng câu hỏi tương ứng cho TẤT CẢ các bộ Quiz.
    """
    return _calculate_and_render_quiz_modes('all')

# Route cho trường hợp set_id là số nguyên
@quiz_learning_bp.route('/get_quiz_modes_partial/<int:set_id>', methods=['GET'])
@login_required
def get_quiz_modes_partial_by_id(set_id): # Endpoint: learning.quiz_learning.get_quiz_modes_partial_by_id
    """
    Trả về partial HTML chứa các chế độ học và số lượng câu hỏi tương ứng cho một bộ Quiz cụ thể.
    """
    return _calculate_and_render_quiz_modes(set_id)

# Route cho việc bắt đầu phiên học với 'all' sets
@quiz_learning_bp.route('/start_quiz_session/all/<string:mode>', methods=['GET'])
@login_required
def start_quiz_session_all(mode): # Endpoint: learning.quiz_learning.start_quiz_session_all
    """
    Bắt đầu một phiên học Quiz cho TẤT CẢ các bộ câu hỏi với chế độ đã chọn.
    """
    return f"Bắt đầu học Quiz: Bộ ALL, Chế độ {mode}" # Tạm thời

# Route cho việc bắt đầu phiên học với một bộ cụ thể
@quiz_learning_bp.route('/start_quiz_session/<int:set_id>/<string:mode>', methods=['GET'])
@login_required
def start_quiz_session_by_id(set_id, mode): # Endpoint: learning.quiz_learning.start_quiz_session_by_id
    """
    Bắt đầu một phiên học Quiz cho một bộ câu hỏi cụ thể với chế độ đã chọn.
    """
    return f"Bắt đầu học Quiz: Bộ {set_id}, Chế độ {mode}" # Tạm thời


@quiz_learning_bp.route('/get_quiz_sets_partial', methods=['GET'])
@login_required
def get_quiz_sets_partial():
    """
    Trả về partial HTML chứa danh sách các bộ Quiz, có hỗ trợ tìm kiếm và phân trang.
    Sử dụng AJAX để tải nội dung này.
    """
    page = request.args.get('page', 1, type=int)
    search_query = request.args.get('q', '', type=str)
    search_field = request.args.get('search_field', 'all', type=str)
    current_filter = request.args.get('filter', 'doing', type=str)
    
    try:
        base_query_accessible = LearningContainer.query.filter_by(container_type='QUIZ_SET')

        if current_user.user_role != 'admin':
            user_id = current_user.user_id
            created_sets_query = LearningContainer.query.filter_by(
                creator_user_id=user_id,
                container_type='QUIZ_SET'
            )
            contributed_sets_query = LearningContainer.query.join(ContainerContributor).filter(
                ContainerContributor.user_id == user_id,
                ContainerContributor.permission_level == 'editor',
                LearningContainer.container_type == 'QUIZ_SET'
            )
            public_sets_query = LearningContainer.query.filter_by(
                is_public=True,
                container_type='QUIZ_SET'
            )
            base_query_accessible = created_sets_query.union(contributed_sets_query).union(public_sets_query)
        else:
            base_query_accessible = LearningContainer.query.filter_by(container_type='QUIZ_SET')

        final_query = base_query_accessible

        if current_filter == 'doing':
            sets_with_progress_ids = db.session.query(LearningItem.container_id).join(UserProgress).filter(
                UserProgress.user_id == current_user.user_id,
                LearningItem.item_type == 'QUIZ_MCQ'
            ).distinct().subquery()
            final_query = final_query.filter(
                LearningContainer.container_id.in_(sets_with_progress_ids)
            )
        elif current_filter == 'explore':
            pass
        
        quiz_set_search_options = {
            'title': LearningContainer.title,
            'description': LearningContainer.description, 
            'tags': LearningContainer.tags
        }
        
        final_query = apply_search_filter(final_query, search_query, quiz_set_search_options, search_field)

        # Lấy tất cả các bộ Quiz mà không phân trang
        quiz_sets = final_query.order_by(LearningContainer.created_at.desc()).all()

        for set_item in quiz_sets:
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

        # Không truyền pagination object vào template nữa
        return render_template('_quiz_sets_selection.html', 
                               quiz_sets=quiz_sets, 
                               search_query=search_query,
                               search_field=search_field,
                               search_options=quiz_set_search_options)
    except Exception as e:
        current_app.logger.error(f"Lỗi khi tải danh sách bộ Quiz qua AJAX: {e}", exc_info=True)
        return '<p class="text-red-500 text-center py-4">Đã xảy ra lỗi khi tải danh sách bộ câu hỏi. Vui lòng thử lại.</p>', 500


def _calculate_and_render_quiz_modes(set_identifier):
    total_items = 0
    new_items_count = 0
    due_items_count = 0
    hard_items_count = 0

    accessible_container_query = LearningContainer.query.filter_by(container_type='QUIZ_SET')
    if current_user.user_role != 'admin':
        user_id = current_user.user_id
        created_sets_query = LearningContainer.query.filter_by(
            creator_user_id=user_id,
            container_type='QUIZ_SET'
        )
        contributed_sets_query = LearningContainer.query.join(ContainerContributor).filter(
            ContainerContributor.user_id == user_id,
            ContainerContributor.permission_level == 'editor',
            LearningContainer.container_type == 'QUIZ_SET'
        )
        public_sets_query = LearningContainer.query.filter_by(
            is_public=True,
            container_type='QUIZ_SET'
        )
        accessible_container_query = created_sets_query.union(contributed_sets_query).union(public_sets_query)
    
    all_accessible_quiz_set_ids = [s.container_id for s in accessible_container_query.all()]

    items_query = LearningItem.query.filter(LearningItem.item_type == 'QUIZ_MCQ')
    if set_identifier == 'all':
        if not all_accessible_quiz_set_ids:
            items_query = items_query.filter(False)
        else:
            items_query = items_query.filter(LearningItem.container_id.in_(all_accessible_quiz_set_ids))
    else:
        try:
            set_id_int = int(set_identifier)
            items_query = items_query.filter_by(container_id=set_id_int)
        except ValueError:
            abort(404)

    total_items = items_query.count()

    new_items_count = items_query.outerjoin(UserProgress, 
        (LearningItem.item_id == UserProgress.item_id) & (UserProgress.user_id == current_user.user_id)
    ).filter(
        UserProgress.item_id == None
    ).count()

    due_items_count = items_query.join(UserProgress).filter(
        UserProgress.user_id == current_user.user_id,
        UserProgress.due_time <= func.now()
    ).count()

    hard_items_count = items_query.join(UserProgress).filter(
        UserProgress.user_id == current_user.user_id,
        UserProgress.memory_score < 0.5
    ).count()

    modes = [
        {'id': 'sequential', 'name': 'Làm mới tuần tự', 'count': total_items},
        {'id': 'new_only', 'name': 'Chỉ làm mới', 'count': new_items_count},
        {'id': 'due_only', 'name': 'Ôn tập tới hạn', 'count': due_items_count},
        {'id': 'random', 'name': 'Làm ngẫu nhiên', 'count': total_items},
        {'id': 'hard_only', 'name': 'Ôn tập từ khó', 'count': hard_items_count},
        {'id': 'autoplay', 'name': 'Auto Play', 'count': total_items}
    ]
    return render_template('_quiz_modes_selection.html', modes=modes, selected_set_id=str(set_identifier))
