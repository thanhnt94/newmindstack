# MindStack Configuration Guide

## Overview

Hướng dẫn cấu hình MindStack cho các môi trường khác nhau.

---

## 📁 Configuration Files

```
newmindstack/
├── .env                          # Environment variables
├── mindstack_app/
│   ├── config.py                 # Main Flask config
│   ├── core/
│   │   └── logging_config.py     # Logging setup
│   └── services/
│       ├── config_service.py     # Runtime config
│       └── memory_power_config_service.py
```

---

## 🔧 Main Configuration

### config.py

```python
# mindstack_app/config.py

import os

# Base directory
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))

class Config:
    # === Security ===
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'a_very_secret_key'
    
    # === Database ===
    DATABASE_PATH = os.path.join(BASE_DIR, "database", "mindstack_new.db")
    SQLALCHEMY_DATABASE_URI = os.environ.get('SQLALCHEMY_DATABASE_URI') or f'sqlite:///{DATABASE_PATH}'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # SQLite optimization
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_pre_ping': True,
        'connect_args': {'timeout': 30}
    }
    
    # === Pagination ===
    ITEMS_PER_PAGE = 12
    
    # === File Storage ===
    UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads')
    BACKUP_FOLDER = os.path.join(BASE_DIR, 'backups')
    FLASHCARD_AUDIO_CACHE_DIR = os.path.join(UPLOAD_FOLDER, 'flashcard', 'audio', 'cache')
    FLASHCARD_IMAGE_CACHE_DIR = os.path.join(UPLOAD_FOLDER, 'flashcard', 'images', 'cache')
    
    # === Web Push ===
    VAPID_PRIVATE_KEY = os.environ.get('VAPID_PRIVATE_KEY') or 'default_key'
    VAPID_PUBLIC_KEY = os.environ.get('VAPID_PUBLIC_KEY') or 'default_key'
    VAPID_EMAIL = os.environ.get('VAPID_EMAIL') or 'mailto:admin@mindstack.app'
```

---

## 🌍 Environment Variables

### Development (.env)

```bash
# .env file
PYTHONDONTWRITEBYTECODE=1
FLASK_ENV=development
FLASK_DEBUG=1

# Security
SECRET_KEY=dev-secret-key-change-in-production

# Database (optional - defaults to SQLite)
# SQLALCHEMY_DATABASE_URI=sqlite:///database/mindstack_new.db

# AI Keys (optional - stored in database)
# GEMINI_API_KEY=your_key
# HUGGINGFACE_API_KEY=your_key

# Web Push (optional)
# VAPID_PRIVATE_KEY=your_private_key
# VAPID_PUBLIC_KEY=your_public_key
```

### Production

```bash
# Production environment variables
FLASK_ENV=production
SECRET_KEY=your-very-secure-random-key-here

# Database
SQLALCHEMY_DATABASE_URI=sqlite:///database/mindstack_new.db

# Web Push
VAPID_PRIVATE_KEY=your_vapid_private_key
VAPID_PUBLIC_KEY=your_vapid_public_key
VAPID_EMAIL=mailto:your@email.com
```

---

## 📊 Configuration Reference

### Required Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `SECRET_KEY` | Flask session encryption | Built-in (insecure) |

### Optional Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `FLASK_ENV` | Environment mode | `development` |
| `FLASK_DEBUG` | Enable debug mode | `0` |
| `SQLALCHEMY_DATABASE_URI` | Database connection | SQLite local |
| `ITEMS_PER_PAGE` | Pagination size | `12` |

### Web Push Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `VAPID_PRIVATE_KEY` | VAPID private key | For push notifications |
| `VAPID_PUBLIC_KEY` | VAPID public key | For push notifications |
| `VAPID_EMAIL` | Contact email | For push notifications |

---

## 🗂️ Directory Structure

MindStack tự động tạo các thư mục cần thiết:

```python
# Trong config.py
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(FLASHCARD_AUDIO_CACHE_DIR, exist_ok=True)
os.makedirs(FLASHCARD_IMAGE_CACHE_DIR, exist_ok=True)
os.makedirs(BACKUP_FOLDER, exist_ok=True)
```

