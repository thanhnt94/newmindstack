# File: web/mindstack_app/models.py
# Mục đích: Định nghĩa cấu trúc database (phiên bản v11) dưới dạng các lớp Python,
#           đã thêm các trường theo dõi tiến độ học tập hiện tại của người dùng
#           và các trường liên quan đến AI cho LearningContainer và LearningItem.

from .db_instance import db
from sqlalchemy.sql import func
from sqlalchemy.types import JSON
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

# ==============================================================================
# I. LÕI HỌC TẬP (LEARNING CORE)
# ==============================================================================

class LearningContainer(db.Model):
    __tablename__ = 'learning_containers'
    container_id = db.Column(db.Integer, primary_key=True)
    creator_user_id = db.Column(db.Integer, db.ForeignKey('users.user_id'), nullable=False)
    container_type = db.Column(db.String(50), nullable=False) # 'COURSE', 'FLASHCARD_SET', 'QUIZ_SET'
    title = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text)
    tags = db.Column(db.String(255))
    is_public = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), server_default=func.now())
    updated_at = db.Column(db.DateTime(timezone=True), onupdate=func.now())
    ai_settings = db.Column(JSON, nullable=True) # TRƯỜNG MỚI: Lưu cài đặt AI cho bộ thẻ/quiz/course

class LearningGroup(db.Model):
    __tablename__ = 'learning_groups'
    group_id = db.Column(db.Integer, primary_key=True)
    container_id = db.Column(db.Integer, db.ForeignKey('learning_containers.container_id'), nullable=False)
    group_type = db.Column(db.String(50), nullable=False) # 'PASSAGE', 'AUDIO'
    content = db.Column(JSON, nullable=False) # Chứa đoạn văn hoặc link audio

class LearningItem(db.Model):
    __tablename__ = 'learning_items'
    item_id = db.Column(db.Integer, primary_key=True)
    container_id = db.Column(db.Integer, db.ForeignKey('learning_containers.container_id'), nullable=False)
    group_id = db.Column(db.Integer, db.ForeignKey('learning_groups.group_id'), nullable=True)
    item_type = db.Column(db.String(50), nullable=False) # 'LESSON', 'FLASHCARD', 'QUIZ_MCQ', 'QUIZ_COMPOUND'
    content = db.Column(JSON, nullable=False)
    order_in_container = db.Column(db.Integer, default=0)
    ai_explanation = db.Column(db.Text, nullable=True) # TRƯỜNG MỚI: Nội dung giải thích do AI tạo ra

# ==============================================================================
# II. NGƯỜI DÙNG & TƯƠNG TÁC (USER & INTERACTION)
# ==============================================================================

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    user_id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    user_role = db.Column(db.String(50), default='user', nullable=False) # 'user', 'admin'
    total_score = db.Column(db.Integer, default=0)
    last_seen = db.Column(db.DateTime(timezone=True))

    # CÁC TRƯỜNG MỚI ĐỂ LƯU TIẾN ĐỘ HỌC HIỆN TẠI
    current_flashcard_container_id = db.Column(db.Integer, db.ForeignKey('learning_containers.container_id'), nullable=True)
    current_quiz_container_id = db.Column(db.Integer, db.ForeignKey('learning_containers.container_id'), nullable=True)
    current_course_container_id = db.Column(db.Integer, db.ForeignKey('learning_containers.container_id'), nullable=True)
    current_flashcard_mode = db.Column(db.String(50), nullable=True)
    current_quiz_mode = db.Column(db.String(50), nullable=True)
    
    def get_id(self):
        return str(self.user_id)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class UserProgress(db.Model):
    __tablename__ = 'user_progress'
    progress_id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.user_id'), nullable=False)
    item_id = db.Column(db.Integer, db.ForeignKey('learning_items.item_id'), nullable=False)
    due_time = db.Column(db.DateTime(timezone=True))
    memory_score = db.Column(db.Float, default=0)
    last_reviewed = db.Column(db.DateTime(timezone=True))
    correct_streak = db.Column(db.Integer, default=0)
    incorrect_streak = db.Column(db.Integer, default=0)
    vague_streak = db.Column(db.Integer, default=0)
    status = db.Column(db.String(50), default='new') # 'new', 'learning', 'mastered'
    times_correct = db.Column(db.Integer, default=0)
    times_incorrect = db.Column(db.Integer, default=0)
    times_vague = db.Column(db.Integer, default=0)
    first_seen_timestamp = db.Column(db.DateTime(timezone=True))
    review_history = db.Column(JSON)
    __table_args__ = (db.UniqueConstraint('user_id', 'item_id', name='_user_item_uc'),)

class ScoreLog(db.Model):
    __tablename__ = 'score_logs'
    log_id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.user_id'), nullable=False)
    item_id = db.Column(db.Integer, db.ForeignKey('learning_items.item_id'), nullable=True)
    score_change = db.Column(db.Integer, nullable=False)
    reason = db.Column(db.String(100))
    timestamp = db.Column(db.DateTime(timezone=True), server_default=func.now())

class UserNote(db.Model):
    __tablename__ = 'user_notes'
    note_id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.user_id'), nullable=False)
    item_id = db.Column(db.Integer, db.ForeignKey('learning_items.item_id'), nullable=False)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), server_default=func.now())

class UserFeedback(db.Model):
    __tablename__ = 'user_feedback'
    feedback_id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.user_id'), nullable=False)
    item_id = db.Column(db.Integer, db.ForeignKey('learning_items.item_id'), nullable=False)
    content = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(50), default='new') # 'new', 'resolved', 'wont_fix'
    timestamp = db.Column(db.DateTime(timezone=True), server_default=func.now())

# ==============================================================================
# III. HỆ THỐNG & QUẢN TRỊ (SYSTEM & ADMIN)
# ==============================================================================

class SystemSetting(db.Model):
    __tablename__ = 'system_settings'
    setting_id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(100), unique=True, nullable=False)
    value = db.Column(JSON, nullable=False)
    description = db.Column(db.Text)

class BackgroundTask(db.Model):
    __tablename__ = 'background_tasks'
    task_id = db.Column(db.Integer, primary_key=True)
    task_name = db.Column(db.String(100), unique=True, nullable=False)
    status = db.Column(db.String(50), default='idle') # 'idle', 'running', 'error', 'completed'
    progress = db.Column(db.Integer, default=0)
    total = db.Column(db.Integer, default=0)
    message = db.Column(db.Text)
    stop_requested = db.Column(db.Boolean, default=False)
    is_enabled = db.Column(db.Boolean, default=False)
    last_updated = db.Column(db.DateTime(timezone=True), onupdate=func.now())
    
class ApiKey(db.Model):
    __tablename__ = 'api_keys'
    key_id = db.Column(db.Integer, primary_key=True)
    key_value = db.Column(db.String(255), unique=True, nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    is_exhausted = db.Column(db.Boolean, default=False)
    last_used_timestamp = db.Column(db.DateTime(timezone=True))
    notes = db.Column(db.Text)
