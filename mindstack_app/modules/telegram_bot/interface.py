# File: mindstack_app/modules/telegram_bot/interface.py
"""Public interface for telegram_bot module (Gatekeeper Rule)."""
from .services import send_telegram_message, generate_connect_link

# Re-export for external access
__all__ = ['send_telegram_message', 'generate_connect_link']
