# MindStack Testing Guide

## Overview

Hướng dẫn viết và chạy tests cho MindStack project.

---

## 🚀 Quick Start

```bash
# Chạy tất cả tests
python -m pytest tests/ -v

# Chạy test cụ thể
python -m pytest tests/test_srs_logic.py -v

# Chạy với coverage
python -m pytest tests/ --cov=mindstack_app

# Chạy tests matching pattern
python -m pytest tests/ -k "test_srs" -v
```

---

## 📁 Test Structure

```
tests/
├── conftest.py              # Fixtures & config
├── test_access_control.py   # Permission tests
├── test_admin_user_management.py
├── test_config_management.py
├── test_excel_utils.py
├── test_gamification.py     # Points, badges
├── test_image_service.py
├── test_module_registry.py
├── test_quiz_submission.py
├── test_srs_logic.py        # SRS algorithm
└── test_stats_api.py        # Statistics API
```

---

## 🔧 Test Configuration

### conftest.py

```python
import pytest
from mindstack_app import create_app, db
from mindstack_app.config import Config

class TestConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite://'  # In-memory DB
    SQLALCHEMY_ENGINE_OPTIONS = {
        'connect_args': {'check_same_thread': False}
    }
    WTF_CSRF_ENABLED = False  # Disable CSRF for testing

@pytest.fixture
def app():
    """Create test application."""
    app = create_app(TestConfig)
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()

@pytest.fixture
def client(app):
    """Create test client."""
    return app.test_client()

@pytest.fixture
def authenticated_client(client, app):
    """Client with logged-in user."""
    with app.app_context():
        # Create test user
        user = User(username='testuser', email='test@test.com')
        user.set_password('password')
        db.session.add(user)
        db.session.commit()
        
        # Login
        client.post('/auth/login', data={
            'username': 'testuser',
            'password': 'password'
        })
    return client
```

---

## 📝 Writing Tests

### Basic Test

```python
# tests/test_example.py

def test_homepage(client):
    """Test homepage loads."""
    response = client.get('/')
    assert response.status_code == 200

def test_login_required(client):
    """Test protected routes require login."""
    response = client.get('/dashboard')
    assert response.status_code == 302  # Redirect to login
```

### Testing SRS Logic

```python
# tests/test_srs_logic.py

from mindstack_app.modules.learning.logics.srs_engine import SrsEngine

def test_easiness_factor_calculation():
    """Test EF calculation with different qualities."""
    # Perfect answer
    new_ef = SrsEngine.calculate_new_ef(2.5, quality=5)
    assert new_ef > 2.5
    
    # Wrong answer
    new_ef = SrsEngine.calculate_new_ef(2.5, quality=1)
    assert new_ef < 2.5
    assert new_ef >= 1.3  # Minimum EF

def test_interval_calculation():
    """Test interval progression."""
    intervals = []
    current_interval = 1
    ef = 2.5
    
    for _ in range(5):
        current_interval = SrsEngine.calculate_next_interval(
            current_interval, ef, quality=4
        )
        intervals.append(current_interval)
    
    # Intervals should increase
    assert intervals == sorted(intervals)
```

### Testing API Endpoints

```python
# tests/test_stats_api.py
import json

def test_get_item_stats(authenticated_client, app):
    """Test item statistics endpoint."""
    with app.app_context():
        # Create test item
        item = create_test_item()
        
    response = authenticated_client.get(f'/stats/api/item/{item.item_id}')
    assert response.status_code == 200
    
    data = json.loads(response.data)
    assert 'success' in data
    assert data['success'] == True
```

### Testing Gamification

```python
# tests/test_gamification.py

def test_score_calculation(app):
    """Test point calculation for different qualities."""
    with app.app_context():
        from mindstack_app.modules.learning.logics.scoring_engine import ScoringEngine
        
        # Perfect answer
        points = ScoringEngine.calculate_points(
            mode='flashcard',
            quality=5,
            is_first_time=True
        )
        assert points == 10 * 2.0 + 5  # base * multiplier + first_time_bonus
        
        # Wrong answer
        points = ScoringEngine.calculate_points(
            mode='flashcard',
            quality=1,
            is_first_time=False
        )
        assert points == 0
```

