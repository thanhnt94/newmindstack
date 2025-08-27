# File: mindstack_app/modules/learning/quiz_learning/algorithms.py
# Phiên bản: 1.14
# Mục đích: Chứa logic thuật toán để lựa chọn và sắp xếp các câu hỏi Quiz cho các chế độ học khác nhau.
# ĐÃ SỬA: Sửa hàm get_filtered_quiz_sets để sắp xếp các bộ "Đang làm" theo last_accessed.
# ĐÃ SỬA: Đơn giản hóa logic lọc cho tab "Khám phá" để chỉ hiển thị các bộ chưa từng được tương tác.

from ....models import db, LearningItem, UserProgress, LearningContainer, ContainerContributor, UserContainerState
from flask_login import current_user
from sqlalchemy import func, and_, not_, or_
from flask import current_app
from ....utils.pagination import get_pagination_data
from ....utils.search import apply_search_filter
from .config import QuizLearningConfig


def _get_base_items_query(user_id, container_id):
    """
    Tạo truy vấn cơ sở cho LearningItem dựa trên container_id hoặc tất cả các container có thể truy cập.
    Hàm này sẽ không lọc theo trạng thái archive. Việc lọc archive sẽ được xử lý ở các hàm gọi nó.

    Args:
        user_id (int): ID của người dùng hiện tại.
        container_id (int/str): ID của LearningContainer hoặc 'all' nếu muốn lấy tất cả các bộ.

    Returns:
        sqlalchemy.orm.query.Query: Đối tượng truy vấn LearningItem cơ sở.
    """
    print(f">>> ALGORITHMS: Bắt đầu _get_base_items_query cho user_id={user_id}, container_id={container_id} <<<")
    items_query = LearningItem.query.filter(LearningItem.item_type == 'QUIZ_MCQ')

    if container_id == 'all':
        access_conditions = []
        if current_user.user_role != 'admin':
            access_conditions.append(LearningContainer.creator_user_id == user_id)
            access_conditions.append(LearningContainer.is_public == True)
            
            contributed_ids_subquery = db.session.query(ContainerContributor.container_id).filter(
                ContainerContributor.user_id == user_id,
                ContainerContributor.permission_level == 'editor'
            ).subquery()
            access_conditions.append(LearningContainer.container_id.in_(contributed_ids_subquery))

            accessible_containers = LearningContainer.query.filter(
                LearningContainer.container_type == 'QUIZ_SET',
                or_(*access_conditions)
            ).all()
            all_accessible_quiz_set_ids = [c.container_id for c in accessible_containers]
            print(f">>> ALGORITHMS: 'all' mode (User), Accessible Quiz Set IDs: {all_accessible_quiz_set_ids} <<<")
        else:
            all_accessible_quiz_set_ids = [s.container_id for s in LearningContainer.query.filter_by(container_type='QUIZ_SET').all()]
            print(f">>> ALGORITHMS: 'all' mode (Admin), All Quiz Set IDs: {all_accessible_quiz_set_ids} <<<")
        
        if not all_accessible_quiz_set_ids:
            items_query = items_query.filter(False)
            print(">>> ALGORITHMS: Không có bộ quiz nào có thể truy cập, truy vấn trả về rỗng. <<<")
        else:
            items_query = items_query.filter(LearningItem.container_id.in_(all_accessible_quiz_set_ids))
            print(f">>> ALGORITHMS: 'all' mode, items_query after filtering by accessible sets: {items_query} <<<")
    else:
        try:
            set_id_int = int(container_id)
            items_query = items_query.filter_by(container_id=set_id_int)
            print(f">>> ALGORITHMS: Cụ thể container_id={set_id_int}, items_query: {items_query} <<<")
        except ValueError:
            items_query = items_query.filter(False)
            print(f">>> ALGORITHMS: container_id '{container_id}' không hợp lệ, truy vấn trả về rỗng. <<<")
    
    print(f">>> ALGORITHMS: Kết thúc _get_base_items_query. Query: {items_query} <<<")
    return items_query

