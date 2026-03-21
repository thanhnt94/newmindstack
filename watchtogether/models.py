from sqlalchemy import Column, Integer, String, Boolean, DateTime
from datetime import datetime, timezone
import uuid
from .database import Base
from werkzeug.security import generate_password_hash, check_password_hash

class WTUser(Base):
    __tablename__ = 'wt_users'
    id = Column(Integer, primary_key=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
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
    last_updated = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
