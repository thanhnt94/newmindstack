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
    status = db.Column(db.String(20), default=STATUS_LOBBY, nullable=False)
    is_public = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), server_default=func.now())
    updated_at = db.Column(db.DateTime(timezone=True), onupdate=func.now())

    host = db.relationship('User', backref='hosted_flashcard_collab_rooms', foreign_keys=[host_user_id])
    container = db.relationship('LearningContainer', backref='flashcard_collab_rooms')
    participants = db.relationship(
        'FlashcardCollabParticipant', backref='room', cascade='all, delete-orphan', lazy=True
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
