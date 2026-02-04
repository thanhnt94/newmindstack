"""Collaborative Learning Models.

This module contains all models related to room-based collaborative learning:
- Flashcard Collab (group flashcard study)
- Quiz Battle (multiplayer quiz competition)
"""

from __future__ import annotations
from sqlalchemy.sql import func
from sqlalchemy.types import JSON
from mindstack_app.core.extensions import db


# =============================================================================
# FLASHCARD COLLAB MODELS
# =============================================================================

class FlashcardCollabRoom(db.Model):
    """Represents a collaborative flashcard study room."""
    __tablename__ = 'flashcard_collab_rooms'

    STATUS_LOBBY = 'lobby'
    STATUS_ACTIVE = 'active'
    STATUS_COMPLETED = 'completed'

    room_id = db.Column(db.Integer, primary_key=True)
    room_code = db.Column(db.String(12), unique=True, nullable=False)
    title = db.Column(db.String(120), nullable=False)
    host_user_id = db.Column(db.Integer, db.ForeignKey('users.user_id'), nullable=False)
    container_id = db.Column(db.Integer, db.ForeignKey('learning_containers.container_id'), nullable=False)
    mode = db.Column(db.String(50), nullable=False)
    button_count = db.Column(db.Integer, default=3, nullable=False)
    status = db.Column(db.String(20), default=STATUS_LOBBY, nullable=False)
    is_public = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), server_default=func.now())
    updated_at = db.Column(db.DateTime(timezone=True), onupdate=func.now())

    host = db.relationship('User', backref='hosted_flashcard_collab_rooms', foreign_keys=[host_user_id])
    container = db.relationship('LearningContainer', backref='flashcard_collab_rooms')
    participants = db.relationship(
        'FlashcardCollabParticipant', backref='room', cascade='all, delete-orphan', lazy=True
    )
    rounds = db.relationship(
        'FlashcardCollabRound', backref='room', cascade='all, delete-orphan', lazy=True
    )
    room_progress = db.relationship(
        'FlashcardRoomProgress', backref='room', cascade='all, delete-orphan', lazy=True
    )


class FlashcardCollabParticipant(db.Model):
    """Represents a participant within a collaborative flashcard room."""
    __tablename__ = 'flashcard_collab_participants'

    STATUS_ACTIVE = 'active'
    STATUS_LEFT = 'left'
    STATUS_KICKED = 'kicked'

    participant_id = db.Column(db.Integer, primary_key=True)
    room_id = db.Column(db.Integer, db.ForeignKey('flashcard_collab_rooms.room_id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.user_id'), nullable=False)
    is_host = db.Column(db.Boolean, default=False, nullable=False)
    status = db.Column(db.String(20), default=STATUS_ACTIVE, nullable=False)
    joined_at = db.Column(db.DateTime(timezone=True), server_default=func.now())
    left_at = db.Column(db.DateTime(timezone=True), nullable=True)

    user = db.relationship('User', backref='flashcard_collab_participations', foreign_keys=[user_id])
    __table_args__ = (db.UniqueConstraint('room_id', 'user_id', name='uq_flashcard_collab_participant'),)


class FlashcardCollabMessage(db.Model):
    """Chat messages exchanged inside a collaborative flashcard room."""
    __tablename__ = 'flashcard_collab_messages'

    message_id = db.Column(db.Integer, primary_key=True)
    room_id = db.Column(db.Integer, db.ForeignKey('flashcard_collab_rooms.room_id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.user_id'), nullable=False)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), server_default=func.now(), nullable=False)

    user = db.relationship('User', backref='flashcard_collab_messages', foreign_keys=[user_id])


class FlashcardCollabRound(db.Model):
    """Represents a shared flashcard round within a room."""
    __tablename__ = 'flashcard_collab_rounds'

    STATUS_ACTIVE = 'active'
    STATUS_COMPLETED = 'completed'

    round_id = db.Column(db.Integer, primary_key=True)
    room_id = db.Column(db.Integer, db.ForeignKey('flashcard_collab_rooms.room_id'), nullable=False)
    item_id = db.Column(db.Integer, db.ForeignKey('learning_items.item_id'), nullable=False)
    status = db.Column(db.String(20), default=STATUS_ACTIVE, nullable=False)
    scheduled_for_user_id = db.Column(db.Integer, nullable=True)
    scheduled_due_at = db.Column(db.DateTime(timezone=True), nullable=True)
    started_at = db.Column(db.DateTime(timezone=True), server_default=func.now())
    completed_at = db.Column(db.DateTime(timezone=True), nullable=True)

    answers = db.relationship(
        'FlashcardCollabAnswer', backref='round', cascade='all, delete-orphan', lazy=True
    )


