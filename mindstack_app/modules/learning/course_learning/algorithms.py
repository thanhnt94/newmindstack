# mindstack_app/modules/learning/course_learning/algorithms.py
# Phiên bản: 2.2
# MỤC ĐÍCH: Sửa lỗi logic hiển thị các khóa học ở tab 'Đang học' và 'Khám phá'.
# ĐÃ SỬA: Thay đổi logic lọc để dựa vào sự tồn tại của UserContainerState để phân loại.

from ....models import (
    db,
    LearningItem,
    CourseProgress,
    LearningContainer,
    ContainerContributor,
    UserContainerState,
    User,
)
from flask_login import current_user
from sqlalchemy import func, and_, not_, or_
from flask import current_app
from ...shared.utils.pagination import get_pagination_data
from ...shared.utils.search import apply_search_filter

def get_filtered_course_sets(user_id, search_query, search_field, current_filter, page, per_page=12):
    """
    Mô tả: Lấy danh sách các Khoá học đã được lọc và phân trang dựa trên các tiêu chí.
    Đã sửa lại logic để hiển thị chính xác các khóa học cho từng tab.
    """
    print(f">>> ALGORITHMS: Bắt đầu get_filtered_course_sets cho user_id={user_id}, filter={current_filter} <<<")

    base_query = LearningContainer.query.filter_by(container_type='COURSE')

    # Lọc quyền truy cập
    if current_user.user_role == User.ROLE_ADMIN:
        pass
    elif current_user.user_role == User.ROLE_FREE:
        base_query = base_query.filter(LearningContainer.creator_user_id == user_id)
    else:
        access_conditions = [
            LearningContainer.creator_user_id == user_id,
            LearningContainer.is_public == True
        ]

        # Hoặc các khóa học họ được mời làm cộng tác viên
        contributed_sets_ids = db.session.query(ContainerContributor.container_id).filter(
            ContainerContributor.user_id == user_id
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

    # Truy vấn con: Lấy ID của các khóa học mà người dùng đã tương tác (có bản ghi trong UserContainerState)
    user_interacted_ids_subquery = db.session.query(UserContainerState.container_id).filter(
        UserContainerState.user_id == user_id
    ).subquery()
    
    if current_filter == 'archive':
        # Tab LƯU TRỮ: chỉ lấy các khóa học có trong danh sách lưu trữ
        final_query = filtered_query.join(UserContainerState,
            and_(UserContainerState.container_id == LearningContainer.container_id, UserContainerState.user_id == user_id)
        ).filter(
            UserContainerState.is_archived == True
        )
    elif current_filter == 'doing':
        # SỬA: Lấy các khóa học mà người dùng ĐÃ TƯƠNG TÁC và KHÔNG bị lưu trữ
        final_query = filtered_query.join(UserContainerState,
            and_(UserContainerState.container_id == LearningContainer.container_id, UserContainerState.user_id == user_id)
        ).filter(
            UserContainerState.is_archived == False
        )
    elif current_filter == 'explore':
        # SỬA LỖI: Lấy các khóa học CHƯA TỪNG được tương tác
        final_query = filtered_query.filter(
            ~LearningContainer.container_id.in_(user_interacted_ids_subquery)
        )
    else: # Mặc định là 'all' hoặc các trường hợp khác
        # Lấy tất cả các khóa học không bị lưu trữ
        final_query = filtered_query.outerjoin(UserContainerState,
            and_(UserContainerState.container_id == LearningContainer.container_id, UserContainerState.user_id == user_id)
        ).filter(
            or_(UserContainerState.is_archived == False, UserContainerState.is_archived == None)
        )

    # Sắp xếp theo ngày tạo mới nhất
    final_query = final_query.order_by(LearningContainer.created_at.desc())

    # Phân trang
    pagination = get_pagination_data(final_query, page, per_page=per_page)
    
    # Bổ sung thông tin tiến độ và các thông tin khác
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
                        pass

        set_item.total_lessons = total_lessons
        set_item.overall_completion_percentage = (total_completion_percentage / total_lessons) if total_lessons > 0 else 0
        set_item.total_estimated_time = total_estimated_time

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
    Mô tả: Lấy danh sách các bài học cho một khoá học cụ thể, kèm theo tiến độ của người dùng.
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
