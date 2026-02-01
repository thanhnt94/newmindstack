# MindStack Module Design Guide

## 1. Directory Structure
```
mindstack_app/modules/{module_name}/
├── __init__.py           # Blueprint & Metadata
├── config.py             # Fallback Defaults
├── models.py             # SQLAlchemy Models (String Refs only)
├── schemas.py            # DTOs
├── routes/               # api.py (JSON) & views.py (HTML)
├── services/             # Orchestration & DB Logic
├── engine/               # Stateful Processors
└── logics/               # Stateless Math/Utils (No DB/Flask)
```

## 2. Dependency Rules
- **Logics**: Standard Libs only. NO DB, Models, or Flask.
- **Engine**: Logics, Schemas. NO Services.
- **Models**: Use 'String' references for cross-module relationships.

## 3. Configuration Priority
`Environment (.env)` > `Database (AppSettings)` > `Module Config (config.py)`

## 4. Refactor Checklist
- [ ] Blueprint registered in `__init__.py`.
- [ ] `config.py` handles hardcoded fallbacks.
- [ ] Models use string-based foreign keys/relationships.
- [ ] Logic/Math isolated from database context.
- [ ] API routes separated from HTML views.
- [ ] All DB queries wrapped in Service layer.
