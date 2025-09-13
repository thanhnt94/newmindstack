# File: mindstack_app/modules/learning/flashcard_learning/algorithms.py
# Phiên bản: 2.3 (Corrected)
# MỤC ĐÍCH: Khắc phục lỗi TypeError: '<' not supported between instances of 'int' and 'NoneType'.
# ĐÃ SỬA: Cập nhật hàm get_mixed_items để xử lý chính xác trường hợp session_size là None, trả về một query hợp nhất để đếm.

from ....models import db, LearningItem, FlashcardProgress, LearningContainer, ContainerContributor, UserContainerState
from flask_login import current_user
from sqlalchemy import func, and_, not_, or_
from flask import current_app
from ....utils.pagination import get_pagination_data
from ....utils.search import apply_search_filter
from .config import FlashcardLearningConfig
import random

def _get_base_items_query(user_id, container_id):
    """
    Tạo truy vấn cơ sở cho LearningItem dựa trên container_id hoặc tất cả các container có thể truy cập.
    Hàm này sẽ không lọc theo trạng thái archive. Việc lọc archive sẽ được xử lý ở các hàm gọi nó.
    CÓ THỂ NHẬN: Một số nguyên (container_id), chuỗi 'all', hoặc một danh sách các số nguyên.

    Args:
        user_id (int): ID của người dùng hiện tại.
        container_id (int/str/list): ID của LearningContainer, 'all', hoặc danh sách các ID.

    Returns:
        sqlalchemy.orm.query.Query: Đối tượng truy vấn LearningItem cơ sở.
    """
    print(f">>> ALGORITHMS: Bắt đầu _get_base_items_query cho user_id={user_id}, container_id={container_id} <<<")
    items_query = LearningItem.query.filter(LearningItem.item_type == 'FLASHCARD')
    
    if isinstance(container_id, list):
        print(f">>> ALGORITHMS: Chế độ Multi-selection, IDs: {container_id} <<<")
        items_query = items_query.filter(LearningItem.container_id.in_(container_id))
    elif container_id == 'all':
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
                LearningContainer.container_type == 'FLASHCARD_SET',
                or_(*access_conditions)
            ).all()
            all_accessible_flashcard_set_ids = [c.container_id for c in accessible_containers]
            print(f">>> ALGORITHMS: 'all' mode (User), Accessible Flashcard Set IDs: {all_accessible_flashcard_set_ids} <<<")
        else:
            all_accessible_flashcard_set_ids = [s.container_id for s in LearningContainer.query.filter_by(container_type='FLASHCARD_SET').all()]
            print(f">>> ALGORITHMS: 'all' mode (Admin), All Flashcard Set IDs: {all_accessible_flashcard_set_ids} <<<")
        
        if not all_accessible_flashcard_set_ids:
            items_query = items_query.filter(False)
            print(">>> ALGORITHMS: Không có bộ thẻ nào có thể truy cập, truy vấn trả về rỗng. <<<")
        else:
            items_query = items_query.filter(LearningItem.container_id.in_(all_accessible_flashcard_set_ids))
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
    Lấy danh sách các thẻ chỉ làm mới (chưa có tiến độ) cho một phiên học.
    Hàm này sẽ loại trừ các bộ thẻ đã được archive.
    TRẢ VỀ: Một đối tượng truy vấn nếu session_size là None, hoặc một danh sách các item nếu session_size được chỉ định.
    """
    print(f">>> ALGORITHMS: Bắt đầu get_new_only_items cho user_id={user_id}, container_id={container_id}, session_size={session_size} <<<")
    base_items_query = _get_base_items_query(user_id, container_id)
    
    # SỬA: Join với FlashcardProgress thay vì UserProgress
    new_items_query = base_items_query.outerjoin(FlashcardProgress, 
        and_(FlashcardProgress.item_id == LearningItem.item_id, FlashcardProgress.user_id == user_id)
    ).filter(
        FlashcardProgress.item_id == None
    )

    new_items_query = new_items_query.outerjoin(UserContainerState,
        and_(UserContainerState.container_id == LearningItem.container_id, UserContainerState.user_id == user_id)
    ).filter(
        or_(UserContainerState.is_archived == False, UserContainerState.is_archived == None)
    )
    
    print(f">>> ALGORITHMS: new_items_query (chỉ làm mới): {new_items_query} <<<")
    
    if session_size is None or session_size == 999999:
        return new_items_query
    else:
        items = new_items_query.order_by(func.random()).limit(session_size).all()
    
    print(f">>> ALGORITHMS: get_new_only_items tìm thấy {len(items)} thẻ. <<<")
    return items

def get_due_items(user_id, container_id, session_size):
    """
    Lấy danh sách các thẻ cần ôn tập (due_time < now) cho một phiên học.
    Hàm này sẽ loại trừ các bộ thẻ đã được archive.
    TRẢ VỀ: Một đối tượng truy vấn nếu session_size là None, hoặc một danh sách các item nếu session_size được chỉ định.
    """
    print(f">>> ALGORITHMS: Bắt đầu get_due_items cho user_id={user_id}, container_id={container_id}, session_size={session_size} <<<")
    base_items_query = _get_base_items_query(user_id, container_id)
    
    # SỬA: Join với FlashcardProgress thay vì UserProgress
    due_items_query = base_items_query.join(FlashcardProgress).filter(
        FlashcardProgress.user_id == user_id,
        FlashcardProgress.due_time <= func.now()
    )
    
    due_items_query = due_items_query.outerjoin(UserContainerState,
        and_(UserContainerState.container_id == LearningItem.container_id, UserContainerState.user_id == user_id)
    ).filter(
        or_(UserContainerState.is_archived == False, UserContainerState.is_archived == None)
    )
    
    print(f">>> ALGORITHMS: due_items_query (đến hạn): {due_items_query} <<<")
    
    if session_size is None or session_size == 999999:
        return due_items_query
    else:
        items = due_items_query.order_by(FlashcardProgress.due_time.asc()).limit(session_size).all()
    
    print(f">>> ALGORITHMS: get_due_items tìm thấy {len(items)} thẻ. <<<")
    return items

def get_hard_items(user_id, container_id, session_size):
    """
    Lấy danh sách các thẻ khó (incorrect_streak > 0 hoặc memory_score thấp) cho một phiên học.
    Hàm này sẽ loại trừ các bộ thẻ đã được archive.
    TRẢ VỀ: Một đối tượng truy vấn nếu session_size là None, hoặc một danh sách các item nếu session_size được chỉ định.
    """
    print(f">>> ALGORITHMS: Bắt đầu get_hard_items cho user_id={user_id}, container_id={container_id}, session_size={session_size} <<<")
    base_items_query = _get_base_items_query(user_id, container_id)

    # SỬA: Join với FlashcardProgress thay vì UserProgress
    hard_items_query = base_items_query.join(FlashcardProgress).filter(
        FlashcardProgress.user_id == user_id,
        FlashcardProgress.status == 'hard'
    )
    
    hard_items_query = hard_items_query.outerjoin(UserContainerState,
        and_(UserContainerState.container_id == LearningItem.container_id, UserContainerState.user_id == user_id)
    ).filter(
        or_(UserContainerState.is_archived == False, UserContainerState.is_archived == None)
    )

    print(f">>> ALGORITHMS: hard_items_query (thẻ khó): {hard_items_query} <<<")
    
    if session_size is None or session_size == 999999:
        return hard_items_query
    else:
        items = hard_items_query.order_by(func.random()).limit(session_size).all()
    
    print(f">>> ALGORITHMS: get_hard_items tìm thấy {len(items)} thẻ. <<<")
    return items

def get_mixed_items(user_id, container_id, session_size):
    """
    Mô tả: Lấy một truy vấn hợp nhất của thẻ đến hạn và thẻ mới.
           Hàm này chủ yếu được dùng để ĐẾM tổng số thẻ có thể học khi bắt đầu một phiên.
           Logic chọn thẻ thực tế nằm trong SessionManager.
    Args:
        user_id (int): ID của người dùng.
        container_id (int/str/list): ID của bộ thẻ, 'all', hoặc danh sách ID.
        session_size (int): Thường là None khi gọi từ SessionManager.
    Returns:
        Query: Một đối tượng truy vấn SQLAlchemy.
    """
    print(f">>> ALGORITHMS: Bắt đầu get_mixed_items cho user_id={user_id}, container_id={container_id}, session_size={session_size} <<<")
    
    # ĐÃ SỬA: Khắc phục lỗi TypeError bằng cách chỉ trả về một query hợp nhất để đếm, thay vì xử lý logic phức tạp ở đây.
    # Hàm này chỉ cần cung cấp một cách để biết tổng số thẻ có thể học trong chế độ này.
    
    due_items_query = get_due_items(user_id, container_id, None)
    new_items_query = get_new_only_items(user_id, container_id, None)
    
    # Kết hợp hai truy vấn lại với nhau
    # Đây là cách hiệu quả để đếm tổng số thẻ duy nhất từ cả hai nhóm
    mixed_query = due_items_query.union(new_items_query)
    
    print(f">>> ALGORITHMS: get_mixed_items đã tạo một query hợp nhất. <<<")
    return mixed_query


def get_filtered_flashcard_sets(user_id, search_query, search_field, current_filter, page, per_page=FlashcardLearningConfig.DEFAULT_ITEMS_PER_PAGE):
    """
    Lấy danh sách các bộ Flashcard đã được lọc và phân trang dựa trên các tiêu chí.
    """
    print(f">>> ALGORITHMS: Bắt đầu get_filtered_flashcard_sets cho user_id={user_id}, filter={current_filter} <<<")
    base_query = LearningContainer.query.filter_by(container_type='FLASHCARD_SET')

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

    search_field_map = {
        'title': LearningContainer.title,
        'description': LearningContainer.description,
        'tags': LearningContainer.tags
    }
    
    filtered_query = apply_search_filter(base_query, search_query, search_field_map, search_field)

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
        # SỬA: Truy vấn để lấy các bộ thẻ có tiến độ học từ bảng FlashcardProgress
        final_query = filtered_query.join(LearningItem,
            LearningContainer.container_id == LearningItem.container_id
        ).join(FlashcardProgress,
            and_(LearningItem.item_id == FlashcardProgress.item_id, FlashcardProgress.user_id == user_id)
        ).distinct().outerjoin(UserContainerState,
            and_(UserContainerState.container_id == LearningContainer.container_id, UserContainerState.user_id == user_id)
        ).filter(
            or_(UserContainerState.is_archived == False, UserContainerState.is_archived == None)
        ).order_by(
            db.case(
                (UserContainerState.last_accessed.isnot(None), UserContainerState.last_accessed),
                else_=LearningContainer.created_at
            ).desc()
        )
    elif current_filter == 'explore':
        final_query = filtered_query.filter(
            ~LearningContainer.container_id.in_(user_interacted_ids_subquery)
        ).order_by(LearningContainer.created_at.desc())
    else:
        final_query = filtered_query.outerjoin(UserContainerState,
            and_(UserContainerState.container_id == LearningContainer.container_id, UserContainerState.user_id == user_id)
        ).filter(
            or_(UserContainerState.is_archived == False, UserContainerState.is_archived == None)
        ).order_by(LearningContainer.created_at.desc())

    pagination = get_pagination_data(final_query, page, per_page=per_page)
    
    for set_item in pagination.items:
        if not hasattr(set_item, 'creator') or set_item.creator is None:
            full_container = db.session.query(LearningContainer).filter_by(container_id=set_item.container_id).first()
            if full_container and full_container.creator:
                set_item.creator = full_container.creator
            else:
                set_item.creator = type('obj', (object,), {'username' : 'Người dùng không xác định'})()

        total_items = db.session.query(LearningItem).filter_by(
            container_id=set_item.container_id,
            item_type='FLASHCARD'
        ).count()
        
        # SỬA: Truy vấn số lượng thẻ đã học từ bảng FlashcardProgress
        learned_items = db.session.query(FlashcardProgress).filter(
            FlashcardProgress.user_id == user_id,
            FlashcardProgress.item_id.in_(
                db.session.query(LearningItem.item_id).filter(
                    LearningItem.container_id == set_item.container_id,
                    LearningItem.item_type == 'FLASHCARD'
                )
            )
        ).count()
        
        set_item.item_count_display = f"{learned_items} / {total_items}"
        set_item.total_items = total_items
        set_item.completion_percentage = (learned_items / total_items * 100) if total_items > 0 else 0

        user_state = UserContainerState.query.filter_by(
            user_id=user_id,
            container_id=set_item.container_id
        ).first()
        set_item.user_state = user_state.to_dict() if user_state else {'is_archived': False, 'is_favorite': False}

        set_item.last_accessed = user_state.last_accessed if user_state else None

    print(f">>> ALGORITHMS: Kết thúc get_filtered_flashcard_sets. Tổng số bộ: {pagination.total} <<<")
    return pagination

def get_flashcard_mode_counts(user_id, set_identifier):
    """
    Tính toán số lượng thẻ cho các chế độ học Flashcard.
    Hàm này sẽ loại trừ các bộ thẻ đã được archive.
    """
    print(f">>> ALGORITHMS: Bắt đầu get_flashcard_mode_counts cho user_id={user_id}, set_identifier={set_identifier} <<<")
    
    modes_with_counts = []
    mode_function_map = {
        'mixed_srs': get_mixed_items,
        'new_only': get_new_only_items,
        'due_only': get_due_items,
        'hard_only': get_hard_items,
    }

    for mode_config in FlashcardLearningConfig.FLASHCARD_MODES:
        mode_id = mode_config['id']
        mode_name = mode_config['name']
        algorithm_func = mode_function_map.get(mode_id)

        if algorithm_func:
            # SỬA LỖI: Sử dụng .count() trên đối tượng truy vấn để lấy số lượng
            # Thay vì gọi hàm với session_size=None và sau đó dùng len()
            if mode_id == 'mixed_srs':
                # Chế độ mixed_srs cần phải chạy logic để lấy số lượng thẻ
                due_count = get_due_items(user_id, set_identifier, None).count()
                new_count = get_new_only_items(user_id, set_identifier, None).count()
                count = due_count + new_count
            else:
                count = algorithm_func(user_id, set_identifier, None).count()
            
            modes_with_counts.append({'id': mode_id, 'name': mode_name, 'count': count})
        else:
            current_app.logger.warning(f"Không tìm thấy hàm thuật toán cho chế độ Flashcard: {mode_id}")
            modes_with_counts.append({'id': mode_id, 'name': mode_name, 'count': 0})

    print(f">>> ALGORITHMS: Kết thúc get_flashcard_mode_counts. Modes: {modes_with_counts} <<<")
    return modes_with_counts