from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey
from datetime import datetime, timezone
import uuid
from .database import Base
from werkzeug.security import generate_password_hash, check_password_hash

class WTUser(Base):
    __tablename__ = 'wt_users'
    id = Column(Integer, primary_key=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    is_admin = Column(Boolean, default=False)
    total_watch_minutes = Column(Integer, default=0)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class WTRoom(Base):
    __tablename__ = 'wt_rooms'
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(100), nullable=False)
    host_id = Column(Integer, nullable=False) 
    current_video_id = Column(String(50), nullable=True) 
    is_playing = Column(Boolean, default=False)
    current_time = Column(Integer, default=0) 
    allow_guest_control = Column(Boolean, default=False)
    password = Column(String(50), nullable=True)
    is_public = Column(Boolean, default=True)
    last_updated = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

class WTSetting(Base):
    __tablename__ = 'wt_settings'
    key = Column(String(50), primary_key=True)
    value = Column(String(255))

class WTMembership(Base):
    __tablename__ = 'wt_memberships'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('wt_users.id'), nullable=False)
    room_id = Column(String(36), ForeignKey('wt_rooms.id'), nullable=False)
    joined_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

class WTChatMessage(Base):
    __tablename__ = 'wt_chat_messages'
    id = Column(Integer, primary_key=True)
    room_id = Column(String(36), ForeignKey('wt_rooms.id'), nullable=False)
    username = Column(String(50), nullable=False)
    message = Column(String(1000), nullable=False)
    video_id = Column(String(50), nullable=True)
    timestamp = Column(Integer, nullable=True)
    reactions = Column(String(1000), default='{}')
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

class WTVideoHistory(Base):
    __tablename__ = 'wt_video_history'
    id = Column(Integer, primary_key=True)
    room_id = Column(String(36), ForeignKey('wt_rooms.id'), nullable=False)
    video_id = Column(String(50), nullable=False)
    added_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
