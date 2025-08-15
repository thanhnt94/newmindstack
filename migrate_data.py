# File: migrate_data.py
# Phiên bản: 2.0
# ĐÃ SỬA: Sử dụng đường dẫn tuyệt đối để khắc phục lỗi "unable to open database file".

import os
import random
from sqlalchemy import create_engine, Column, Integer, String, Text, Boolean, TIMESTAMP, ForeignKey, func
from sqlalchemy.orm import sessionmaker, declarative_base
from werkzeug.security import generate_password_hash

# --- CẤU HÌNH ---
# Lấy đường dẫn tuyệt đối của thư mục chứa file script này
basedir = os.path.abspath(os.path.dirname(__file__))

OLD_DB_PATH = os.path.join(basedir, 'old_mindstack.db')
NEW_DB_PATH = os.path.join(basedir, 'instance', 'mindstack.db')

# --- BƯỚC 1: ĐỊNH NGHĨA CẤU TRÚC DATABASE CŨ ---
OldBase = declarative_base()

class OldUser(OldBase):
    __tablename__ = 'Users'
    user_id = Column(Integer, primary_key=True)
    username = Column(String, unique=True)
    password = Column(String)
    user_role = Column(String, default='user')
    score = Column(Integer, default=0)

class OldVocabularySet(OldBase):
    __tablename__ = 'VocabularySets'
    set_id = Column(Integer, primary_key=True)
    title = Column(String, nullable=False)
    description = Column(String)
    tags = Column(String)
    creator_user_id = Column(Integer, ForeignKey('Users.user_id'))
    is_public = Column(Integer, default=1)
    ai_prompt = Column(Text)

class OldFlashcard(OldBase):
    __tablename__ = 'Flashcards'
    flashcard_id = Column(Integer, primary_key=True)
    set_id = Column(Integer, ForeignKey('VocabularySets.set_id'), nullable=False)
    front = Column(String, nullable=False)
    back = Column(String, nullable=False)
    ai_explanation = Column(Text)

class OldQuestionSet(OldBase):
    __tablename__ = 'QuestionSets'
    set_id = Column(Integer, primary_key=True)
    title = Column(String, nullable=False)
    description = Column(String)
    creator_user_id = Column(Integer, ForeignKey('Users.user_id'))
    is_public = Column(Integer, default=1)
    ai_prompt = Column(Text)

class OldQuizQuestion(OldBase):
    __tablename__ = 'QuizQuestions'
    question_id = Column(Integer, primary_key=True)
    set_id = Column(Integer, ForeignKey('QuestionSets.set_id'), nullable=False)
    question = Column(Text)
    option_a = Column(String)
    option_b = Column(String)
    option_c = Column(String)
    option_d = Column(String)
    correct_answer = Column(String(1))
    guidance = Column(Text)
    ai_explanation = Column(Text)

# --- BƯỚC 2: KẾT NỐI TỚI CẢ HAI DATABASE ---
if not os.path.exists(OLD_DB_PATH):
    print(f"LỖI: Không tìm thấy file database cũ tại '{OLD_DB_PATH}'. Vui lòng đặt file 'old_mindstack.db' vào thư mục gốc.")
    exit()

if os.path.exists(NEW_DB_PATH):
    os.remove(NEW_DB_PATH)
    print(f"Đã xóa database mới tại '{NEW_DB_PATH}' để chuẩn bị di chuyển dữ liệu.")

os.makedirs(os.path.dirname(NEW_DB_PATH), exist_ok=True)

old_engine = create_engine(f'sqlite:///{OLD_DB_PATH}')
new_engine = create_engine(f'sqlite:///{NEW_DB_PATH}')
OldSession = sessionmaker(bind=old_engine)
NewSession = sessionmaker(bind=new_engine)
old_session = OldSession()
new_session = NewSession()

from mindstack_app.models import db, User, LearningContainer, LearningItem
from flask import Flask

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{NEW_DB_PATH}'
db.init_app(app)

with app.app_context():
    db.create_all()
    print("Đã tạo thành công các bảng trong database mới.")

# --- BƯỚC 3: THỰC HIỆN CHUYỂN ĐỔI DỮ LIỆU ---

