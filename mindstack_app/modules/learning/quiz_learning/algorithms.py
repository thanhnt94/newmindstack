# File: mindstack_app/modules/learning/quiz_learning/algorithms.py
# Phiên bản: 1.10
# Mục đích: Chứa logic thuật toán để lựa chọn và sắp xếp các câu hỏi Quiz cho các chế độ học khác nhau.
# ĐÃ SỬA: Cập nhật logic lọc cho chế độ 'explore' để bao gồm các bộ quiz của người dùng chưa có tiến độ.
# ĐÃ SỬA: Tối ưu hóa truy vấn cho bộ lọc 'doing' để cải thiện hiệu suất khi lấy thời gian review gần nhất.

from ....models import db, LearningItem, UserProgress, LearningContainer, ContainerContributor
from flask_login import current_user
from sqlalchemy import func, and_, not_, or_
from flask import current_app # Để dùng logger
from ....utils.pagination import get_pagination_data # Import hàm phân trang
from ....utils.search import apply_search_filter # Import hàm tìm kiếm
from .config import QuizLearningConfig # THÊM MỚI: Import cấu hình riêng của Quiz Learning


def _get_base_items_query(user_id, container_id):
    """
    Tạo truy vấn cơ sở cho LearningItem dựa trên container_id hoặc tất cả các container có thể truy cập.

    Args:
        user_id (int): ID của người dùng hiện tại.
        container_id (int/str): ID của LearningContainer hoặc 'all' nếu muốn lấy tất cả các bộ.

    Returns:
        sqlalchemy.orm.query.Query: Đối tượng truy vấn LearningItem cơ sở.
    """
    print(f">>> ALGORITHMS: Bắt đầu _get_base_items_query cho user_id={user_id}, container_id={container_id} <<<")
    items_query = LearningItem.query.filter(LearningItem.item_type == 'QUIZ_MCQ')

    if container_id == 'all':
        # Xây dựng điều kiện lọc quyền truy cập dựa trên vai trò người dùng
        access_conditions = []
        if current_user.user_role != 'admin':
            access_conditions.append(LearningContainer.creator_user_id == user_id) # Người tạo
            access_conditions.append(LearningContainer.is_public == True) # Công khai
            
            # Người đóng góp với quyền editor
            contributed_ids_subquery = db.session.query(ContainerContributor.container_id).filter(
                ContainerContributor.user_id == user_id,
                ContainerContributor.permission_level == 'editor'
            ).subquery()
            access_conditions.append(LearningContainer.container_id.in_(contributed_ids_subquery))

            # Lấy tất cả các container_id có thể truy cập vào một list Python
            accessible_containers = LearningContainer.query.filter(
                LearningContainer.container_type == 'QUIZ_SET',
                or_(*access_conditions)
            ).all()
            all_accessible_quiz_set_ids = [c.container_id for c in accessible_containers]
            print(f">>> ALGORITHMS: 'all' mode (User), Accessible Quiz Set IDs: {all_accessible_quiz_set_ids} <<<")
        else:
            # Admin có quyền truy cập tất cả các bộ quiz
            all_accessible_quiz_set_ids = [s.container_id for s in LearningContainer.query.filter_by(container_type='QUIZ_SET').all()]
            print(f">>> ALGORITHMS: 'all' mode (Admin), All Quiz Set IDs: {all_accessible_quiz_set_ids} <<<")
        
        if not all_accessible_quiz_set_ids:
            items_query = items_query.filter(False) # Truy vấn rỗng nếu không có bộ nào
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

    Args:
        user_id (int): ID của người dùng.
        container_id (int/str): ID của bộ Quiz hoặc 'all'.
        session_size (int): Số lượng câu hỏi mong muốn trong phiên.

    Returns:
        list: Danh sách các đối tượng LearningItem.
    """
    print(f">>> ALGORITHMS: Bắt đầu get_new_only_items cho user_id={user_id}, container_id={container_id}, session_size={session_size} <<<")
    base_items_query = _get_base_items_query(user_id, container_id)
    
    # Lọc các item chưa có bản ghi UserProgress cho người dùng hiện tại
    new_items_query = base_items_query.outerjoin(UserProgress, 
        and_(UserProgress.item_id == LearningItem.item_id, UserProgress.user_id == user_id)
    ).filter(
        UserProgress.item_id == None # Điều kiện UserProgress.item_id == None có nghĩa là không có bản ghi UserProgress khớp
    )
    
    print(f">>> ALGORITHMS: new_items_query (chỉ làm mới): {new_items_query} <<<")
    
    # Lấy ngẫu nhiên các câu hỏi mới và giới hạn số lượng
    # Nếu session_size là None hoặc giá trị lớn, lấy tất cả để đếm
    if session_size is None or session_size == 999999:
        items = new_items_query.all()
    else:
        items = new_items_query.order_by(func.random()).limit(session_size).all()
    
    print(f">>> ALGORITHMS: get_new_only_items tìm thấy {len(items)} câu hỏi. <<<")
    return items

def get_reviewed_items(user_id, container_id, session_size):
    """
    Lấy danh sách các câu hỏi đã làm (có tiến độ) cho một phiên học, không bao gồm câu mới.
    Các câu hỏi sẽ được chọn ngẫu nhiên.

    Args:
        user_id (int): ID của người dùng.
        container_id (int/str): ID của bộ Quiz hoặc 'all'.
        session_size (int): Số lượng câu hỏi mong muốn trong phiên.

    Returns:
        list: Danh sách các đối tượng LearningItem.
    """
    print(f">>> ALGORITHMS: Bắt đầu get_reviewed_items cho user_id={user_id}, container_id={container_id}, session_size={session_size} <<<")
    base_items_query = _get_base_items_query(user_id, container_id)
    
    # Lọc các item đã có bản ghi UserProgress cho người dùng hiện tại
    # và không phải là item mới (đã được xem ít nhất 1 lần)
    reviewed_items_query = base_items_query.join(UserProgress).filter(
        UserProgress.user_id == user_id,
        UserProgress.first_seen_timestamp != None # Đảm bảo đã từng được xem
    )
    print(f">>> ALGORITHMS: reviewed_items_query (đã làm): {reviewed_items_query} <<<")
    
    # Lấy ngẫu nhiên các câu hỏi đã làm và giới hạn số lượng
    if session_size is None or session_size == 999999:
        items = reviewed_items_query.all()
    else:
        items = reviewed_items_query.order_by(func.random()).limit(session_size).all()
    
    print(f">>> ALGORITHMS: get_reviewed_items tìm thấy {len(items)} câu hỏi. <<<")
    return items

def get_hard_items(user_id, container_id, session_size):
    """
    Lấy danh sách các câu hỏi khó cho một phiên học.
    Định nghĩa câu khó: đã được trả lời ít nhất 10 lần (tổng đúng + sai)
    VÀ tỷ lệ đúng < 50%.

    Args:
        user_id (int): ID của người dùng.
        container_id (int/str): ID của bộ Quiz hoặc 'all'.
        session_size (int): Số lượng câu hỏi mong muốn trong phiên.

    Returns:
        list: Danh sách các đối tượng LearningItem.
    """
    print(f">>> ALGORITHMS: Bắt đầu get_hard_items cho user_id={user_id}, container_id={container_id}, session_size={session_size} <<<")
    base_items_query = _get_base_items_query(user_id, container_id)

    # Lọc các item có tiến độ cho người dùng hiện tại
    hard_items_query = base_items_query.join(UserProgress).filter(
        UserProgress.user_id == user_id,
        # Đã trả lời ít nhất 10 lần (tổng đúng + sai)
        (UserProgress.times_correct + UserProgress.times_incorrect) >= 10,
        # Tỷ lệ đúng < 50%
        (UserProgress.times_correct / (UserProgress.times_correct + UserProgress.times_incorrect)) < 0.5
    )
    print(f">>> ALGORITHMS: hard_items_query (câu khó): {hard_items_query} <<<")
    
    # Lấy ngẫu nhiên các câu hỏi khó và giới hạn số lượng
    if session_size is None or session_size == 999999:
        items = hard_items_query.all()
    else:
        items = hard_items_query.order_by(func.random()).limit(session_size).all()
    
    print(f">>> ALGORITHMS: get_hard_items tìm thấy {len(items)} câu hỏi. <<<")
    return items

def get_filtered_quiz_sets(user_id, search_query, search_field, current_filter, page, per_page=QuizLearningConfig.DEFAULT_ITEMS_PER_PAGE):
    """
    Lấy danh sách các bộ Quiz đã được lọc và phân trang dựa trên các tiêu chí.

    Args:
        user_id (int): ID của người dùng hiện tại.
        search_query (str): Chuỗi tìm kiếm.
        search_field (str): Trường tìm kiếm ('all', 'title', 'description', 'tags').
        current_filter (str): Bộ lọc ('doing', 'explore').
        page (int): Số trang hiện tại.
        per_page (int): Số mục trên mỗi trang. Mặc định lấy từ QuizLearningConfig.

    Returns:
        Pagination: Đối tượng phân trang của Flask-SQLAlchemy.
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

    # Áp dụng bộ lọc "Đang làm" hoặc "Khám phá"
    final_query = filtered_query
    
    # THAY ĐỔI LỚN: Tối ưu hóa truy vấn cho bộ lọc 'doing'
    if current_filter == 'doing':
        # Bắt đầu với truy vấn các container mà người dùng đã có tiến độ
        # Sử dụng join với UserProgress và LearningItem để đảm bảo chỉ lấy các bộ quiz có MCQ
        progressed_containers_query = db.session.query(
            LearningContainer.container_id,
            LearningContainer.title,
            LearningContainer.description,
            LearningContainer.tags,
            LearningContainer.is_public,
            LearningContainer.created_at,
            LearningContainer.updated_at,
            LearningContainer.creator_user_id,
            # Lấy thời gian review gần nhất cho mỗi container
            func.max(UserProgress.last_reviewed).label('latest_review')
        ).join(LearningItem, LearningContainer.container_id == LearningItem.container_id).join(
            UserProgress, and_(UserProgress.item_id == LearningItem.item_id, UserProgress.user_id == user_id)
        ).filter(
            LearningContainer.container_type == 'QUIZ_SET',
            LearningItem.item_type == 'QUIZ_MCQ'
        ).group_by(LearningContainer.container_id).subquery() # Tạo subquery từ đây

        # Join lại với LearningContainer để lấy các trường khác và áp dụng bộ lọc tìm kiếm
        # Sắp xếp theo latest_review (thời gian review gần nhất) giảm dần
        final_query = db.session.query(LearningContainer).join(
            progressed_containers_query,
            LearningContainer.container_id == progressed_containers_query.c.container_id
        ).order_by(progressed_containers_query.c.latest_review.desc())

        # Áp dụng lại bộ lọc tìm kiếm trên final_query đã join (nếu có)
        final_query = apply_search_filter(final_query, search_query, search_field_map, search_field)

    elif current_filter == 'explore':
        # Lấy tất cả các bộ quiz mà người dùng CÓ THỂ TRUY CẬP (đã được lọc bởi base_query)
        # và sau đó loại bỏ những bộ mà người dùng ĐÃ CÓ TIẾN ĐỘ.
        user_progressed_container_ids_list = db.session.query(LearningItem.container_id).join(UserProgress).filter(
            UserProgress.user_id == user_id,
            LearningItem.item_type == 'QUIZ_MCQ'
        ).distinct().all()
        progressed_ids = [c.container_id for c in user_progressed_container_ids_list]

        if progressed_ids:
            final_query = final_query.filter(
                ~LearningContainer.container_id.in_(progressed_ids)
            )
        
        final_query = final_query.order_by(LearningContainer.created_at.desc()) # Sắp xếp theo ngày tạo mới nhất
    
    # Phân trang
    pagination = get_pagination_data(final_query, page, per_page=per_page)
    
    # Đếm số lượng câu hỏi trong mỗi bộ (để hiển thị "x/y") và tính phần trăm hoàn thành
    for set_item in pagination.items:
        # Lấy thông tin người tạo
        if not hasattr(set_item, 'creator') or set_item.creator is None:
            # Nếu set_item là kết quả từ subquery (doing filter), nó không có quan hệ creator
            # Cần tải lại đối tượng đầy đủ hoặc join với User
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
        
        set_item.item_count_display = f"{learned_items} / {total_items}" # Tên mới để tránh xung đột với .item_count
        set_item.total_items = total_items # Lưu tổng số item để kiểm tra có thể chọn được không

        # Tính phần trăm hoàn thành
        set_item.completion_percentage = (learned_items / total_items * 100) if total_items > 0 else 0

        # Lấy thời gian review gần nhất cho bộ này (nếu có)
        # Đối với bộ lọc 'doing', latest_review đã có trong progressed_containers_query
        # Đối với bộ lọc 'explore', cần query riêng nếu muốn hiển thị
        if current_filter == 'explore':
            latest_review = db.session.query(func.max(UserProgress.last_reviewed)).join(LearningItem).filter(
                UserProgress.user_id == user_id,
                LearningItem.container_id == set_item.container_id,
                LearningItem.item_type == 'QUIZ_MCQ'
            ).scalar()
            set_item.latest_review_timestamp = latest_review # Lưu timestamp để hiển thị hoặc debug
        elif current_filter == 'doing' and hasattr(set_item, 'latest_review'):
            # Nếu đã có từ subquery, sử dụng nó
            set_item.latest_review_timestamp = set_item.latest_review


    print(f">>> ALGORITHMS: Kết thúc get_filtered_quiz_sets. Tổng số bộ: {pagination.total} <<<")
    return pagination

