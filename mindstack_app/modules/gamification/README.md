# Gamification Module

## Purpose
Provides gamification features including points, badges, streaks, and leaderboards.  
This module acts as an **Event Consumer** - it listens to signals from other modules rather than being called directly.

## Architecture

```
gamification/
├── events.py           # Signal listeners (Core of the module)
├── __init__.py         # Module setup & listener registration
├── models.py           # Badge, UserBadge, ScoreLog, Streak
├── interface.py        # Public API for other modules
├── services/
│   ├── scoring_service.py    # Point awarding & leaderboards
│   ├── badges_service.py     # Badge checking & awarding
│   ├── streak_service.py     # Streak calculation & tracking
│   ├── reward_manager.py     # Event-driven reward orchestration
│   └── gamification_kernel.py # Low-level DB operations
├── logics/
│   └── streak_logic.py       # Pure streak calculation logic
└── routes/
    └── api.py                # Admin endpoints for badge management
```

## Event-Driven Architecture

This module follows the **Event Consumer** pattern:

```
┌─────────────────┐     signals      ┌──────────────────┐
│ vocab_flashcard │ ───────────────> │   gamification   │
│      quiz       │  card_reviewed   │                  │
│    session      │  session_completed│    events.py     │
└─────────────────┘                  └──────────────────┘
                                              │
                                              ▼
                                     ┌──────────────────┐
                                     │    services/     │
                                     │  scoring_service │
                                     │  badges_service  │
                                     │  streak_service  │
                                     └──────────────────┘
```

## Signals Listened

| Signal | Source | Handler | Action |
|--------|--------|---------|--------|
| `card_reviewed` | `core.signals` | `on_card_reviewed` | Award points |
| `session_completed` | `core.signals` | `on_session_completed` | Log session bonus |
| `score_awarded` | `core.signals` | `on_score_awarded` | Check badges |
| `user_registered` | `core.signals` | `on_user_registered` | Welcome bonus |
| `user_logged_in` | `core.signals` | `on_user_logged_in` | Update streak |
| `flashcard_session_completed` | `vocab_flashcard.signals` | `on_flashcard_session_completed` | badges + streak |

## Zero Coupling Guarantee

**This module does NOT import any models or services from:**
- `vocab_flashcard`
- `quiz`
- `learning`

All communication is through signals with **generic parameters**:
- `user_id: int`
- `amount: int`
- `reason: str`
- `item_type: str`

## Services

### ScoreService
- `award_points(user_id, amount, reason, item_id, item_type)` - Award points
- `get_score_history(user_id, page, per_page)` - Get history
- `record_daily_login(user_id)` - Daily login bonus
- `get_leaderboard(timeframe, limit)` - Get rankings

### BadgeService
- `check_and_award_badges(user_id, trigger_type)` - Check conditions & award

### StreakService
- `get_user_streak(user_id)` - Get streak record
- `update_streak(user_id)` - Recalculate streak
- `get_streak_info(user_id)` - Get UI-friendly data

## Models

| Model | Description |
|-------|-------------|
| `Badge` | Badge definitions (name, condition, reward) |
| `UserBadge` | User-badge associations |
| `ScoreLog` | Score change history |
| `Streak` | User streak tracking |

## Configuration

| Key | Default | Description |
|-----|---------|-------------|
| `DAILY_LOGIN_SCORE` | 10 | Points for daily login |
| `WELCOME_BONUS` | 50 | Points for new users |