**Thư mục cuối cùng:**
```
newmindstack/
├── database/
│   └── mindstack_new.db     # SQLite database
├── uploads/
│   └── flashcard/
│       ├── audio/
│       │   └── cache/       # TTS audio cache
│       └── images/
│           └── cache/       # Image cache
└── backups/                 # Database backups
```

---

## 🎯 Runtime Configuration

### Config Service

Quản lý cấu hình động trong database:

```python
from mindstack_app.services.config_service import ConfigService

# Get config
value = ConfigService.get('srs_base_interval', default=10)

# Set config
ConfigService.set('srs_base_interval', 15)

# Get all configs
all_configs = ConfigService.get_all()
```

### Memory Power Config

```python
from mindstack_app.modules.learning.services.memory_power_config_service import MemoryPowerConfigService

# Get memory power settings
config = MemoryPowerConfigService.get_config()
# {
#     'mastery_threshold': 0.8,
#     'retention_target': 0.9,
#     ...
# }
```

---

## 📝 Learning Mode Configuration

### Flashcard Modes

```python
# modules/learning/sub_modules/flashcard/engine/config.py

FLASHCARD_MODES = [
    {
        'id': 'new_only',
        'name': 'Học mới',
        'description': 'Chỉ học thẻ mới',
        'icon': '📚',
        'color': '#4CAF50'
    },
    {
        'id': 'due_only',
        'name': 'Ôn tập',
        'description': 'Thẻ đến hạn ôn',
        'icon': '🔄',
        'color': '#2196F3'
    },
    # ...
]
```

### Quiz Modes

```python
# modules/learning/sub_modules/quiz/engine/config.py

QUIZ_MODES = [
    {
        'id': 'batch',
        'batch_size': 10,
        'time_limit': None
    },
    {
        'id': 'timed',
        'batch_size': 20,
        'time_limit': 600  # 10 minutes
    }
]
```

---

## 🔒 Security Configuration

### Generate Secret Key

```python
# Python
import secrets
print(secrets.token_hex(32))
```

```bash
# Bash
python -c "import secrets; print(secrets.token_hex(32))"
```

### Generate VAPID Keys

```bash
# Using web-push library
pip install py-vapid
vapid --gen
```

---

## 📊 Logging Configuration

### logging_config.py

```python
# core/logging_config.py

LOGGING_CONFIG = {
    'version': 1,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'level': 'DEBUG',
            'formatter': 'detailed'
        },
        'file': {
            'class': 'logging.FileHandler',
            'filename': 'app.log',
            'level': 'INFO'
        }
    },
    'loggers': {
        '': {
            'handlers': ['console', 'file'],
            'level': 'DEBUG'
        }
    }
}
```

### Usage

```python
from flask import current_app

current_app.logger.info("Info message")
current_app.logger.error("Error message", exc_info=True)
```

---

## 🔄 Database Configuration

### SQLite Settings

```python
SQLALCHEMY_ENGINE_OPTIONS = {
    'pool_pre_ping': True,        # Check connection validity
    'connect_args': {
        'timeout': 30,             # Lock timeout (seconds)
        'check_same_thread': False # Allow multi-threading
    }
}
```

### Enable WAL Mode

```python
# Trong __init__.py
from sqlalchemy import event

@event.listens_for(engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA busy_timeout=30000")
    cursor.close()
```

---

## 🚀 Environment-Specific Configs

### Development

```python
class DevelopmentConfig(Config):
    DEBUG = True
    FLASK_ENV = 'development'
```

### Production

```python
class ProductionConfig(Config):
    DEBUG = False
    FLASK_ENV = 'production'
    
    # Stricter security
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
```

### Testing

```python
class TestingConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
```

---

## 📚 References

- [Flask Configuration](https://flask.palletsprojects.com/en/2.0.x/config/)
- [SQLAlchemy Engine](https://docs.sqlalchemy.org/en/14/core/engines.html)
- [python-dotenv](https://github.com/theskumar/python-dotenv)
