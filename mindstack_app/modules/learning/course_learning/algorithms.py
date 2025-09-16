# mindstack_app/modules/learning/course_learning/algorithms.py
# Phiên bản: 1.2
# MỤC ĐÍCH: Khắc phục lỗi không hiển thị khoá học ở tab "Đang học".
# ĐÃ SỬA: Thay đổi logic lọc của tab 'doing' để hiển thị tất cả các khoá học đã tương tác
#         (có bản ghi trong UserContainerState) và chưa bị archive.

from ....models import db, LearningItem, CourseProgress, LearningContainer, ContainerContributor, UserContainerState
from flask_login import current_user
from sqlalchemy import func, and_, not_, or_
from flask import current_app
from ....modules.shared.utils.pagination import get_pagination_data
from ....modules.shared.utils.search import apply_search_filter

def get_filtered_course_sets(user_id, search_query, search_field, current_filter, page, per_page=12):
    """
    Lấy danh sách các Khoá học đã được lọc và phân trang dựa trên các tiêu chí.
    Bao gồm tính toán tiến độ hoàn thành và tổng thời gian dự tính.
    """
    print(f">>> ALGORITHMS: Bắt đầu get_filtered_course_sets cho user_id={user_id}, filter={current_filter} <<<")

    base_query = LearningContainer.query.filter_by(container_type='COURSE')
    
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
        # ĐÃ SỬA: Lấy tất cả các khoá học đã tương tác và chưa bị archive
        final_query = filtered_query.join(UserContainerState,
            and_(UserContainerState.container_id == LearningContainer.container_id, UserContainerState.user_id == user_id)
        ).filter(
            UserContainerState.is_archived == False
        ).order_by(UserContainerState.last_accessed.desc())
        
    elif current_filter == 'explore':
        final_query = filtered_query.filter(
            ~LearningContainer.container_id.in_(user_interacted_ids_subquery)
        ).order_by(LearningContainer.created_at.desc())
    else: # Mặc định là 'all', bao gồm cả 'doing' và 'explore'
        final_query = filtered_query.outerjoin(UserContainerState,
            and_(UserContainerState.container_id == LearningContainer.container_id, UserContainerState.user_id == user_id)
        ).filter(
            or_(UserContainerState.is_archived == False, UserContainerState.is_archived == None)
        ).order_by(LearningContainer.created_at.desc())

    # Phân trang
    pagination = get_pagination_data(final_query, page, per_page=per_page)
    
    # Bổ sung thông tin tiến độ và tổng thời gian
    for set_item in pagination.items:
        # Lấy tất cả các bài học thuộc khoá học
        lessons = LearningItem.query.filter_by(container_id=set_item.container_id, item_type='LESSON').all()
        total_lessons = len(lessons)
        
        total_completion_percentage = 0
        total_estimated_time = 0
        
        if total_lessons > 0:
            lesson_ids = [lesson.item_id for lesson in lessons]
            
            # Tính tổng % hoàn thành
            progress_records = CourseProgress.query.filter(
                CourseProgress.user_id == user_id,
                CourseProgress.item_id.in_(lesson_ids)
            ).all()
            
            for progress in progress_records:
                total_completion_percentage += progress.completion_percentage
            
            # Tính tổng thời gian dự tính
            for lesson in lessons:
                if lesson.content and 'estimated_time' in lesson.content and lesson.content['estimated_time']:
                    try:
                        total_estimated_time += int(lesson.content['estimated_time'])
                    except (ValueError, TypeError):
                        pass # Bỏ qua nếu giá trị không hợp lệ

        set_item.total_lessons = total_lessons
        set_item.overall_completion_percentage = (total_completion_percentage / total_lessons) if total_lessons > 0 else 0
        set_item.total_estimated_time = total_estimated_time # Tổng thời gian tính bằng phút

        # Lấy trạng thái archive và favorite
        user_state = UserContainerState.query.filter_by(
            user_id=user_id,
            container_id=set_item.container_id
        ).first()
        set_item.user_state = user_state.to_dict() if user_state else {'is_archived': False, 'is_favorite': False}

    print(f">>> ALGORITHMS: Kết thúc get_filtered_course_sets. Tổng số khoá học: {pagination.total} <<<")
    return pagination

def get_lessons_for_course(user_id, course_id):
    """
    Lấy danh sách các bài học cho một khoá học cụ thể, kèm theo tiến độ của người dùng.
    """
    lessons = LearningItem.query.filter_by(
        container_id=course_id, 
        item_type='LESSON'
    ).order_by(LearningItem.order_in_container).all()

    lesson_ids = [lesson.item_id for lesson in lessons]
    
    progress_map = {
        p.item_id: p.completion_percentage 
        for p in CourseProgress.query.filter(
            CourseProgress.user_id == user_id,
            CourseProgress.item_id.in_(lesson_ids)
        )
    }

    for lesson in lessons:
        lesson.completion_percentage = progress_map.get(lesson.item_id, 0)

    return lessons

