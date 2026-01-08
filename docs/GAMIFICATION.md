# MindStack Gamification System

## Overview

Hệ thống gamification khuyến khích học tập thông qua:
- 💎 **Points** - Điểm thưởng mỗi hoạt động
- 🔥 **Streaks** - Chuỗi ngày học liên tục
- 🏆 **Badges** - Huy hiệu thành tựu
- 📊 **Leaderboard** - Bảng xếp hạng

---

## Point System

### Base Points by Mode

| Mode | Base Points | Cognitive Load |
|------|-------------|----------------|
| Flashcard | 10 | Low |
| MCQ/Quiz | 12 | Low |
| Matching | 12 | Low |
| Typing | 15 | High |
| Listening | 15 | High |
| Speed | 8 | Low |

### Quality Multipliers

| Quality | Points |
|---------|--------|
| 5 (Perfect) | Base × 2.0 |
| 4 (Good) | Base × 1.0 |
| 3 (Hard) | Base × 0.5 |
| 0-2 (Fail) | 0 |

### Bonuses

| Bonus Type | Points |
|------------|--------|
| First-time learning | +5 |
| Streak 5+ | +2 per item |
| Streak 10+ | +5 per item |
| Daily login | +10 |
| Session completion | +20 |
| Perfect session (100%) | +50 |

---

## Streak System

### Daily Streak

Đếm số ngày liên tục có hoạt động học tập.

```
Day 1: Learn → Streak = 1
Day 2: Learn → Streak = 2
Day 3: (skip) → Streak = 0
Day 4: Learn → Streak = 1
```

### Correct Streak

Đếm số câu trả lời đúng liên tiếp trong session.

| Streak | Bonus |
|--------|-------|
| 3 | +3 |
| 5 | +5 |
| 10 | +10 |
| 20 | +25 |

---

## Badge System

### Badge Types

| Type | Trigger |
|------|---------|
| `STREAK` | Daily streak milestones |
| `TOTAL_SCORE` | Điểm tổng đạt ngưỡng |
| `FLASHCARD_COUNT` | Số flashcard đã học |
| `QUIZ_COUNT` | Số quiz đã làm |

### Example Badges

| Badge | Condition | Reward |
|-------|-----------|--------|
| 🔥 Streak 7 | 7 ngày liên tục | +50 |
| 🔥 Streak 30 | 30 ngày liên tục | +200 |
| 💎 1000 Points | Tổng 1000 điểm | +100 |
| 📚 100 Cards | Học 100 flashcards | +50 |

---

## Leaderboard

### Timeframes

| Period | Description |
|--------|-------------|
| Day | Top trong 24h |
| Week | Top 7 ngày |
| Month | Top 30 ngày |
| All-time | Tổng điểm |

---

## Code References

- [scoring_engine.py](../mindstack_app/modules/learning/logics/scoring_engine.py) - Point calculations
- [scoring_service.py](../mindstack_app/modules/gamification/services/scoring_service.py) - Score persistence
- [badges_service.py](../mindstack_app/modules/gamification/services/badges_service.py) - Badge logic
