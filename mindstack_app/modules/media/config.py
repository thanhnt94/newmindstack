# File: mindstack_app/modules/media/config.py
"""Default configuration for media module."""

class MediaModuleDefaultConfig:
    """Default values for media module configuration."""
    
    # Image cache settings
    IMAGE_CACHE_DIR = 'flashcard/images/cache'
    MAX_IMAGE_SIZE_BYTES = 5 * 1024 * 1024  # 5 MB
    SUPPORTED_IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.gif', '.webp'}
    
    # DuckDuckGo search settings
    IMAGE_SEARCH_MAX_RESULTS = 8
    IMAGE_SEARCH_RETRY_ATTEMPTS = 3
    IMAGE_SEARCH_RETRY_DELAY = 3  # seconds