class FlashcardCollabAnswer(db.Model):
    """Tracks each participant's answer in a collaborative round."""
    __tablename__ = 'flashcard_collab_answers'

    answer_id = db.Column(db.Integer, primary_key=True)
    round_id = db.Column(db.Integer, db.ForeignKey('flashcard_collab_rounds.round_id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.user_id'), nullable=False)
    answer_label = db.Column(db.String(50), nullable=True)
    answer_quality = db.Column(db.Integer, nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), server_default=func.now())
    updated_at = db.Column(db.DateTime(timezone=True), onupdate=func.now())

    user = db.relationship('User', backref='flashcard_collab_answers', foreign_keys=[user_id])
    __table_args__ = (db.UniqueConstraint('round_id', 'user_id', name='uq_flashcard_collab_answer'),)


class FlashcardRoomProgress(db.Model):
    """Tracks FSRS progress for a specific ITEM within a specific ROOM (Collab)."""
    __tablename__ = 'flashcard_room_progress'

    progress_id = db.Column(db.Integer, primary_key=True)
    room_id = db.Column(db.Integer, db.ForeignKey('flashcard_collab_rooms.room_id'), nullable=False)
    item_id = db.Column(db.Integer, db.ForeignKey('learning_items.item_id'), nullable=False)
    
    fsrs_state = db.Column(db.Integer, default=0, nullable=False) # 0=New, 1=Learning, 2=Review, 3=Relearning
    fsrs_due = db.Column(db.DateTime(timezone=True), nullable=True)
    fsrs_stability = db.Column(db.Float, default=0.0)
    fsrs_difficulty = db.Column(db.Float, default=0.0)
    
    current_interval = db.Column(db.Float, default=0.0) # In days
    repetitions = db.Column(db.Integer, default=0)
    lapses = db.Column(db.Integer, default=0)
    last_reviewed = db.Column(db.DateTime(timezone=True), nullable=True)

    __table_args__ = (db.UniqueConstraint('room_id', 'item_id', name='uq_flashcard_room_progress'),)


# =============================================================================
# QUIZ BATTLE MODELS
# =============================================================================

class QuizBattleRoom(db.Model):
    """Represents a multiplayer quiz battle lobby and running session."""

    __tablename__ = 'quiz_battle_rooms'

    STATUS_LOBBY = 'lobby'
    STATUS_IN_PROGRESS = 'in_progress'
    STATUS_AWAITING_HOST = 'awaiting_host'
    STATUS_COMPLETED = 'completed'

    MODE_SLOW = 'SLOW'
    MODE_TIMED = 'TIMED'

    room_id = db.Column(db.Integer, primary_key=True)
    room_code = db.Column(db.String(12), unique=True, nullable=False)
    title = db.Column(db.String(120), nullable=False)
    host_user_id = db.Column(db.Integer, db.ForeignKey('users.user_id'), nullable=False)
    container_id = db.Column(
        db.Integer,
        db.ForeignKey('learning_containers.container_id'),
        nullable=False,
    )
    status = db.Column(db.String(20), default=STATUS_LOBBY, nullable=False)
    is_locked = db.Column(db.Boolean, default=False, nullable=False)
    max_players = db.Column(db.Integer, nullable=True)
    question_limit = db.Column(db.Integer, nullable=True)
    is_public = db.Column(db.Boolean, default=False, nullable=False)
    mode = db.Column(db.String(20), default=MODE_SLOW, nullable=False)
    time_per_question_seconds = db.Column(db.Integer, nullable=True)
    question_order = db.Column(JSON, nullable=True)
    current_round_number = db.Column(db.Integer, default=0, nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), server_default=func.now())
    updated_at = db.Column(db.DateTime(timezone=True), onupdate=func.now())

    host = db.relationship('User', backref='hosted_quiz_battle_rooms', foreign_keys=[host_user_id])
    container = db.relationship('LearningContainer', backref='quiz_battle_rooms')
    participants = db.relationship(
        'QuizBattleParticipant',
        backref='room',
        cascade='all, delete-orphan',
        lazy=True,
    )
    rounds = db.relationship(
        'QuizBattleRound',
        backref='room',
        cascade='all, delete-orphan',
        order_by='QuizBattleRound.sequence_number',
        lazy=True,
    )
    messages = db.relationship(
        'QuizBattleMessage',
        backref='room',
        cascade='all, delete-orphan',
        order_by='QuizBattleMessage.created_at',
        lazy=True,
    )


