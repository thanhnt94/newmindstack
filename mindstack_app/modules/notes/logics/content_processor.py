# mindstack_app/modules/notes/logics/content_processor.py
from mindstack_app.utils.html_sanitizer import sanitize_rich_text
import re

class NoteContentProcessor:
    """Stateless logic for processing note content."""
    
    @staticmethod
    def sanitize(content: str) -> str:
        if not content:
            return ""
        return sanitize_rich_text(content)

    @staticmethod
    def format_summary(content: str, max_length: int = 100) -> str:
        if not content:
            return ""
        # Remove tags for summary (rough strip using regex as internal helper doesn't have it)
        text = re.sub(r'<[^>]+>', '', content)
        if len(text) > max_length:
            return text[:max_length] + "..."
        return text
