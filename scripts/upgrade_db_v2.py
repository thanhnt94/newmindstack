
import sys
import os
from datetime import datetime

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from flask import Flask
from sqlalchemy import text, inspect
from mindstack_app import create_app, db
from mindstack_app.models import LearningItem, FlashcardProgress, ReviewLog

def upgrade_database():
    app = create_app()
    with app.app_context():
        inspector = inspect(db.engine)
        
        print("=== BẮT ĐẦU NÂNG CẤP CƠ SỞ DỮ LIỆU V2 ===")

        # 1. SCHEMA MIGRATION
        # ---------------------------------------------------------
        print("\n[1/4] Kiểm tra và cập nhật Schema...")
        
        # A. Tạo bảng ReviewLog nếu chưa có
        if not inspector.has_table('review_logs'):
            print(" -> Đang tạo bảng 'review_logs'...")
            ReviewLog.__table__.create(db.engine)
        else:
            print(" -> Bảng 'review_logs' đã tồn tại.")

        # B. Thêm cột search_text vào learning_items nếu chưa có
        columns = [c['name'] for c in inspector.get_columns('learning_items')]
        if 'search_text' not in columns:
            print(" -> Đang thêm cột 'search_text' vào bảng 'learning_items'...")
            with db.engine.connect() as conn:
                # Sử dụng ALTER TABLE của SQLite/Postgres (tương thích cơ bản)
                conn.execute(text("ALTER TABLE learning_items ADD COLUMN search_text TEXT"))
                conn.commit()
        else:
            print(" -> Cột 'search_text' đã tồn tại.")

        # 2. DATA MIGRATION: SEARCH TEXT
        # ---------------------------------------------------------
        print("\n[2/4] Tạo dữ liệu tìm kiếm (Search Text)...")
        items = LearningItem.query.all()
        count = 0
        for item in items:
            # Gọi phương thức helper đã viết trong Model
            item.update_search_text()
            count += 1
            if count % 100 == 0:
                print(f" -> Đã xử lý {count} mục...")
        
        db.session.commit()
        print(f" -> Hoàn tất cập nhật search_text cho {count} mục.")

        # 3. DATA MIGRATION: REVIEW HISTORY
        # ---------------------------------------------------------
        print("\n[3/4] Di chuyển lịch sử ôn tập sang bảng ReviewLog...")
        progress_records = FlashcardProgress.query.filter(FlashcardProgress.review_history.isnot(None)).all()
        
        log_count = 0
        for record in progress_records:
            history = record.review_history
            if not isinstance(history, list):
                continue
            
            for entry in history:
                # Giả định cấu trúc JSON cũ: {'timestamp': 'ISO...', 'rating': int, ...}
                # Cần try-catch để tránh lỗi dữ liệu bẩn
                try:
                    ts_str = entry.get('timestamp')
                    rating = entry.get('rating', 0)
                    
                    if ts_str:
                        try:
                            ts = datetime.fromisoformat(ts_str)
                        except ValueError:
                            ts = datetime.now()
                    else:
                        ts = datetime.now()

                    new_log = ReviewLog(
                        user_id=record.user_id,
                        item_id=record.item_id,
                        timestamp=ts,
                        rating=rating,
                        duration_ms=entry.get('duration', 0),
                        review_type='flashcard'
                    )
                    db.session.add(new_log)
                    log_count += 1
                except Exception as e:
                    print(f" [Warn] Bỏ qua 1 log lỗi của user {record.user_id}: {e}")

        db.session.commit()
        print(f" -> Đã chuyển đổi thành công {log_count} bản ghi lịch sử ôn tập.")

        print("\n=== NÂNG CẤP HOÀN TẤT ===")

if __name__ == '__main__':
    upgrade_database()
