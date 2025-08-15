# File: mindstack_app/modules/learning/quiz_learning/algorithms.py
# Phiên bản: 1.3
# Mục đích: Chứa logic thuật toán để lựa chọn và sắp xếp các câu hỏi Quiz cho các chế độ học khác nhau.
# ĐÃ SỬA: Thêm print() debug chi tiết để chẩn đoán lỗi không tìm thấy câu hỏi.
# ĐÃ SỬA: Tối ưu hóa cách lấy all_accessible_quiz_set_ids để đảm bảo tính chính xác và mạnh mẽ hơn.

from ....models import db, LearningItem, UserProgress, LearningContainer, ContainerContributor
from flask_login import current_user
from sqlalchemy import func, and_, not_, or_ # Import or_
import random
from flask import current_app # Import current_app để dùng logger (dự phòng)

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
    # Nếu session_size là None, lấy tất cả để đếm
    if session_size is None or session_size == 999999: # 999999 là giá trị lớn để lấy tất cả
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