def get_quiz_mode_counts(user_id, set_identifier):
    """
    Tính toán số lượng câu hỏi cho các chế độ học Quiz.

    Args:
        user_id (int): ID của người dùng hiện tại.
        set_identifier (int/str): ID của bộ Quiz hoặc 'all'.

    Returns:
        list: Danh sách các dict, mỗi dict chứa {'id': mode_id, 'name': mode_name, 'count': count}.
    """
    print(f">>> ALGORITHMS: Bắt đầu get_quiz_mode_counts cho user_id={user_id}, set_identifier={set_identifier} <<<")
    
    modes_with_counts = []
    # Ánh xạ mode_id với hàm lấy câu hỏi tương ứng
    mode_function_map = {
        'new_only': get_new_only_items,
        'due_only': get_reviewed_items,
        'hard_only': get_hard_items,
        # Thêm các ánh xạ khác tại đây nếu có thêm mode
        # Ví dụ: {'id': 'random_all', 'name': 'Ngẫu nhiên tất cả', 'algorithm_func_name': 'get_all_items_randomly'},
    }

    for mode_config in QuizLearningConfig.QUIZ_MODES:
        mode_id = mode_config['id']
        mode_name = mode_config['name']
        algorithm_func = mode_function_map.get(mode_id)

        if algorithm_func:
            # None để lấy tất cả các câu phù hợp, không giới hạn bởi session_size ở đây
            count = len(algorithm_func(user_id, set_identifier, None))
            modes_with_counts.append({'id': mode_id, 'name': mode_name, 'count': count})
        else:
            current_app.logger.warning(f"Không tìm thấy hàm thuật toán cho chế độ Quiz: {mode_id}")
            modes_with_counts.append({'id': mode_id, 'name': mode_name, 'count': 0}) # Trả về 0 nếu không có hàm

    print(f">>> ALGORITHMS: Kết thúc get_quiz_mode_counts. Modes: {modes_with_counts} <<<")
    return modes_with_counts
