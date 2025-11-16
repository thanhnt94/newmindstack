"""Database models dedicated to the interactive quiz battle feature."""

from __future__ import annotations

from sqlalchemy.sql import func
from sqlalchemy.types import JSON

from ..db_instance import db


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
