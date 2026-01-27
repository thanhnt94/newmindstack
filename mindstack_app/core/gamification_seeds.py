from mindstack_app.models.gamification import Badge
from mindstack_app.extensions import db

def seed_badges():
    """Khởi tạo dữ liệu mẫu cho hệ thống huy hiệu."""
    badges_data = [
        # --- STREAK BADGES ---
        {
            "name": "Khởi đầu nan",
            "description": "Duy trì chuỗi học tập 3 ngày liên tiếp",
            "icon_class": "fas fa-seedling",
            "condition_type": Badge.TYPE_STREAK,
            "condition_value": 3,
            "reward_points": 50
        },
        {
            "name": "Thói quen hình thành",
            "description": "Duy trì chuỗi học tập 7 ngày liên tiếp",
            "icon_class": "fas fa-leaf",
            "condition_type": Badge.TYPE_STREAK,
            "condition_value": 7,
            "reward_points": 200
        },
        {
            "name": "Kỷ luật thép",
            "description": "Duy trì chuỗi học tập 30 ngày liên tiếp",
            "icon_class": "fas fa-fire",
            "condition_type": Badge.TYPE_STREAK,
            "condition_value": 30,
            "reward_points": 1000
        },
        {
            "name": "Học giả bền bỉ",
            "description": "Duy trì chuỗi học tập 100 ngày liên tiếp",
            "icon_class": "fas fa-mountain",
            "condition_type": Badge.TYPE_STREAK,
            "condition_value": 100,
            "reward_points": 5000
        },
        {
            "name": "Huyền thoại sống",
            "description": "Duy trì chuỗi học tập 365 ngày liên tiếp",
            "icon_class": "fas fa-crown",
            "condition_type": Badge.TYPE_STREAK,
            "condition_value": 365,
            "reward_points": 20000
        },

        # --- SCORE BADGES ---
        {
            "name": "Bước chân đầu tiên",
            "description": "Đạt tổng số điểm 100",
            "icon_class": "fas fa-walking",
            "condition_type": Badge.TYPE_TOTAL_SCORE,
            "condition_value": 100,
            "reward_points": 20
        },
        {
            "name": "Nhà thám hiểm trí tuệ",
            "description": "Đạt tổng số điểm 1,000",
            "icon_class": "fas fa-compass",
            "condition_type": Badge.TYPE_TOTAL_SCORE,
            "condition_value": 1000,
            "reward_points": 100
        },
        {
            "name": "Triệu phú điểm số",
            "description": "Đạt tổng số điểm 10,000",
            "icon_class": "fas fa-coins",
            "condition_type": Badge.TYPE_TOTAL_SCORE,
            "condition_value": 10000,
            "reward_points": 500
        },
        {
            "name": "Đỉnh cao tri thức",
            "description": "Đạt tổng số điểm 50,000",
            "icon_class": "fas fa-trophy",
            "condition_type": Badge.TYPE_TOTAL_SCORE,
            "condition_value": 50000,
            "reward_points": 2000
        },
        {
            "name": "Vị thần MindStack",
            "description": "Đạt tổng số điểm 100,000",
            "icon_class": "fas fa-bolt",
            "condition_type": Badge.TYPE_TOTAL_SCORE,
            "condition_value": 100000,
            "reward_points": 10000
        },

        # --- FLASHCARD BADGES ---
        {
            "name": "Lật thẻ làm quen",
            "description": "Học được 50 thẻ Flashcard khác nhau",
            "icon_class": "fas fa-clone",
            "condition_type": Badge.TYPE_FLASHCARD_COUNT,
            "condition_value": 50,
            "reward_points": 50
        },
        {
            "name": "Bậc thầy ghi nhớ",
            "description": "Học được 500 thẻ Flashcard",
            "icon_class": "fas fa-brain",
            "condition_type": Badge.TYPE_FLASHCARD_COUNT,
            "condition_value": 500,
            "reward_points": 300
        },
        {
            "name": "Kho tàng ngôn ngữ",
            "description": "Học được 2,000 thẻ Flashcard",
            "icon_class": "fas fa-book",
            "condition_type": Badge.TYPE_FLASHCARD_COUNT,
            "condition_value": 2000,
            "reward_points": 1500
        },
        {
            "name": "Tinh anh lật thẻ",
            "description": "Học được 5,000 thẻ Flashcard",
            "icon_class": "fas fa-star",
            "condition_type": Badge.TYPE_FLASHCARD_COUNT,
            "condition_value": 5000,
            "reward_points": 4000
        },
        {
            "name": "Siêu nhân Flashcard",
            "description": "Học được 10,000 thẻ Flashcard",
            "icon_class": "fas fa-rocket",
            "condition_type": Badge.TYPE_FLASHCARD_COUNT,
            "condition_value": 10000,
            "reward_points": 10000
        },

        # --- QUIZ BADGES ---
        {
            "name": "Giải mã thử thách",
            "description": "Hoàn thành 10 lượt Quiz",
            "icon_class": "fas fa-puzzle-piece",
            "condition_type": Badge.TYPE_QUIZ_COUNT,
            "condition_value": 10,
            "reward_points": 50
        },
        {
            "name": "Chiến binh trắc nghiệm",
            "description": "Hoàn thành 100 lượt Quiz",
            "icon_class": "fas fa-fist-raised",
            "condition_type": Badge.TYPE_QUIZ_COUNT,
            "condition_value": 100,
            "reward_points": 500
        },
        {
            "name": "Bách phát bách trúng",
            "description": "Hoàn thành 500 lượt Quiz",
            "icon_class": "fas fa-bullseye",
            "condition_type": Badge.TYPE_QUIZ_COUNT,
            "condition_value": 500,
            "reward_points": 2500
        },
        {
            "name": "Giáo sư Quiz",
            "description": "Hoàn thành 1,000 lượt Quiz",
            "icon_class": "fas fa-graduation-cap",
            "condition_type": Badge.TYPE_QUIZ_COUNT,
            "condition_value": 1000,
            "reward_points": 6000
        },
        {
            "name": "Vua vĩ đại",
            "description": "Hoàn thành 5,000 lượt Quiz",
            "icon_class": "fas fa-gem",
            "condition_type": Badge.TYPE_QUIZ_COUNT,
            "condition_value": 5000,
            "reward_points": 30000
        }
    ]

    added_count = 0
    for data in badges_data:
        # Kiểm tra xem badge đã tồn tại chưa (dựa trên tên hoặc loại + giá trị)
        existing = Badge.query.filter_by(name=data['name']).first()
        if not existing:
            badge = Badge(**data)
            db.session.add(badge)
            added_count += 1
    
    if added_count > 0:
        db.session.commit()
    
    return added_count
