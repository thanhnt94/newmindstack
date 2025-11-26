"""Database models for collaborative flashcard learning sessions."""

from __future__ import annotations

from sqlalchemy.sql import func

from ..db_instance import db


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
