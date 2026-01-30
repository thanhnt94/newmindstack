"""AI-related database models moved to Kernel."""

from __future__ import annotations
from sqlalchemy.sql import func
from mindstack_app.core.extensions import db

class ApiKey(db.Model):
    """Persisted API keys for AI providers."""

    __tablename__ = 'api_keys'

    key_id = db.Column(db.Integer, primary_key=True)
    provider = db.Column(db.String(50), default='gemini', nullable=False)
    key_value = db.Column(db.String(255), unique=True, nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    is_exhausted = db.Column(db.Boolean, default=False)
    last_used_timestamp = db.Column(db.DateTime(timezone=True))
    notes = db.Column(db.Text)

class AiTokenLog(db.Model):
    """Log entry for AI usage, token tracking, and cost auditing."""

    __tablename__ = 'ai_token_logs'

    log_id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime(timezone=True), server_default=func.now())
    user_id = db.Column(db.Integer, nullable=True)
    
    provider = db.Column(db.String(50), nullable=False)   # 'gemini', 'huggingface'
    model_name = db.Column(db.String(100), nullable=False) # 'gemini-1.5-flash'
    key_id = db.Column(db.Integer, db.ForeignKey('api_keys.key_id'), nullable=True)
    
    feature = db.Column(db.String(50))   # 'explanation', 'chat', 'translation'
    context_ref = db.Column(db.String(255)) # e.g. "Card #123"
    
    input_tokens = db.Column(db.Integer, default=0)
    output_tokens = db.Column(db.Integer, default=0)
    processing_time_ms = db.Column(db.Integer, default=0)
    
    status = db.Column(db.String(20), default='success')
    error_message = db.Column(db.Text, nullable=True)

    # Relationships
    api_key = db.relationship('ApiKey', backref='usage_logs')

class AiCache(db.Model):
    """Cache for AI generated content to save costs and reduce latency."""

    __tablename__ = 'ai_cache'

    cache_id = db.Column(db.Integer, primary_key=True)
    provider = db.Column(db.String(50), nullable=False)
    model_name = db.Column(db.String(100), nullable=False)
    
    # Hashed prompt or key data
    prompt_hash = db.Column(db.String(64), index=True, nullable=False)
    
    # The actual cached response
    response_text = db.Column(db.Text, nullable=False)
    
    created_at = db.Column(db.DateTime(timezone=True), server_default=func.now())
    expires_at = db.Column(db.DateTime(timezone=True), nullable=True)
    
    # Metadata for auditing
    hit_count = db.Column(db.Integer, default=0)
    last_hit_at = db.Column(db.DateTime(timezone=True))