class QuizBattleParticipant(db.Model):
    """Represents a user that participates in a quiz battle room."""

    __tablename__ = 'quiz_battle_participants'

    STATUS_ACTIVE = 'active'
    STATUS_LEFT = 'left'
    STATUS_KICKED = 'kicked'

    participant_id = db.Column(db.Integer, primary_key=True)
    room_id = db.Column(db.Integer, db.ForeignKey('quiz_battle_rooms.room_id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.user_id'), nullable=False)
    is_host = db.Column(db.Boolean, default=False, nullable=False)
    status = db.Column(db.String(20), default=STATUS_ACTIVE, nullable=False)
    joined_at = db.Column(db.DateTime(timezone=True), server_default=func.now())
    left_at = db.Column(db.DateTime(timezone=True), nullable=True)
    kicked_by = db.Column(db.Integer, db.ForeignKey('users.user_id'), nullable=True)
    session_score = db.Column(db.Integer, default=0, nullable=False)
    correct_answers = db.Column(db.Integer, default=0, nullable=False)
    incorrect_answers = db.Column(db.Integer, default=0, nullable=False)

    user = db.relationship('User', foreign_keys=[user_id], backref='quiz_battle_participations')
    kicker = db.relationship('User', foreign_keys=[kicked_by], backref='quiz_battle_kicks')

    __table_args__ = (db.UniqueConstraint('room_id', 'user_id', name='uq_quiz_battle_participant'),)


class QuizBattleRound(db.Model):
    """Represents a question round within a quiz battle session."""

    __tablename__ = 'quiz_battle_rounds'

    STATUS_PENDING = 'pending'
    STATUS_ACTIVE = 'active'
    STATUS_COMPLETED = 'completed'

    round_id = db.Column(db.Integer, primary_key=True)
    room_id = db.Column(db.Integer, db.ForeignKey('quiz_battle_rooms.room_id'), nullable=False)
    sequence_number = db.Column(db.Integer, nullable=False)
    item_id = db.Column(db.Integer, db.ForeignKey('learning_items.item_id'), nullable=False)
    status = db.Column(db.String(20), default=STATUS_PENDING, nullable=False)
    started_at = db.Column(db.DateTime(timezone=True), nullable=True)
    ended_at = db.Column(db.DateTime(timezone=True), nullable=True)

    item = db.relationship('LearningItem', backref='quiz_battle_rounds')
    answers = db.relationship(
        'QuizBattleAnswer',
        backref='round',
        cascade='all, delete-orphan',
        lazy=True,
    )

    __table_args__ = (db.UniqueConstraint('room_id', 'sequence_number', name='uq_quiz_battle_round'),)


class QuizBattleAnswer(db.Model):
    """Stores an answer submitted during a quiz battle round."""

    __tablename__ = 'quiz_battle_answers'

    answer_id = db.Column(db.Integer, primary_key=True)
    round_id = db.Column(db.Integer, db.ForeignKey('quiz_battle_rounds.round_id'), nullable=False)
    participant_id = db.Column(db.Integer, db.ForeignKey('quiz_battle_participants.participant_id'), nullable=False)
    selected_option = db.Column(db.String(5), nullable=False)
    is_correct = db.Column(db.Boolean, default=False, nullable=False)
    score_delta = db.Column(db.Integer, default=0, nullable=False)
    correct_option = db.Column(db.String(5), nullable=True)
    explanation = db.Column(db.Text, nullable=True)
    answered_at = db.Column(db.DateTime(timezone=True), server_default=func.now())

    participant = db.relationship('QuizBattleParticipant', backref='answers')

    __table_args__ = (db.UniqueConstraint('round_id', 'participant_id', name='uq_quiz_battle_answer'),)


class QuizBattleMessage(db.Model):
    """Chat message shared between participants inside a quiz battle room."""

    __tablename__ = 'quiz_battle_messages'

    message_id = db.Column(db.Integer, primary_key=True)
    room_id = db.Column(db.Integer, db.ForeignKey('quiz_battle_rooms.room_id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.user_id'), nullable=False)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), server_default=func.now(), nullable=False)

    user = db.relationship('User', backref='quiz_battle_messages')
