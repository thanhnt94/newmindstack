from mindstack_app.core.extensions import db
from datetime import datetime

class GenerationLog(db.Model):
    """
    Model to track all generation requests and their status.
    Acts as an audit log and a status tracker for async tasks.
    """
    __tablename__ = 'content_generator_logs'

    id = db.Column(db.Integer, primary_key=True)
    task_id = db.Column(db.String(64), index=True, nullable=True) # Celery task ID
    
    # Request Details
    request_type = db.Column(db.String(20), nullable=False) # 'text', 'audio', 'image'
    requester_module = db.Column(db.String(50), nullable=True) # e.g., 'flashcard', 'course'
    session_id = db.Column(db.String(100), index=True, nullable=True) # Unique ID
    session_name = db.Column(db.String(255), nullable=True) # User-friendly name
    item_id = db.Column(db.Integer, nullable=True) # Link to LearningItem
    item_title = db.Column(db.String(255), nullable=True) # Cached title (Front/Question) for quick display
    delay_seconds = db.Column(db.Integer, default=0) # Planned delay to avoid bans
    
    # Status
    status = db.Column(db.String(20), default='pending') # pending, processing, completed, failed
    stop_requested = db.Column(db.Boolean, default=False) # New field to support stopping
    
    # Data Payloads (Stored as JSON strings for flexibility)
    input_payload = db.Column(db.Text, nullable=True) 
    output_result = db.Column(db.Text, nullable=True) # Result text or file path
    
    # Metadata
    cost_tokens = db.Column(db.Integer, default=0)
    execution_time_ms = db.Column(db.Integer, default=0)
    error_message = db.Column(db.Text, nullable=True)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    completed_at = db.Column(db.DateTime, nullable=True)

    def __repr__(self):
        return f'<GenerationLog {self.id} - {self.request_type} ({self.status})>'
