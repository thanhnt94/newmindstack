
import os
import sys

# Thêm đường dẫn để import được mindstack_app
sys.path.append(os.getcwd())

from start_mindstack_app import app
from mindstack_app.models import db, StudyLog
# Import LearningProgress từ đúng module của nó
from mindstack_app.modules.learning.models import LearningProgress

def cap_durations():
    MAX_DURATION_MS = 60000  # 60 seconds
    
    with app.app_context():
        print("--- Đang bắt đầu cập nhật giới hạn thời gian (max 60s) ---")
        
        # 1. Cập nhật bảng StudyLog
        study_logs_to_fix = StudyLog.query.filter(StudyLog.review_duration > MAX_DURATION_MS).all()
        count_study = len(study_logs_to_fix)
        if count_study > 0:
            print(f"Phát hiện {count_study} bản ghi trong StudyLog vượt quá 60s.")
            for log in study_logs_to_fix:
                log.review_duration = MAX_DURATION_MS
            print(f"Đã sửa {count_study} bản ghi StudyLog.")
        else:
            print("Không có bản ghi StudyLog nào vượt quá 60s.")
            
        # 2. Cập nhật bảng LearningProgress
        progress_to_fix = LearningProgress.query.filter(LearningProgress.last_review_duration > MAX_DURATION_MS).all()
        count_progress = len(progress_to_fix)
        if count_progress > 0:
            print(f"Phát hiện {count_progress} bản ghi trong LearningProgress vượt quá 60s.")
            for p in progress_to_fix:
                p.last_review_duration = MAX_DURATION_MS
            print(f"Đã sửa {count_progress} bản ghi LearningProgress.")
        else:
            print("Không có bản ghi LearningProgress nào vượt quá 60s.")
            
        if count_study > 0 or count_progress > 0:
            db.session.commit()
            print("--- Đã lưu thay đổi vào cơ sở dữ liệu ---")
        else:
            print("--- Không có gì cần thay đổi ---")

if __name__ == "__main__":
    cap_durations()
