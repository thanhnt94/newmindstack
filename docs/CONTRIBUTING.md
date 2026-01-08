# Contributing to MindStack

## 🚀 Quick Start

```bash
# Clone
git clone <repo-url>
cd newmindstack

# Setup
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt

# Run
python start_mindstack_app.py
```

---

## 📁 Project Structure

```
mindstack_app/
├── models/       # Database models
├── modules/      # Feature blueprints
│   ├── learning/
│   │   ├── logics/    # Pure calculation engines
│   │   ├── services/  # DB + business logic
│   │   └── sub_modules/
│   └── ...
├── services/     # Shared services
└── templates/    # Jinja2 templates
```

---

## 🧪 Testing

```bash
# Run all tests
python -m pytest tests/ -v

# Run specific test file
python -m pytest tests/test_srs_logic.py -v

# Run with coverage
python -m pytest tests/ --cov=mindstack_app
```

---

## 📝 Code Style

### Python

- Follow PEP 8
- Use type hints where possible
- Docstrings for public functions

### Architecture Patterns

| Layer | Responsibility |
|-------|----------------|
| `routes.py` | HTTP handling only |
| `services/` | DB + business orchestration |
| `logics/` | Pure calculations (no DB) |

### Naming Conventions

```python
# Files
my_module.py      # snake_case

# Classes
class MyClass:    # PascalCase

# Functions/Variables
def my_function(): # snake_case
my_variable = 1
```

---

## 🔀 Git Workflow

### Branch Names

```
feature/add-voice-recognition
bugfix/fix-srs-calculation
refactor/cleanup-templates
```

### Commit Messages

```
feat: add voice pronunciation scoring
fix: correct SRS interval calculation
refactor: extract common template components
docs: update API documentation
test: add gamification scoring tests
```

---

## 📋 Pull Request Checklist

- [ ] Tests pass (`pytest tests/ -v`)
- [ ] Code follows style guidelines
- [ ] Documentation updated if needed
- [ ] No breaking changes (or documented)

---

## 📚 Documentation

| Doc | Purpose |
|-----|---------|
| [ARCHITECTURE.md](ARCHITECTURE.md) | System overview |
| [API.md](API.md) | Endpoint reference |
| [SRS_ALGORITHM.md](SRS_ALGORITHM.md) | SRS details |
| [GAMIFICATION.md](GAMIFICATION.md) | Points/badges |
| [DATABASE.md](DATABASE.md) | Schema reference |
