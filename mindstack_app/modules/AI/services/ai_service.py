"""
AI Module Service (Features).
Orchestrates AI tasks based on system signals.
"""

import logging
from typing import Any
from flask import current_app

from mindstack_app.core.signals import content_changed, ai_action_requested, ai_response_ready
from mindstack_app.core.extensions import db
from .ai_manager import AIServiceManager

logger = logging.getLogger(__name__)

def setup_ai_signals(app):
    """Register signal listeners for the AI module."""
    
    @content_changed.connect_via(app)
    def handle_content_change(sender, **kwargs):
        """
        Listen for content changes (e.g. LearningItem updated).
        Optionally trigger background explanation generation.
        """
        content_type = kwargs.get('content_type')
        content_id = kwargs.get('content_id')
        payload = kwargs.get('payload', {})
        
        logger.info(f"AI Module: Received content_changed for {content_type} {content_id}")
        
        # Logic to decide if we need background processing
        # This could check settings if auto-explain is on
        pass

    @ai_action_requested.connect_via(app)
    def handle_ai_request(sender, **kwargs):
        """
        Listen for manual AI action requests from UI/other modules.
        """
        user_id = kwargs.get('user_id')
        action_type = kwargs.get('action_type')
        context_data = kwargs.get('context_data', {})
        request_id = context_data.get('request_id')
        
        logger.info(f"AI Module: Handling {action_type} for user {user_id}")
        
        try:
            ai_client = AIServiceManager.get_service()
            prompt = context_data.get('prompt')
            
            if not prompt:
                logger.warning("AI Module: No prompt provided in request.")
                return

            success, result = ai_client.generate_content(
                prompt, 
                feature=action_type, 
                context_ref=context_data.get('ref', 'N/A'),
                user_id=user_id
            )
            
            # Emit response
            ai_response_ready.send(
                current_app._get_current_object(),
                request_id=request_id,
                success=success,
                result=result,
                usage={} # usage metrics could be passed here if needed by the caller
            )
            
        except Exception as e:
            logger.error(f"AI Module: Error processing request: {e}")
            ai_response_ready.send(
                current_app._get_current_object(),
                request_id=request_id,
                success=False,
                result=str(e),
                usage={}
            )

logger.info("AI Module: Signals configured.")
