# Stats Module

## Purpose
Provides analytics and statistics aggregation for the dashboard and reporting.  
This module acts as a **Data Aggregator** - it calls module interfaces instead of querying databases directly.

## Architecture

```
stats/
├── __init__.py             # Module setup
├── interface.py            # Public API for other modules
├── models.py               # Stats-specific models (if any)
├── services/
│   ├── stats_aggregator.py      # NEW: Interface-based aggregation
│   ├── analytics_service.py     # Dashboard data assembly
│   ├── leaderboard_service.py   # Ranking calculations
│   ├── vocabulary_stats_service.py  # Legacy (TODO: migrate)
│   ├── metrics.py               # Legacy metrics (TODO: migrate)
│   └── analytics_listener.py    # Event listeners
├── logics/
│   └── chart_utils.py      # Pure chart/date logic
└── routes/
    ├── api.py              # JSON endpoints
    └── views.py            # HTML rendering
```

## Data Aggregator Pattern

This module follows the **Data Aggregator** pattern:

```
┌─────────────────┐     interface     ┌──────────────────┐
│      fsrs       │ ◄───────────────► │                  │
│   gamification  │  get_global_stats │      stats       │
│ learning_history│  get_user_progress│  StatsAggregator │
└─────────────────┘                   └──────────────────┘
                                              │
                                              ▼
                                     ┌──────────────────┐
                                     │    Dashboard     │
                                     │       API        │
                                     └──────────────────┘
```

## Interface Calls (NOT direct DB queries)

| Source Module | Interface Method | Returns |
|---------------|------------------|---------|
| `fsrs` | `FSRSInterface.get_global_stats()` | total_cards, due_count, mastered_count |
| `fsrs` | `FSRSInterface.get_container_stats()` | container-specific FSRS stats |
| `gamification` | `get_user_progress()` | current_streak, total_xp, level |
| `learning_history` | `get_activity_heatmap()` | activity dates and counts |

## API Endpoints

### New Interface-Based Endpoints
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/summary` | Unified dashboard stats (via interfaces) |
| GET | `/api/container/<id>/summary` | Container summary (via interface) |

### Legacy Endpoints
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/leaderboard` | Global leaderboard |
| GET | `/api/leaderboard/container/<id>` | Container leaderboard |

## Zero Coupling Guarantee

**The new `StatsAggregator` does NOT import:**
- `ItemMemoryState` from `fsrs`
- `Streak` from `gamification`
- Any models from other modules

All data flows through public interfaces with generic parameters.

## Migration Notes

> [!WARNING]
> `vocabulary_stats_service.py` and `metrics.py` still contain direct `ItemMemoryState` imports (40+ usages).
> These are marked for gradual migration as the interface methods expand.

### Migration Strategy
1. New features use `StatsAggregator` (interface-based)
2. Legacy code continues to work (direct DB)
3. Gradually migrate legacy code to use interfaces
4. Eventually remove direct model imports

## Caching Recommendations

For performance optimization, consider adding Redis caching for:
- `get_global_stats()` - Cache for 5 minutes
- `get_user_progress()` - Cache for 1 minute
- Leaderboard data - Cache for 15 minutes

```python
# Future: Redis caching example
@cache.cached(timeout=300, key_prefix='fsrs_stats')
def get_global_stats(user_id):
    ...
```
