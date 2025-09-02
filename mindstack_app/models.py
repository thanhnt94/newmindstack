# File: web/mindstack_app/models.py
# Phiên bản: 12.4
# ĐÃ SỬA: Thêm phương thức to_dict() vào UserContainerState để khắc phục lỗi AttributeError.
# ĐÃ SỬA: Xóa cột memory_score và thêm các cột easiness_factor, repetitions, interval
#         để hỗ trợ thuật toán lặp lại ngắt quãng SuperMemo-2 (SM-2) cho Flashcard.

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
    ai_settings = db.Column(JSON, nullable=True)

    # Mối quan hệ với User để dễ dàng truy cập thông tin người tạo
    # SỬA: Thêm foreign_keys=[creator_user_id] để chỉ định rõ ràng cột khóa ngoại
    creator = db.relationship('User', backref='created_containers', foreign_keys=[creator_user_id], lazy=True)
    contributors = db.relationship('ContainerContributor', backref='container', lazy=True, cascade="all, delete-orphan")


class LearningGroup(db.Model):
    __tablename__ = 'learning_groups'
    group_id = db.Column(db.Integer, primary_key=True)
    container_id = db.Column(db.Integer, db.ForeignKey('learning_containers.container_id'), nullable=False)
    group_type = db.Column(db.String(50), nullable=False) # 'PASSAGE', 'AUDIO'
    content = db.Column(JSON, nullable=False)

class LearningItem(db.Model):
    __tablename__ = 'learning_items'
    item_id = db.Column(db.Integer, primary_key=True)
    container_id = db.Column(db.Integer, db.ForeignKey('learning_containers.container_id'), nullable=False)
    group_id = db.Column(db.Integer, db.ForeignKey('learning_groups.group_id'), nullable=True)
    item_type = db.Column(db.String(50), nullable=False) # 'LESSON', 'FLASHCARD', 'QUIZ_MCQ', 'QUIZ_COMPOUND'
    content = db.Column(JSON, nullable=False)
    order_in_container = db.Column(db.Integer, default=0)
    ai_explanation = db.Column(db.Text, nullable=True)

# ==============================================================================
# II. NGƯỜI DÙNG & TƯƠNG TÁC (USER & INTERACTION)
# ==============================================================================

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    user_id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    user_role = db.Column(db.String(50), default='user', nullable=False) # 'user', 'admin'
    total_score = db.Column(db.Integer, default=0)
    last_seen = db.Column(db.DateTime(timezone=True))

    current_flashcard_container_id = db.Column(db.Integer, db.ForeignKey('learning_containers.container_id'), nullable=True)
    current_quiz_container_id = db.Column(db.Integer, db.ForeignKey('learning_containers.container_id'), nullable=True)
    current_course_container_id = db.Column(db.Integer, db.ForeignKey('learning_containers.container_id'), nullable=True)
    current_flashcard_mode = db.Column(db.String(50), nullable=True)
    current_quiz_mode = db.Column(db.String(50), nullable=True)
    current_quiz_batch_size = db.Column(db.Integer, nullable=True)
    flashcard_button_count = db.Column(db.Integer, default=3) # THÊM MỚI: Cài đặt số nút đánh giá cho Flashcard

    contributed_containers = db.relationship('ContainerContributor', backref='user', lazy=True)
    # THÊM MỚI: Mối quan hệ với UserContainerState
    container_states = db.relationship('UserContainerState', backref='user', lazy=True, cascade="all, delete-orphan")


    def get_id(self):
        return str(self.user_id)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

# THÊM MỚI: Model UserContainerState để lưu trữ các trạng thái cá nhân hóa của người dùng đối với các bộ học liệu
class UserContainerState(db.Model):
    __tablename__ = 'user_container_states'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.user_id'), nullable=False)
    container_id = db.Column(db.Integer, db.ForeignKey('learning_containers.container_id'), nullable=False)
    
    # Các trường trạng thái đa năng
    is_archived = db.Column(db.Boolean, default=False, nullable=False)
    is_favorite = db.Column(db.Boolean, default=False, nullable=False) # Ví dụ: Đánh dấu yêu thích
    last_accessed = db.Column(db.DateTime(timezone=True), server_default=func.now(), onupdate=func.now()) # Lần cuối truy cập

    # Mối quan hệ với LearningContainer
    container = db.relationship('LearningContainer', backref='user_states', lazy=True)

    __table_args__ = (db.UniqueConstraint('user_id', 'container_id', name='_user_container_uc'),)

    # THÊM MỚI: Phương thức to_dict() để trả về một dictionary
    def to_dict(self):
        return {
            'is_archived': self.is_archived,
            'is_favorite': self.is_favorite,
            'last_accessed': self.last_accessed.isoformat() if self.last_accessed else None
        }

class UserProgress(db.Model):
    __tablename__ = 'user_progress'
    progress_id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.user_id'), nullable=False)
    item_id = db.Column(db.Integer, db.ForeignKey('learning_items.item_id'), nullable=False)
    due_time = db.Column(db.DateTime(timezone=True))
    easiness_factor = db.Column(db.Float, default=2.5) # THÊM MỚI: Hệ số dễ
    repetitions = db.Column(db.Integer, default=0)       # THÊM MỚI: Số lần lặp lại
    interval = db.Column(db.Integer, default=0)          # THÊM MỚI: Khoảng thời gian ôn tập
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

class ContainerContributor(db.Model):
    __tablename__ = 'container_contributors'
    contributor_id = db.Column(db.Integer, primary_key=True)
    container_id = db.Column(db.Integer, db.ForeignKey('learning_containers.container_id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.user_id'), nullable=False)
    permission_level = db.Column(db.String(50), nullable=False) # ví dụ: 'editor', 'viewer', 'admin'
    granted_at = db.Column(db.DateTime(timezone=True), server_default=func.now())
    __table_args__ = (db.UniqueConstraint('container_id', 'user_id', name='_container_user_uc'),)

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