def get_new_only_items(user_id, container_id, session_size):
    """
    Lấy danh sách các câu hỏi chỉ làm mới (chưa có tiến độ) cho một phiên học.
    Hàm này sẽ loại trừ các bộ quiz đã được archive.
    """
    print(f">>> ALGORITHMS: Bắt đầu get_new_only_items cho user_id={user_id}, container_id={container_id}, session_size={session_size} <<<")
    base_items_query = _get_base_items_query(user_id, container_id)
    
    # Lọc các item chưa có bản ghi UserProgress cho người dùng hiện tại
    new_items_query = base_items_query.outerjoin(UserProgress, 
        and_(UserProgress.item_id == LearningItem.item_id, UserProgress.user_id == user_id)
    ).filter(
        UserProgress.item_id == None
    )

    # THÊM MỚI: Loại trừ các bộ quiz đã được archive
    new_items_query = new_items_query.outerjoin(UserContainerState,
        and_(UserContainerState.container_id == LearningItem.container_id, UserContainerState.user_id == user_id)
    ).filter(
        or_(UserContainerState.is_archived == False, UserContainerState.is_archived == None)
    )
    
    print(f">>> ALGORITHMS: new_items_query (chỉ làm mới): {new_items_query} <<<")
    
    if session_size is None or session_size == 999999:
        items = new_items_query.all()
    else:
        items = new_items_query.order_by(func.random()).limit(session_size).all()
    
    print(f">>> ALGORITHMS: get_new_only_items tìm thấy {len(items)} câu hỏi. <<<")
    return items

def get_reviewed_items(user_id, container_id, session_size):
    """
    Lấy danh sách các câu hỏi đã làm (có tiến độ) cho một phiên học, không bao gồm câu mới.
    Hàm này sẽ loại trừ các bộ quiz đã được archive.
    """
    print(f">>> ALGORITHMS: Bắt đầu get_reviewed_items cho user_id={user_id}, container_id={container_id}, session_size={session_size} <<<")
    base_items_query = _get_base_items_query(user_id, container_id)
    
    reviewed_items_query = base_items_query.join(UserProgress).filter(
        UserProgress.user_id == user_id,
        UserProgress.first_seen_timestamp != None
    )
    
    # THÊM MỚI: Loại trừ các bộ quiz đã được archive
    reviewed_items_query = reviewed_items_query.outerjoin(UserContainerState,
        and_(UserContainerState.container_id == LearningItem.container_id, UserContainerState.user_id == user_id)
    ).filter(
        or_(UserContainerState.is_archived == False, UserContainerState.is_archived == None)
    )

    print(f">>> ALGORITHMS: reviewed_items_query (đã làm): {reviewed_items_query} <<<")
    
    if session_size is None or session_size == 999999:
        items = reviewed_items_query.all()
    else:
        items = reviewed_items_query.order_by(func.random()).limit(session_size).all()
    
    print(f">>> ALGORITHMS: get_reviewed_items tìm thấy {len(items)} câu hỏi. <<<")
    return items