---

## 🎯 Testing Patterns

### Testing Pure Logic (logics/)

```python
# Logic functions are pure - no DB, easy to test
def test_memory_power_calculation():
    from mindstack_app.modules.learning.logics.memory_engine import MemoryEngine
    
    result = MemoryEngine.calculate_memory_power(
        mastery=0.8,
        retention=0.9
    )
    assert result == 0.72  # 0.8 * 0.9
```

### Testing Services (services/)

```python
# Services need app context and database
def test_srs_service_update(app):
    with app.app_context():
        from mindstack_app.modules.learning.services.srs_service import SrsService
        
        # Create test data
        user = create_test_user()
        item = create_test_item()
        
        # Test update
        result = SrsService.update_unified(
            user_id=user.user_id,
            item_id=item.item_id,
            quality=4
        )
        
        assert result is not None
        assert result.status in ('learning', 'reviewing')
```

### Testing Routes

```python
def test_flashcard_session_start(authenticated_client, app):
    with app.app_context():
        set_item = create_test_set_with_items()
        
    response = authenticated_client.get(f'/flashcard/set/{set_item.container_id}/session')
    assert response.status_code == 200
```

---

## 🔄 Database Fixtures

### Creating Test Data

```python
@pytest.fixture
def test_user(app):
    with app.app_context():
        user = User(
            username='testuser',
            email='test@example.com',
            user_role='user'
        )
        user.set_password('password123')
        db.session.add(user)
        db.session.commit()
        yield user

@pytest.fixture
def test_flashcard_set(app, test_user):
    with app.app_context():
        container = LearningContainer(
            title='Test Set',
            container_type='FLASHCARD',
            creator_user_id=test_user.user_id
        )
        db.session.add(container)
        
        for i in range(10):
            item = LearningItem(
                container=container,
                content={'front': f'Front {i}', 'back': f'Back {i}'}
            )
            db.session.add(item)
        
        db.session.commit()
        yield container
```

---

## 📊 Test Coverage

### Check Coverage

```bash
# Generate coverage report
python -m pytest tests/ --cov=mindstack_app --cov-report=html

# Open report
start htmlcov/index.html  # Windows
open htmlcov/index.html   # Mac
```

### Coverage Targets

| Component | Target |
|-----------|--------|
| Logic modules | >90% |
| Services | >80% |
| Routes | >70% |
| Models | >85% |

---

## ⚠️ Testing Best Practices

### DO ✅

```python
# Use descriptive names
def test_srs_interval_increases_on_correct_answer():
    pass

# Test edge cases
def test_ef_does_not_go_below_minimum():
    pass

# Use fixtures for setup
@pytest.fixture
def user_with_progress(app):
    pass
```

### DON'T ❌

```python
# Vague names
def test_function1():
    pass

# Test multiple things
def test_everything():
    # Testing login AND logout AND dashboard
    pass

# Depend on external services
def test_with_real_api():
    # Should mock external calls
    pass
```

---

## 🔧 Mocking

```python
from unittest.mock import patch, MagicMock

def test_ai_service_with_mock(app):
    with app.app_context():
        with patch('mindstack_app.modules.ai_services.gemini_client.GeminiClient') as mock:
            mock.return_value.generate_content.return_value = (True, "Mocked response")
            
            # Test code that uses AI service
            result = some_function_using_ai()
            assert "Mocked response" in result
```

---

## 📚 References

- [pytest Documentation](https://docs.pytest.org/)
- [Flask Testing](https://flask.palletsprojects.com/en/2.0.x/testing/)
- [pytest-cov](https://pytest-cov.readthedocs.io/)
