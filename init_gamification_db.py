from mindstack_app import create_app, db
from mindstack_app.modules.gamification.models import Badge

app = create_app()

def init_db():
    with app.app_context():
        print("Đang kết nối database...")
        # Tạo các bảng mới (nếu chưa có)
        db.create_all()
        print("Đã cập nhật cấu trúc bảng (badges, user_badges).")
        
        # Seed data
        print("Đang kiểm tra dữ liệu mẫu...")
        if not Badge.query.first():
            print("Chưa có huy hiệu. Đang khởi tạo dữ liệu mẫu...")
            defaults = [
                {
                    'name': 'Người khởi đầu', 
                    'desc': 'Đạt được 100 điểm đầu tiên trong hành trình.', 
                    'icon': 'fas fa-star', 
                    'type': 'TOTAL_SCORE', 
                    'val': 100, 
                    'pts': 50,
                    'is_active': True
                },
                {
                    'name': 'Chiến binh Kiên trì', 
                    'desc': 'Học tập liên tiếp trong 3 ngày.', 
                    'icon': 'fas fa-fire', 
                    'type': 'STREAK', 
                    'val': 3, 
                    'pts': 100,
                    'is_active': True
                },
                {
                    'name': 'Tuần lễ Vàng', 
                    'desc': 'Giữ chuỗi học tập liên tục 7 ngày.', 
                    'icon': 'fas fa-fire-alt', 
                    'type': 'STREAK', 
                    'val': 7, 
                    'pts': 300,
                    'is_active': True
                },
                {
                    'name': 'Bậc thầy Tri thức', 
                    'desc': 'Chạm mốc 1000 điểm tổng tích lũy.', 
                    'icon': 'fas fa-crown', 
                    'type': 'TOTAL_SCORE', 
                    'val': 1000, 
                    'pts': 500,
                    'is_active': True
                },
                {
                    'name': 'Học giả Chăm chỉ', 
                    'desc': 'Hoàn thành 50 Flashcard.', 
                    'icon': 'fas fa-book-reader', 
                    'type': 'FLASHCARD_COUNT', 
                    'val': 50, 
                    'pts': 200,
                    'is_active': True
                },
            ]
            
            for d in defaults:
                b = Badge(
                    name=d['name'], 
                    description=d['desc'], 
                    icon_class=d['icon'],
                    condition_type=d['type'], 
                    condition_value=d['val'], 
                    reward_points=d['pts'],
                    is_active=d['is_active']
                )
                db.session.add(b)
            
            db.session.commit()
            print(f"Đã thêm thành công {len(defaults)} huy hiệu mẫu.")
        else:
            print("Dữ liệu huy hiệu đã tồn tại. Bỏ qua bước khởi tạo.")
            
        print("Hoàn tất! Bạn có thể truy cập Admin Panel để kiểm tra.")

if __name__ == '__main__':
    init_db()
