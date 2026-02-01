# 🎨 MindStack Template & Theme Guidelines

This document defines the patterns for frontend development in MindStack using the Theme system.

---

## 1. The Theme System (`themes/`)

MindStack uses a theme-based approach. The active theme is controlled by the `ACTIVE_THEME` environment variable.

**Active Theme:** `aura_mobile` (Mobile-First, Slate/Indigo aesthetic)

### Directory Structure
```
themes/aura_mobile/
├── static/              # Global theme assets (url_for('aura_mobile.static'))
└── templates/
    └── aura_mobile/     # Namespaced folder
        ├── layouts/     # base.html, etc.
        ├── components/  # Shared components (_flash_msg.html)
        └── modules/     # Module-specific views
```

---

## 2. Template Organization

Templates for modules are co-located within the theme to ensure design consistency.

**Path Pattern:** `aura_mobile/modules/[module_name]/[feature]/index.html`

### Example: Vocabulary Dashboard
- Template: `aura_mobile/modules/learning/vocabulary/dashboard/index.html`
- Partial: `aura_mobile/modules/learning/vocabulary/dashboard/detail.html`

---

## 3. Asset Co-location (Advanced)

For complex modules, assets (CSS/JS) can be stored alongside templates in `modules/` instead of the global `static/` folder.

### Structure:
```
modules/learning/vocabulary/dashboard/
├── css/
│   └── dashboard.css
├── js/
│   └── dashboard.js
└── index.html
```

### Serving Assets:
Each module must define a route to serve these assets:
```python
@blueprint.route('/assets/<path:filename>')
def serve_dashboard_asset(filename):
    # Dynamically resolves path to themes/{active_theme}/templates/{active_theme}/modules/...
```

---

## 4. Responsive & Mobile-First Patterns

### Mutual Exclusivity (Mobile Optimization)
To prevent heavy DOM on mobile, large views (e.g., Grid vs Detail) should be mutually exclusive.
- **Server-side**: Use `{% if active_step == 'detail' %}` to render only the needed view.
- **Client-side**: Use `showStep(step)` in JS to toggle visibility and update history.

### Layout Classes
Use standard body classes for specific session modes to hide global UI:
- `.flashcard-session-active`: Hides global header/footer for immersive learning.

---

## 5. Development Checklist

- [ ] **Namespacing**: Is the template inside the `{theme_name}/` folder?
- [ ] **Fallback**: Does `{% set _v = template_version or 'aura_mobile' %}` exist at the top?
- [ ] **Paths**: Use `_v ~ '/path/to/component.html'` for includes.
- [ ] **Assets**: Are CSS/JS files served via `url_for('module.serve_asset', ...)` if co-located?
- [ ] **Mobile**: Has the layout been tested on a small screen breakpoint?