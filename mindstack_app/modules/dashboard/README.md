# Dashboard Module

## Overview
The Dashboard module acts as a pure **Aggregator Service** for the MindStack application (Tier 1).
It is responsible for gathering data from multiple domain modules (FSRS, Stats, Gamification, Goals) and presenting a unified view for the user's home screen.

## Architecture

### Clean Architecture Principles
- **No Direct DB Access**: This module does NOT query usage tables directly.
- **Interface Driven**: All data is fetched via public `interface.py` of other modules.
- **Resilience**: Failures in sub-modules (e.g., gamification) should not crash the entire dashboard.

### Dependencies
aggregates data from:
- `mindstack_app.modules.stats`: For learning metrics and activity summaries.
- `mindstack_app.modules.fsrs`: For "Due" counts (operational data).
- `mindstack_app.modules.gamification`: For user level, XP, and badges.
- `mindstack_app.modules.goals`: For tracking user goals progress.

## Key Components

### `services/dashboard_service.py`
The core service that orchestrates data fetching.
- `get_dashboard_data(user_id)`: The main entry point.

### `routes/views.py`
Minimal controller that delegates entirely to `DashboardService`.

## Usage
```python
from mindstack_app.modules.dashboard.services.dashboard_service import DashboardService

# Get context for rendering dashboard template
context = DashboardService.get_dashboard_data(user_id=1)
```
