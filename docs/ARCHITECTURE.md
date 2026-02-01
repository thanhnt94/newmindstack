# MindStack Architecture Overview (v2.0)

## 📁 Project Structure

The project follows a **Modular Monolith** architecture with a clear separation between Infrastructure, Business Logic, and Presentation layers.

```
mindstack_app/
├── core/                # Infrastructure & Orchestration
│   ├── bootstrap.py     # System Heart: Discovery & Registry
│   ├── config.py        # Settings & ENV management
│   ├── extensions.py    # Flask Extensions (DB, Migrate, CSRF)
│   ├── module_registry.py # Dynamic module tracking
│   └── error_handlers.py
│
├── themes/              # Presentation Layer (Dynamic Themes)
│   ├── aura_mobile/     # Primary Mobile-First Theme
│   │   ├── static/      # Theme-specific CSS/JS/Images
│   │   ├── templates/   # Namespaced Jinja2 templates
│   │   └── __init__.py  # Blueprint definition
│   └── admin/           # Administrative Interface
│
├── modules/             # Feature Modules (Domain Layer)
│   ├── learning/        # Shared learning logic
│   ├── vocabulary/      # Vocab specific features
│   ├── quiz/            # Quiz & Question engines
│   ├── vocab_flashcard/ # Flashcard specialized module
│   ├── ai_services/     # LLM Integrations
│   ├── gamification/    # Points & Badges
│   └── ...
│
├── models/              # Global Database Models
├── services/            # Shared System Services (Config, Metrics)
├── utils/               # Shared Utilities (Filters, Helpers)
└── static/              # Global static assets (System-wide)
```

---

## 🚀 The Bootstrapping Process (`core/bootstrap.py`)

MindStack uses **Auto-Discovery** to load modules and themes:

1. **Init Infrastructure**: Initializes DB, Migrations, CSRF, and Scheduler.
2. **Global Handlers**: Registers error handlers and Jinja2 filters.
3. **Module Discovery**: Scans `modules/`, imports blueprints, and executes `setup_module()` if present.
4. **Theme Activation**: Loads the active theme defined in `ACTIVE_THEME` config.
5. **Model Registry**: Ensures all SQLAlchemy models are imported for visibility.

---

## 🎨 Presentation Layer: Themes

MindStack supports multiple themes. The active theme is registered as a blueprint and its `templates/` folder is used for rendering.

- **Namespacing**: Templates are organized as `aura_mobile/modules/learning/...` to avoid conflicts.
- **Dynamic Assets**: Supports co-located assets within template folders served via special routes (e.g., `serve_v3_asset`).
- **Mutual Exclusivity**: Modern themes (like Aura Mobile) use hybrid rendering where complex views (Dashboard vs Detail) are mutually exclusive to optimize mobile performance.

---

## 🧩 Module Structure

Each module in `modules/` typically contains:
- `routes/`: Blueprint routes and views.
- `services/`: Module-specific business logic.
- `models.py`: Database models (if specific to module).
- `logics/`: Pure logic (no DB) for algorithms.

---

## 🧠 Core Services

- **TemplateService**: Manages active theme version and path resolution.
- **LearningSessionService**: Unified service for managing all types of learning sessions (Flashcard, Quiz, etc.).
- **ConfigService**: Syncs database-stored settings with `app.config`.

---

## 🤖 AI Integration

- **Interface Layer**: `modules/AI/interface.py` provides a unified way to interact with LLMs.
- **Features**: Supports explanations, content generation, and smart hints.
- **Providers**: Primary support for Google Gemini with fallbacks.