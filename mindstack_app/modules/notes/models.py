from datetime import datetime, timezone
from mindstack_app.core.extensions import db
from sqlalchemy.sql import func

class Note(db.Model):
    """
    Unified Note Model (Contextual Note System).
    Can attach to any entity via reference_type + reference_id.
    """
    __tablename__ = 'notes'

    note_id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.user_id'), nullable=False)
    
    # Generic Reference info
    reference_type = db.Column(db.String(50), nullable=False) # e.g., 'item', 'container', 'lesson', 'general'
    reference_id = db.Column(db.Integer, nullable=True)       # ID of the referenced entity
    
    title = db.Column(db.String(255), nullable=True)
    content = db.Column(db.Text, nullable=False) # Markdown or HTML
    
    created_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime(timezone=True), onupdate=lambda: datetime.now(timezone.utc))
    
    is_archived = db.Column(db.Boolean, default=False)
    tags = db.Column(db.String(255), nullable=True) # Comma separated for now

    __table_args__ = (
        db.Index('ix_notes_user_ref', 'user_id', 'reference_type', 'reference_id'),
    )

    def to_dict(self):
        return {
            'id': self.note_id,
            'title': self.title,
            'content': self.content,
            'reference_type': self.reference_type,
            'reference_id': self.reference_id,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