def get_hard_items(user_id, container_id, session_size):
    """
    Lấy danh sách các câu hỏi khó cho một phiên học.
    Hàm này sẽ loại trừ các bộ quiz đã được archive.
    """
    print(f">>> ALGORITHMS: Bắt đầu get_hard_items cho user_id={user_id}, container_id={container_id}, session_size={session_size} <<<")
    base_items_query = _get_base_items_query(user_id, container_id)

    hard_items_query = base_items_query.join(UserProgress).filter(
        UserProgress.user_id == user_id,
        (UserProgress.times_correct + UserProgress.times_incorrect) >= 10,
        (UserProgress.times_correct / (UserProgress.times_correct + UserProgress.times_incorrect)) < 0.5
    )
    
    # THÊM MỚI: Loại trừ các bộ quiz đã được archive
    hard_items_query = hard_items_query.outerjoin(UserContainerState,
        and_(UserContainerState.container_id == LearningItem.container_id, UserContainerState.user_id == user_id)
    ).filter(
        or_(UserContainerState.is_archived == False, UserContainerState.is_archived == None)
    )

    print(f">>> ALGORITHMS: hard_items_query (câu khó): {hard_items_query} <<<")
    
    if session_size is None or session_size == 999999:
        items = hard_items_query.all()
    else:
        items = hard_items_query.order_by(func.random()).limit(session_size).all()
    
    print(f">>> ALGORITHMS: get_hard_items tìm thấy {len(items)} câu hỏi. <<<")
    return items

def get_filtered_quiz_sets(user_id, search_query, search_field, current_filter, page, per_page=QuizLearningConfig.DEFAULT_ITEMS_PER_PAGE):
    """
    Lấy danh sách các bộ Quiz đã được lọc và phân trang dựa trên các tiêu chí.
    Bây giờ có thể lọc theo trạng thái archive và sắp xếp theo last_accessed.
    """
    print(f">>> ALGORITHMS: Bắt đầu get_filtered_quiz_sets cho user_id={user_id}, filter={current_filter} <<<")

    base_query = LearningContainer.query.filter_by(container_type='QUIZ_SET')
    
    # Lọc quyền truy cập
    access_conditions = []
    if current_user.user_role != 'admin':
        access_conditions.append(LearningContainer.creator_user_id == user_id)
        access_conditions.append(LearningContainer.is_public == True)
        
        contributed_sets_ids = db.session.query(ContainerContributor.container_id).filter(
            ContainerContributor.user_id == user_id,
            ContainerContributor.permission_level == 'editor'
        ).all()
        
        if contributed_sets_ids:
            access_conditions.append(LearningContainer.container_id.in_([c.container_id for c in contributed_sets_ids]))

        base_query = base_query.filter(or_(*access_conditions))
    
    # Ánh xạ các trường có thể tìm kiếm
    search_field_map = {
        'title': LearningContainer.title,
        'description': LearningContainer.description,
        'tags': LearningContainer.tags
    }
    
    # Áp dụng bộ lọc tìm kiếm
    filtered_query = apply_search_filter(base_query, search_query, search_field_map, search_field)

    # THAY ĐỔI LỚN: Áp dụng bộ lọc archive và sắp xếp theo last_accessed
    # SỬA: Sẽ sử dụng truy vấn con để loại trừ các bộ đã có bản ghi trong UserContainerState
    user_interacted_ids_subquery = db.session.query(UserContainerState.container_id).filter(
        UserContainerState.user_id == user_id
    ).subquery()
    
    if current_filter == 'archive':
        final_query = filtered_query.join(UserContainerState,
            and_(UserContainerState.container_id == LearningContainer.container_id, UserContainerState.user_id == user_id)
        ).filter(
            UserContainerState.is_archived == True
        ).order_by(UserContainerState.last_accessed.desc())
    elif current_filter == 'doing':
        final_query = filtered_query.join(UserContainerState,
            and_(UserContainerState.container_id == LearningContainer.container_id, UserContainerState.user_id == user_id)
        ).filter(
            UserContainerState.is_archived == False
        ).order_by(UserContainerState.last_accessed.desc())
        
        # Áp dụng bộ lọc 'doing' để chỉ lấy các bộ có tiến độ
        final_query = final_query.filter(
            LearningContainer.container_id.in_(
                db.session.query(LearningItem.container_id).join(UserProgress).filter(
                    UserProgress.user_id == user_id,
                    LearningItem.item_type == 'QUIZ_MCQ'
                ).distinct()
            )
        )
    elif current_filter == 'explore':
        # SỬA LỖI: Chỉ lấy các bộ quiz CHƯA TỪNG được tương tác (không có bản ghi nào trong UserContainerState)
        final_query = filtered_query.filter(
            ~LearningContainer.container_id.in_(user_interacted_ids_subquery)
        ).order_by(LearningContainer.created_at.desc())
    else:
        # Trường hợp mặc định hoặc không hợp lệ, trả về tất cả (loại trừ archive)
        final_query = filtered_query.outerjoin(UserContainerState,
            and_(UserContainerState.container_id == LearningContainer.container_id, UserContainerState.user_id == user_id)
        ).filter(
            or_(UserContainerState.is_archived == False, UserContainerState.is_archived == None)
        ).order_by(LearningContainer.created_at.desc())


    # Phân trang
    pagination = get_pagination_data(final_query, page, per_page=per_page)
    
    # Đếm số lượng câu hỏi trong mỗi bộ (để hiển thị "x/y") và tính phần trăm hoàn thành
    for set_item in pagination.items:
        if not hasattr(set_item, 'creator') or set_item.creator is None:
            full_container = db.session.query(LearningContainer).filter_by(container_id=set_item.container_id).first()
            if full_container and full_container.creator:
                set_item.creator = full_container.creator
            else:
                set_item.creator = type('obj', (object,), {'username' : 'Người dùng không xác định'})()

        total_items = db.session.query(LearningItem).filter_by(
            container_id=set_item.container_id,
            item_type='QUIZ_MCQ'
        ).count()
        
        learned_items = db.session.query(UserProgress).filter(
            UserProgress.user_id == user_id,
            UserProgress.item_id.in_(
                db.session.query(LearningItem.item_id).filter(
                    LearningItem.container_id == set_item.container_id,
                    LearningItem.item_type == 'QUIZ_MCQ'
                )
            )
        ).count()
        
        set_item.item_count_display = f"{learned_items} / {total_items}"
        set_item.total_items = total_items
        set_item.completion_percentage = (learned_items / total_items * 100) if total_items > 0 else 0

        # Lấy trạng thái archive và favorite
        user_state = UserContainerState.query.filter_by(
            user_id=user_id,
            container_id=set_item.container_id
        ).first()
        set_item.user_state = user_state.to_dict() if user_state else {'is_archived': False, 'is_favorite': False}

        # Lấy last_accessed để hiển thị
        set_item.last_accessed = user_state.last_accessed if user_state else None


    print(f">>> ALGORITHMS: Kết thúc get_filtered_quiz_sets. Tổng số bộ: {pagination.total} <<<")
    return pagination

