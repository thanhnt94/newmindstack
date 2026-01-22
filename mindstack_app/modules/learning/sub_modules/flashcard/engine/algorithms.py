# File: mindstack_app/modules/learning/flashcard/engine/algorithms.py
# Phiên bản: 4.0 (Engine refactor)
# MỤC ĐÍCH: Core flashcard algorithms - pure engine module.
# Engine này được gọi từ nhiều entry points: vocabulary, practice, collab.

from mindstack_app.models import (
    db,
    LearningItem,
    LearningContainer,
    ContainerContributor,
    UserContainerState,
    User,
    UserItemMarker,
)
from mindstack_app.models.learning_progress import LearningProgress
from flask_login import current_user
from sqlalchemy import func, and_, not_, or_, cast, String
from flask import current_app
from mindstack_app.utils.pagination import get_pagination_data
from mindstack_app.utils.search import apply_search_filter
from .config import FlashcardLearningConfig
from mindstack_app.services.memory_power_config_service import MemoryPowerConfigService
import random


def _normalize_capability_flags(raw_flags):
    """Chuẩn hóa dữ liệu capability trong ai_settings thành tập hợp chuỗi."""
    normalized = set()
    if isinstance(raw_flags, (list, tuple, set)):
        for value in raw_flags:
            if isinstance(value, str) and value:
                normalized.add(value)
    elif isinstance(raw_flags, dict):
        for key, enabled in raw_flags.items():
            if enabled and isinstance(key, str) and key:
                normalized.add(key)
    elif isinstance(raw_flags, str) and raw_flags:
        normalized.add(raw_flags)
    return normalized


