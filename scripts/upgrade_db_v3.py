
import sys
import os

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from flask import Flask
from sqlalchemy import text, inspect
from mindstack_app import create_app, db
from mindstack_app.models import User, UserSession, LearningItem

def upgrade_database_v3():
    app = create_app()
    with app.app_context():
        inspector = inspect(db.engine)
        
        print("=== BẮT ĐẦU NÂNG CẤP CƠ SỞ DỮ LIỆU V3 ===")
        print("Mục tiêu: Tạo Index tìm kiếm & Tách bảng UserSession.")

        # 1. TẠO INDEX CHO SEARCH_TEXT
        # ---------------------------------------------------------
        print("\n[1/3] Tạo Index cho cột search_text...")
        indexes = [i['name'] for i in inspector.get_indexes('learning_items')]
        if 'ix_learning_items_search_text' not in indexes:
            # Tạo index thủ công bằng SQL raw để đảm bảo tương thích
            try:
                with db.engine.connect() as conn:
                    conn.execute(text("CREATE INDEX ix_learning_items_search_text ON learning_items (search_text)"))
                    conn.commit()
                print(" -> Đã tạo Index thành công.")
            except Exception as e:
                print(f" -> Lỗi khi tạo Index (có thể đã tồn tại): {e}")
        else:
            print(" -> Index đã tồn tại.")

        # 2. TẠO BẢNG USER_SESSION
        # ---------------------------------------------------------
        print("\n[2/3] Tạo bảng UserSession...")
        if not inspector.has_table('user_sessions'):
            UserSession.__table__.create(db.engine)
            print(" -> Đã tạo bảng 'user_sessions'.")
        else:
            print(" -> Bảng 'user_sessions' đã tồn tại.")

        # 3. MIGRATE DỮ LIỆU TỪ USER -> USER_SESSION
        # ---------------------------------------------------------
        print("\n[3/3] Di chuyển dữ liệu Session...")
        users = User.query.all()
        migrated_count = 0
        
        for user in users:
            # Kiểm tra xem user này đã có session chưa
            if UserSession.query.get(user.user_id):
                continue
            
            # Tạo session mới từ dữ liệu cũ trong bảng User
            new_session = UserSession(
                user_id=user.user_id,
                current_flashcard_container_id=user.current_flashcard_container_id,
                current_quiz_container_id=user.current_quiz_container_id,
                current_course_container_id=user.current_course_container_id,
                current_flashcard_mode=user.current_flashcard_mode or 'basic',
                current_quiz_mode=user.current_quiz_mode or 'standard',
                current_quiz_batch_size=user.current_quiz_batch_size or 10,
                flashcard_button_count=user.flashcard_button_count or 3
            )
            db.session.add(new_session)
            migrated_count += 1
            
            if migrated_count % 50 == 0:
                print(f" -> Đã di chuyển {migrated_count} người dùng...")

        db.session.commit()
        print(f" -> Hoàn tất di chuyển session cho {migrated_count} người dùng.")
        print("\n=== NÂNG CẤP V3 HOÀN TẤT ===")
        print("LƯU Ý: Code Python cũ vẫn đang đọc cột cũ từ bảng User.")
        print("Bạn cần cập nhật code (Routes/Services) để sử dụng 'user.session_state.current_...' thay vì 'user.current_...' trong tương lai.")

if __name__ == '__main__':
    upgrade_database_v3()
