"""
Centralized Logging Configuration for MindStack

Provides consistent logging setup across the application with:
- Structured JSON format for production
- Human-readable format for development
- File rotation for log management
"""

import os
import logging
import logging.handlers
from typing import Optional


def setup_logging(
    app=None,
    log_level: str = 'INFO',
    log_dir: Optional[str] = None,
    json_format: bool = False
) -> logging.Logger:
    """
    Configure application logging.
    
    Args:
        app: Flask application instance (optional)
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR)
        log_dir: Directory for log files (default: logs/)
        json_format: Use JSON format for structured logging
        
    Returns:
        Configured logger instance
    """
    # Determine log directory
    if log_dir is None:
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        log_dir = os.path.join(base_dir, 'logs')
    
    os.makedirs(log_dir, exist_ok=True)
    
    # Get log level
    level = getattr(logging, log_level.upper(), logging.INFO)
    
    # Create logger
    logger = logging.getLogger('mindstack')
    logger.setLevel(level)
    
    # Clear existing handlers
    logger.handlers.clear()
    
    # Define formats
    if json_format:
        format_str = '{"time": "%(asctime)s", "level": "%(levelname)s", "module": "%(module)s", "message": "%(message)s"}'
    else:
        format_str = '%(asctime)s [%(levelname)s] %(module)s: %(message)s'
    
    formatter = logging.Formatter(format_str, datefmt='%Y-%m-%d %H:%M:%S')
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # File handler with rotation
    log_file = os.path.join(log_dir, 'mindstack.log')
    file_handler = logging.handlers.RotatingFileHandler(
        log_file,
        maxBytes=10 * 1024 * 1024,  # 10 MB
        backupCount=5,
        encoding='utf-8'
    )
    file_handler.setLevel(level)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    
    # If Flask app provided, configure werkzeug logger too
    if app:
        werkzeug_logger = logging.getLogger('werkzeug')
        werkzeug_logger.setLevel(logging.WARNING)
    
    logger.info(f"Logging initialized: level={log_level}, dir={log_dir}")
    
    return logger


def get_logger(name: str = 'mindstack') -> logging.Logger:
    """Get a logger by name."""
    return logging.getLogger(name)