def get_accessible_flashcard_set_ids(user_id):
    """Return IDs of flashcard sets accessible to the current user."""

    base_query = LearningContainer.query.filter(
        LearningContainer.container_type == 'FLASHCARD_SET'
    )

    if current_user.user_role == User.ROLE_ADMIN:
        return [container.container_id for container in base_query.all()]

    if current_user.user_role == User.ROLE_FREE:
        return [
            container.container_id
            for container in base_query.filter(
                LearningContainer.creator_user_id == user_id
            ).all()
        ]

    contributed_ids_subquery = db.session.query(ContainerContributor.container_id).filter(
        ContainerContributor.user_id == user_id,
        ContainerContributor.permission_level == 'editor',
    ).subquery()

    accessible_query = base_query.filter(
        or_(
            LearningContainer.creator_user_id == user_id,
            LearningContainer.is_public == True,
            LearningContainer.container_id.in_(contributed_ids_subquery),
        )
    )

    return [container.container_id for container in accessible_query.all()]


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
    
    accessible_set_ids = set(get_accessible_flashcard_set_ids(user_id))

    if isinstance(container_id, list):
        print(f">>> ALGORITHMS: Chế độ Multi-selection, IDs: {container_id} <<<")
        normalized_ids = []
        for set_id in container_id:
            try:
                set_id_int = int(set_id)
            except (TypeError, ValueError):
                continue
            if set_id_int in accessible_set_ids:
                normalized_ids.append(set_id_int)

        if not normalized_ids:
            items_query = items_query.filter(False)
            print(">>> ALGORITHMS: Không có bộ thẻ khả dụng sau khi lọc multi-selection. <<<")
        else:
            items_query = items_query.filter(LearningItem.container_id.in_(normalized_ids))
    elif container_id == 'all':
        if not accessible_set_ids:
            items_query = items_query.filter(False)
            print(">>> ALGORITHMS: Không có bộ thẻ nào có thể truy cập ở chế độ 'all'. <<<")
        else:
            items_query = items_query.filter(LearningItem.container_id.in_(accessible_set_ids))
            print(f">>> ALGORITHMS: 'all' mode, items_query after filtering by accessible sets: {items_query} <<<")
    else:
        try:
            set_id_int = int(container_id)
            if set_id_int in accessible_set_ids:
                items_query = items_query.filter_by(container_id=set_id_int)
                print(f">>> ALGORITHMS: Cụ thể container_id={set_id_int}, items_query: {items_query} <<<")
            else:
                items_query = items_query.filter(False)
                print(f">>> ALGORITHMS: Người dùng không có quyền với container_id={set_id_int}, truy vấn trả về rỗng. <<<")
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
    
    # MIGRATED: Sử dụng LearningProgress thay vì FlashcardProgress
    new_items_query = base_items_query.outerjoin(LearningProgress, 
        and_(
            LearningProgress.item_id == LearningItem.item_id, 
            LearningProgress.user_id == user_id,
            LearningProgress.learning_mode == LearningProgress.MODE_FLASHCARD
        )
    ).filter(
        or_(
            LearningProgress.item_id == None,
            LearningProgress.fsrs_state == LearningProgress.STATE_NEW
        )
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
    
    # MIGRATED: Sử dụng LearningProgress thay vì FlashcardProgress
    due_items_query = base_items_query.join(
        LearningProgress,
        and_(
            LearningProgress.item_id == LearningItem.item_id,
            LearningProgress.user_id == user_id,
            LearningProgress.learning_mode == LearningProgress.MODE_FLASHCARD
        )
    ).filter(
        LearningProgress.fsrs_due <= func.now()
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
        items = due_items_query.order_by(LearningProgress.fsrs_due.asc()).limit(session_size).all()
    
    print(f">>> ALGORITHMS: get_due_items tìm thấy {len(items)} thẻ. <<<")
    return items

def get_all_review_items(user_id, container_id, session_size):
    """
    Lấy danh sách tất cả các thẻ đã học (đã có tiến độ) để phục vụ chế độ ôn tập toàn bộ.
    Hàm này bỏ qua hạn ôn tập và chỉ loại trừ các bộ thẻ đã bị archive.
    """
    print(f">>> ALGORITHMS: Bắt đầu get_all_review_items cho user_id={user_id}, container_id={container_id}, session_size={session_size} <<<")
    base_items_query = _get_base_items_query(user_id, container_id)

    # MIGRATED: Sử dụng LearningProgress thay vì FlashcardProgress
    review_items_query = base_items_query.join(
        LearningProgress,
        and_(
            LearningProgress.item_id == LearningItem.item_id, 
            LearningProgress.user_id == user_id,
            LearningProgress.learning_mode == LearningProgress.MODE_FLASHCARD
        )
    ).filter(
        LearningProgress.fsrs_state != LearningProgress.STATE_NEW
    )

    review_items_query = review_items_query.outerjoin(UserContainerState,
        and_(UserContainerState.container_id == LearningItem.container_id, UserContainerState.user_id == user_id)
    ).filter(
        or_(UserContainerState.is_archived == False, UserContainerState.is_archived == None)
    )

    print(f">>> ALGORITHMS: review_items_query (ôn tập toàn bộ): {review_items_query} <<<")

    if session_size is None or session_size == 999999:
        return review_items_query
    else:
        items = review_items_query.order_by(
            LearningProgress.fsrs_due.asc(),
            LearningItem.item_id.asc()
        ).limit(session_size).all()

    print(f">>> ALGORITHMS: get_all_review_items tìm thấy {len(items)} thẻ. <<<")
    return items


def _get_items_by_capability(user_id, container_id, session_size, capability_flag):
    """Lấy các thẻ được đánh dấu hỗ trợ một kiểu học cụ thể."""
    print(
        f">>> ALGORITHMS: Bắt đầu _get_items_by_capability cho user_id={user_id}, container_id={container_id}, "
        f"capability={capability_flag}, session_size={session_size} <<<"
    )
    base_items_query = _get_base_items_query(user_id, container_id)

    accessible_ids = set(get_accessible_flashcard_set_ids(user_id))
    if isinstance(container_id, list):
        candidate_ids = set()
        for value in container_id:
            try:
                candidate_id = int(value)
            except (TypeError, ValueError):
                continue
            if candidate_id in accessible_ids:
                candidate_ids.add(candidate_id)
    elif container_id == 'all':
        candidate_ids = accessible_ids
    else:
        try:
            candidate_id = int(container_id)
            candidate_ids = {candidate_id} if candidate_id in accessible_ids else set()
        except (TypeError, ValueError):
            candidate_ids = set()

    enabled_set_ids = set()
    if candidate_ids:
        containers = LearningContainer.query.filter(
            LearningContainer.container_id.in_(candidate_ids)
        ).all()
        for container in containers:
            capabilities = set()
            if hasattr(container, 'capability_flags'):
                capabilities = container.capability_flags()
            else:
                settings_payload = container.ai_settings if hasattr(container, 'ai_settings') else None
                if isinstance(settings_payload, dict):
                    capabilities = _normalize_capability_flags(
                        settings_payload.get('capabilities')
                    )
            if capability_flag in capabilities:
                enabled_set_ids.add(container.container_id)

    capability_items_query = base_items_query.outerjoin(
        UserContainerState,
        and_(
            UserContainerState.container_id == LearningItem.container_id,
            UserContainerState.user_id == user_id
        )
    ).filter(
        or_(
            UserContainerState.is_archived == False,
            UserContainerState.is_archived == None
        )
    )

    capability_json_value = cast(LearningItem.content[capability_flag], String)
    capability_filters = [
        func.lower(func.coalesce(capability_json_value, 'false')) == 'true'
    ]
    if enabled_set_ids:
        capability_filters.append(LearningItem.container_id.in_(enabled_set_ids))

    capability_items_query = capability_items_query.filter(or_(*capability_filters))

    if session_size is None or session_size == 999999:
        return capability_items_query

    items = capability_items_query.order_by(
        LearningItem.order_in_container.asc(),
        LearningItem.item_id.asc()
    ).limit(session_size).all()

    print(
        f">>> ALGORITHMS: _get_items_by_capability tìm thấy {len(items)} thẻ với capability={capability_flag}. <<<"
    )
    return items


def get_pronunciation_items(user_id, container_id, session_size):
    return _get_items_by_capability(user_id, container_id, session_size, 'supports_pronunciation')


def get_writing_items(user_id, container_id, session_size):
    return _get_items_by_capability(user_id, container_id, session_size, 'supports_writing')


def get_quiz_items(user_id, container_id, session_size):
    return _get_items_by_capability(user_id, container_id, session_size, 'supports_quiz')


def get_essay_items(user_id, container_id, session_size):
    return _get_items_by_capability(user_id, container_id, session_size, 'supports_essay')


def get_listening_items(user_id, container_id, session_size):
    return _get_items_by_capability(user_id, container_id, session_size, 'supports_listening')


def get_speaking_items(user_id, container_id, session_size):
    return _get_items_by_capability(user_id, container_id, session_size, 'supports_speaking')


def get_all_items_for_autoplay(user_id, container_id, session_size):
    """
    Lấy toàn bộ thẻ (bao gồm thẻ mới) phục vụ cho chế độ AutoPlay.
    Hàm này vẫn loại trừ các bộ thẻ đã được archive.
    """
    print(
        f">>> ALGORITHMS: Bắt đầu get_all_items_for_autoplay cho user_id={user_id}, container_id={container_id}, session_size={session_size} <<<"
    )
    base_items_query = _get_base_items_query(user_id, container_id)

    autoplay_items_query = base_items_query.outerjoin(
        UserContainerState,
        and_(
            UserContainerState.container_id == LearningItem.container_id,
            UserContainerState.user_id == user_id
        )
    ).filter(
        or_(
            UserContainerState.is_archived == False,
            UserContainerState.is_archived == None
        )
    )

    print(f">>> ALGORITHMS: autoplay_items_query (tất cả thẻ): {autoplay_items_query} <<<")

    if session_size is None or session_size == 999999:
        return autoplay_items_query

    items = autoplay_items_query.order_by(LearningItem.order_in_container.asc()).limit(session_size).all()
    print(f">>> ALGORITHMS: get_all_items_for_autoplay tìm thấy {len(items)} thẻ. <<<")
    return items

def get_hard_items(user_id, container_id, session_size):
    """
    Lấy danh sách các thẻ khó cho một phiên học.
    Sử dụng HardItemService để đảm bảo logic nhất quán với toàn hệ thống.
    TRẢ VỀ: Một đối tượng truy vấn nếu session_size là None, hoặc một danh sách các item nếu session_size được chỉ định.
    """
    print(f">>> ALGORITHMS: Bắt đầu get_hard_items cho user_id={user_id}, container_id={container_id}, session_size={session_size} <<<")
    
    # Use centralized HardItemService for core "hard" logic
    from mindstack_app.modules.learning.services.hard_item_service import HardItemService
    
    hard_items_query = HardItemService.get_hard_items_query(
        user_id=user_id,
        container_id=container_id,
        learning_mode=LearningProgress.MODE_FLASHCARD
    )
    
    # Add archive filter (Session-specific)
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
    
    [OPTIMIZED] Sử dụng batch queries thay vì N+1 queries trong vòng lặp.
    """
    print(f">>> ALGORITHMS: Bắt đầu get_filtered_flashcard_sets cho user_id={user_id}, filter={current_filter} <<<")
    
    # === PHASE 1: Build base query with eager loading ===
    base_query = LearningContainer.query.filter_by(container_type='FLASHCARD_SET')
    
    user_interacted_ids_subquery = db.session.query(UserContainerState.container_id).filter(
        UserContainerState.user_id == user_id
    ).subquery()

    # Access control based on user role
    if current_user.user_role == User.ROLE_ADMIN:
        pass
    elif current_user.user_role == User.ROLE_FREE:
        base_query = base_query.filter(
            or_(
                LearningContainer.creator_user_id == user_id,
                LearningContainer.container_id.in_(user_interacted_ids_subquery),
            )
        )
    else:
        access_conditions = [
            LearningContainer.creator_user_id == user_id,
            LearningContainer.is_public == True,
            LearningContainer.container_id.in_(user_interacted_ids_subquery),
        ]

        contributed_sets_ids = db.session.query(ContainerContributor.container_id).filter(
            ContainerContributor.user_id == user_id,
            ContainerContributor.permission_level == 'editor'
        ).all()

        if contributed_sets_ids:
            access_conditions.append(LearningContainer.container_id.in_([c.container_id for c in contributed_sets_ids]))

        base_query = base_query.filter(or_(*access_conditions))

    # Apply search filter
    search_field_map = {
        'title': LearningContainer.title,
        'description': LearningContainer.description,
        'tags': LearningContainer.tags
    }
    filtered_query = apply_search_filter(base_query, search_query, search_field_map, search_field)

    # === PHASE 2: Apply filter and JOIN UserContainerState in main query ===
    # This eliminates the N+1 query for user_state
    
    if current_filter == 'archive':
        final_query = filtered_query.join(UserContainerState,
            and_(UserContainerState.container_id == LearningContainer.container_id, UserContainerState.user_id == user_id)
        ).add_columns(
            UserContainerState.is_archived,
            UserContainerState.is_favorite,
            UserContainerState.last_accessed
        ).filter(
            UserContainerState.is_archived == True
        ).order_by(UserContainerState.last_accessed.desc())
    elif current_filter == 'doing':
        final_query = filtered_query.join(UserContainerState,
            and_(UserContainerState.container_id == LearningContainer.container_id, UserContainerState.user_id == user_id)
        ).add_columns(
            UserContainerState.is_archived,
            UserContainerState.is_favorite,
            UserContainerState.last_accessed
        ).filter(
            UserContainerState.is_archived == False
        ).order_by(UserContainerState.last_accessed.desc())
    elif current_filter == 'explore':
        # Explore: sets never interacted with - use literal values for columns
        final_query = filtered_query.filter(
            ~LearningContainer.container_id.in_(user_interacted_ids_subquery)
        ).add_columns(
            db.literal(False).label('is_archived'),
            db.literal(False).label('is_favorite'),
            db.literal(None).label('last_accessed')
        ).order_by(LearningContainer.created_at.desc())
    else:
        # Default: all non-archived sets
        final_query = filtered_query.outerjoin(UserContainerState,
            and_(UserContainerState.container_id == LearningContainer.container_id, UserContainerState.user_id == user_id)
        ).add_columns(
            UserContainerState.is_archived,
            UserContainerState.is_favorite,
            UserContainerState.last_accessed
        ).filter(
            or_(UserContainerState.is_archived == False, UserContainerState.is_archived == None)
        ).order_by(LearningContainer.created_at.desc())

    # === PHASE 3: Paginate ===
    pagination = get_pagination_data(final_query, page, per_page=per_page)
    
    # Extract container IDs and map joined data
    container_ids = []
    user_state_map = {}  # container_id -> {is_archived, is_favorite, last_accessed}
    
    for row in pagination.items:
        # Row is a tuple: (LearningContainer, is_archived, is_favorite, last_accessed)
        if isinstance(row, tuple):
            container = row[0]
            user_state_map[container.container_id] = {
                'is_archived': row[1] if row[1] is not None else False,
                'is_favorite': row[2] if row[2] is not None else False,
                'last_accessed': row[3]
            }
        else:
            container = row
            user_state_map[container.container_id] = {'is_archived': False, 'is_favorite': False, 'last_accessed': None}
        container_ids.append(container.container_id)
    
    if not container_ids:
        # Empty result, return early
        # Convert pagination items to proper format
        pagination.items = []
        return pagination
    
    # === PHASE 4: Batch Query for Item Counts ===
    # Single query to get total items per container
    item_counts = db.session.query(
        LearningItem.container_id,
        func.count(LearningItem.item_id).label('total')
    ).filter(
        LearningItem.container_id.in_(container_ids),
        LearningItem.item_type == 'FLASHCARD'
    ).group_by(LearningItem.container_id).all()
    
    item_count_map = {row.container_id: row.total for row in item_counts}
    
    # === PHASE 5: Batch Query for Learned Items ===
    # Single query to get learned items per container
    # Join LearningProgress with LearningItem to filter by container
    learned_counts = db.session.query(
        LearningItem.container_id,
        func.count(LearningProgress.item_id).label('learned')
    ).join(
        LearningProgress,
        and_(
            LearningProgress.item_id == LearningItem.item_id,
            LearningProgress.user_id == user_id,
            LearningProgress.learning_mode == LearningProgress.MODE_FLASHCARD
        )
    ).filter(
        LearningItem.container_id.in_(container_ids),
        LearningItem.item_type == 'FLASHCARD'
    ).group_by(LearningItem.container_id).all()
    
    learned_count_map = {row.container_id: row.learned for row in learned_counts}
    
    # === PHASE 6: Map batch data to pagination items ===
    processed_items = []
    
    for row in pagination.items:
        if isinstance(row, tuple):
            set_item = row[0]
        else:
            set_item = row
        
        container_id = set_item.container_id
        
        # Ensure creator is loaded (should be eager loaded, but fallback if not)
        if not hasattr(set_item, 'creator') or set_item.creator is None:
            set_item.creator = type('obj', (object,), {'username': 'Người dùng không xác định'})()
        
        # Get counts from batch query maps
        total_items = item_count_map.get(container_id, 0)
        learned_items = learned_count_map.get(container_id, 0)
        
        set_item.item_count_display = f"{learned_items} / {total_items}"
        set_item.total_items = total_items
        set_item.completion_percentage = (learned_items / total_items * 100) if total_items > 0 else 0
        
        # Get user state from map (already fetched via JOIN)
        state_data = user_state_map.get(container_id, {'is_archived': False, 'is_favorite': False, 'last_accessed': None})
        set_item.user_state = state_data
        set_item.last_accessed = state_data.get('last_accessed')
        
        processed_items.append(set_item)
    
    # Replace pagination items with processed containers
    pagination.items = processed_items

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
        'all_review': get_all_review_items,
        'hard_only': get_hard_items,
        'pronunciation_practice': get_pronunciation_items,
        'writing_practice': get_writing_items,
        'quiz_practice': get_quiz_items,
        'essay_practice': get_essay_items,
        'listening_practice': get_listening_items,
        'speaking_practice': get_speaking_items,
    }

    for mode_config in FlashcardLearningConfig.FLASHCARD_MODES:
        mode_id = mode_config['id']
        mode_name = mode_config['name']
        algorithm_func = mode_function_map.get(mode_id)
        hide_if_zero = mode_config.get('hide_if_zero', False)

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

            if hide_if_zero and count == 0:
                continue

            modes_with_counts.append({'id': mode_id, 'name': mode_name, 'count': count})
        else:
            current_app.logger.warning(f"Không tìm thấy hàm thuật toán cho chế độ Flashcard: {mode_id}")
            modes_with_counts.append({'id': mode_id, 'name': mode_name, 'count': 0})

    autoplay_learned_count = get_all_review_items(user_id, set_identifier, None).count()
    autoplay_all_count = get_all_items_for_autoplay(user_id, set_identifier, None).count()
    autoplay_total_count = max(autoplay_learned_count, autoplay_all_count)

    modes_with_counts.append({
        'id': 'autoplay',
        'name': FlashcardLearningConfig.AUTOPLAY_MODE_NAME,
        'count': autoplay_total_count,
        'autoplay_counts': {
            'autoplay_learned': autoplay_learned_count,
            'autoplay_all': autoplay_all_count,
        }
    })

    print(f">>> ALGORITHMS: Kết thúc get_flashcard_mode_counts. Modes: {modes_with_counts} <<<")
    return modes_with_counts