def migrate_data():
    """
    Hàm chính thực hiện việc đọc, chuyển đổi và ghi dữ liệu.
    """
    try:
        # 3.1. Chuyển đổi Users
        print("\nBắt đầu chuyển đổi Users...")
        old_users = old_session.query(OldUser).all()
        for old_user in old_users:
            new_user = User(
                user_id=old_user.user_id,
                username=old_user.username,
                email=f"{old_user.username.lower().replace(' ', '_')}_{random.randint(100,999)}@example.com",
                password_hash=old_user.password or generate_password_hash('123456'),
                user_role=old_user.user_role or 'user',
                total_score=old_user.score or 0
            )
            if new_user.username == 'admin':
                new_user.email = 'admin@example.com'
            new_session.add(new_user)
        new_session.commit()
        print(f"-> Đã chuyển đổi thành công {len(old_users)} users.")

        # 3.2. Chuyển đổi VocabularySets -> LearningContainer
        print("\nBắt đầu chuyển đổi Bộ thẻ (VocabularySets)...")
        old_vsets = old_session.query(OldVocabularySet).all()
        for old_vset in old_vsets:
            new_container = LearningContainer(
                container_id=old_vset.set_id,
                creator_user_id=old_vset.creator_user_id,
                container_type='FLASHCARD_SET',
                title=old_vset.title,
                description=old_vset.description,
                tags=old_vset.tags or "chua_phan_loai",
                is_public=bool(old_vset.is_public),
                ai_settings={'custom_prompt': old_vset.ai_prompt} if old_vset.ai_prompt else None
            )
            new_session.add(new_container)
        new_session.commit()
        print(f"-> Đã chuyển đổi thành công {len(old_vsets)} bộ thẻ.")

        # 3.3. Chuyển đổi Flashcards -> LearningItem
        print("\nBắt đầu chuyển đổi Thẻ (Flashcards)...")
        old_flashcards = old_session.query(OldFlashcard).all()
        for old_card in old_flashcards:
            new_item = LearningItem(
                item_id=old_card.flashcard_id,
                container_id=old_card.set_id,
                item_type='FLASHCARD',
                content={
                    "front": old_card.front,
                    "back": old_card.back
                },
                ai_explanation=old_card.ai_explanation
            )
            new_session.add(new_item)
        new_session.commit()
        print(f"-> Đã chuyển đổi thành công {len(old_flashcards)} thẻ.")

        # 3.4. Chuyển đổi QuestionSets -> LearningContainer
        print("\nBắt đầu chuyển đổi Bộ câu hỏi (QuestionSets)...")
        max_vset_id = old_session.query(func.max(OldVocabularySet.set_id)).scalar() or 0
        old_qsets = old_session.query(OldQuestionSet).all()
        for old_qset in old_qsets:
            new_container = LearningContainer(
                container_id=old_qset.set_id + max_vset_id,
                creator_user_id=old_qset.creator_user_id,
                container_type='QUIZ_SET',
                title=old_qset.title,
                description=old_qset.description,
                tags="chua_phan_loai",
                is_public=bool(old_qset.is_public),
                ai_settings={'custom_prompt': old_qset.ai_prompt} if old_qset.ai_prompt else None
            )
            new_session.add(new_container)
        new_session.commit()
        print(f"-> Đã chuyển đổi thành công {len(old_qsets)} bộ câu hỏi.")

        # 3.5. Chuyển đổi QuizQuestions -> LearningItem
        print("\nBắt đầu chuyển đổi Câu hỏi (QuizQuestions)...")
        max_flashcard_id = old_session.query(func.max(OldFlashcard.flashcard_id)).scalar() or 0
        old_questions = old_session.query(OldQuizQuestion).all()
        for old_q in old_questions:
            options = {
                'A': old_q.option_a,
                'B': old_q.option_b,
                'C': old_q.option_c,
                'D': old_q.option_d
            }
            new_item = LearningItem(
                item_id=old_q.question_id + max_flashcard_id,
                container_id=old_q.set_id + max_vset_id,
                item_type='QUIZ_MCQ',
                content={
                    "question": old_q.question,
                    "options": {k: v for k, v in options.items() if v is not None},
                    "correct_answer": old_q.correct_answer,
                    "explanation": old_q.guidance
                },
                ai_explanation=old_q.ai_explanation
            )
            new_session.add(new_item)
        new_session.commit()
        print(f"-> Đã chuyển đổi thành công {len(old_questions)} câu hỏi.")

        print("\n===> QUÁ TRÌNH CHUYỂN ĐỔI DỮ LIỆU HOÀN TẤT! <===")

    except Exception as e:
        print(f"\n!!! ĐÃ CÓ LỖI XẢY RA: {e}")
        new_session.rollback()
    finally:
        old_session.close()
        new_session.close()

if __name__ == '__main__':
    migrate_data()
