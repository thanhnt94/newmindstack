# File: mindstack_app/modules/chat/__init__.py
# Chat Module - Generic chat for collaborative rooms

from flask import Blueprint

chat_bp = Blueprint(
    'chat',
    __name__,
    url_prefix='/chat'
)

from . import routes  # noqa: E402,F401

__all__ = ['chat_bp']