def get_quiz_mode_counts(user_id, set_identifier):
    """
    Tính toán số lượng câu hỏi cho các chế độ học Quiz.
    Hàm này sẽ loại trừ các bộ quiz đã được archive.
    """
    print(f">>> ALGORITHMS: Bắt đầu get_quiz_mode_counts cho user_id={user_id}, set_identifier={set_identifier} <<<")
    
    modes_with_counts = []
    mode_function_map = {
        'new_only': get_new_only_items,
        'due_only': get_reviewed_items,
        'hard_only': get_hard_items,
    }

    for mode_config in QuizLearningConfig.QUIZ_MODES:
        mode_id = mode_config['id']
        mode_name = mode_config['name']
        algorithm_func = mode_function_map.get(mode_id)

        if algorithm_func:
            count = len(algorithm_func(user_id, set_identifier, None))
            modes_with_counts.append({'id': mode_id, 'name': mode_name, 'count': count})
        else:
            current_app.logger.warning(f"Không tìm thấy hàm thuật toán cho chế độ Quiz: {mode_id}")
            modes_with_counts.append({'id': mode_id, 'name': mode_name, 'count': 0})

    print(f">>> ALGORITHMS: Kết thúc get_quiz_mode_counts. Modes: {modes_with_counts} <<<")
    return modes_with_counts
