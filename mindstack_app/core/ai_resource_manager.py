"""
Centralized AI Resource Manager (Kernel).
Handles API key rotation, usage logging, and caching.
"""

import threading
import logging
from typing import Optional, Tuple, Dict, Any
from datetime import datetime

from ..db_instance import db
from ..models.ai import ApiKey, AiTokenLog, AiCache

logger = logging.getLogger(__name__)

class AiResourceManager:
    """
    Manages shared AI infrastructure resources.
    This service belongs to the Kernel and is feature-agnostic.
    """
    
    _instances: Dict[str, 'AiResourceManager'] = {}
    _lock = threading.Lock()

    def __init__(self, provider: str):
        self.provider = provider
        self.key_ids = []
        self.keys_loaded = False
        self.local_lock = threading.Lock()

    @classmethod
    def get_manager(cls, provider: str) -> 'AiResourceManager':
        """Get or create a manager for a specific provider."""
        with cls._lock:
            if provider not in cls._instances:
                cls._instances[provider] = cls(provider)
            return cls._instances[provider]

    def _load_keys(self):
        """Load available API keys from DB."""
        try:
            # Clear session to get fresh data
            db.session.expire_all()
            
            keys = ApiKey.query.filter_by(
                provider=self.provider,
                is_active=True,
                is_exhausted=False
            ).order_by(ApiKey.last_used_timestamp.asc().nullsfirst()).all()
            
            self.key_ids = [k.key_id for k in keys]
            self.keys_loaded = True
            
            if not self.key_ids:
                logger.warning(f"AiResourceManager ({self.provider}): No available API keys found.")
            else:
                logger.info(f"AiResourceManager ({self.provider}): Loaded {len(self.key_ids)} keys.")
                
        except Exception as e:
            logger.error(f"AiResourceManager ({self.provider}): Error loading keys: {e}")
            self.key_ids = []

    def get_key(self) -> Tuple[Optional[int], Optional[str]]:
        """Get a valid API key (id, value)."""
        with self.local_lock:
            for _ in range(5): # Retry a few times if keys are invalid
                if not self.keys_loaded or not self.key_ids:
                    self._load_keys()
                    if not self.key_ids:
                        return None, None
                
                key_id = self.key_ids.pop(0)
                
                try:
                    key_obj = ApiKey.query.get(key_id)
                    if key_obj and key_obj.is_active and not key_obj.is_exhausted:
                        key_obj.last_used_timestamp = datetime.now()
                        db.session.commit()
                        return key_obj.key_id, key_obj.key_value
                    else:
                        logger.warning(f"AiResourceManager ({self.provider}): Key {key_id} is no longer valid.")
                        continue
                except Exception as e:
                    logger.error(f"AiResourceManager ({self.provider}): Error retrieving key {key_id}: {e}")
                    db.session.rollback()
                    continue
            return None, None

    def mark_key_exhausted(self, key_id: int):
        """Mark a key as exhausted (quota reached)."""
        try:
            key_obj = ApiKey.query.get(key_id)
            if key_obj:
                key_obj.is_exhausted = True
                db.session.commit()
                logger.warning(f"AiResourceManager ({self.provider}): Key {key_id} marked as exhausted.")
        except Exception as e:
            logger.error(f"AiResourceManager ({self.provider}): Failed to mark key {key_id} exhausted: {e}")
            db.session.rollback()

    def log_usage(self, 
                  model_name: str, 
                  key_id: Optional[int], 
                  feature: str,
                  input_tokens: int = 0,
                  output_tokens: int = 0,
                  duration_ms: int = 0,
                  status: str = 'success',
                  error_message: Optional[str] = None,
                  context_ref: Optional[str] = None,
                  user_id: Optional[int] = None):
        """Log AI interaction for auditing."""
        try:
            log = AiTokenLog(
                provider=self.provider,
                model_name=model_name,
                key_id=key_id,
                feature=feature,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                processing_time_ms=duration_ms,
                status=status,
                error_message=error_message[:1000] if error_message else None,
                context_ref=context_ref,
                user_id=user_id
            )
            db.session.add(log)
            db.session.commit()
        except Exception as e:
            logger.error(f"AiResourceManager ({self.provider}): Failed to log usage: {e}")
            db.session.rollback()

    def force_refresh(self):
        """Force reload of keys on next request."""
        with self.local_lock:
            self.keys_loaded = False
            self.key_ids = []
