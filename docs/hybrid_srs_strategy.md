# Hybrid SRS Strategy - Technical Design Document

> **Version:** 1.0  
> **Date:** 29/12/2025  
> **Status:** Active Implementation

---

## 🎯 Overview

MindStack uses a **Hybrid SRS System** that combines two proven approaches:

1. **SM-2 Algorithm** → Scheduling & interval calculation (proven, backend)
2. **Memory Power System** → User metrics & analytics (intuitive, frontend)

This approach provides **optimal scheduling** (SM-2) while presenting **intuitive progress metrics** (Memory Power) to users.

---

## 🧠 Core Principles

### SM-2: The Scheduling Engine

**Purpose:** Determine **WHEN** to review items

**Usage:** All learning modes use SM-2 for:
- Calculating next review interval
- Determining due dates
- Optimizing study schedule

**Why SM-2:**
- ✅ 40+ years of research backing
- ✅ Industry-proven algorithm
- ✅ Handles forgetting curve scientifically
- ✅ Consistent across modes

### Memory Power: The Analytics Engine

**Purpose:** Show **HOW WELL** items are remembered

**Formula:**
```
Memory Power = Mastery × Retention

Where:
- Mastery: How well knowledge is encoded (0-100%)
- Retention: Probability of recall right now (0-100%)
```

**Why Memory Power:**
- ✅ Intuitive for users ("82% remembered")
- ✅ Shows both encoding quality and time decay
- ✅ Great for dashboards and progress tracking
- ✅ Easy to visualize

---

## 🔄 Data Flow

### When User Answers a Question

```
1. User submits answer with quality/correctness
           ↓
2. SM-2 Engine calculates:
   - New interval (e.g., 2880 minutes = 2 days)
   - New easiness factor (e.g., 2.6)
   - Due time (now + interval)
           ↓
3. Memory Power Engine calculates:
   - Mastery based on streaks and reps
   - Retention = 100% (just reviewed)
   - Memory Power = mastery × 1.0
           ↓
4. Save to database:
   - SM-2 fields: interval, ef, reps, status, due_time
   - Memory fields: correct_streak, incorrect_streak
   - DO NOT save retention or memory_power (computed on-demand)
           ↓
5. Return to UI:
   - Next review time (from SM-2)
   - Memory Power metrics (for display)
```

### When Displaying Dashboard Stats

```
1. Fetch all progress records for user
           ↓
2. For each item, calculate real-time:
   - Mastery (from stored streaks + reps)
   - Retention (from last_reviewed + interval + NOW)
   - Memory Power = mastery × retention
           ↓
3. Aggregate:
   - Average memory power
   - Items by strength (strong/medium/weak)
   - Due items count
           ↓
4. Display to user
```

---

## 📐 Quality Normalization

Different learning modes map to SM-2 quality (0-5) differently:

### Flashcard (Self-Report)
```python
User clicks button → Direct quality mapping
- Button 1 (Forgot): 0
- Button 2 (Hard): 2  
- Button 3 (Good): 4
- Button 4 (Easy): 5
```

### Quiz MCQ (Binary)
```python
Correct/Incorrect → Quality mapping
- Correct: 4 (Good)
- Incorrect: 1 (Again)
```

### Typing (Accuracy-based)
```python
Accuracy percentage → Quality mapping
- 100%: 5 (Perfect)
- 90-99%: 4 (Good)
- 70-89%: 3 (Hard)
- 50-69%: 2 (Very hard)
- <50%: 1 (Failed)
```

### Listening (Accuracy-based)
```python
Same as Typing above
```

### Matching (Binary)
```python
Same as Quiz MCQ above
```

**Key Point:** All modes normalize to 0-5 quality, then use same SM-2 logic.

---

## 💾 Database Schema

### LearningProgress Model

**SM-2 Fields:**
```python
interval: int                 # Minutes until next review
easiness_factor: float       # SM-2 EF value (1.3-3.0)
repetitions: int             # Successful reps in current phase
status: str                  # 'new', 'learning', 'reviewing'
due_time: datetime           # When next review is due
last_reviewed: datetime      # Last interaction timestamp
```

**Memory Power Fields:**
```python
correct_streak: int          # Consecutive correct answers
incorrect_streak: int        # Consecutive incorrect answers

# DO NOT STORE:
# - mastery (calculate from streaks + reps)
# - retention (calculate from last_reviewed + interval + NOW)
# - memory_power (calculate from mastery × retention)
```

**Why not store calculated metrics?**
- Retention changes every second (time-based decay)
- Memory Power = mastery × retention also changes
- Storing would require constant updates
- Calculate on-demand is faster and accurate

---

## 🔧 Implementation Architecture

### Core Classes

```
logics/
├── srs_engine.py          # SM-2 calculations
├── memory_engine.py       # Memory Power calculations  
├── scoring_engine.py      # Points/gamification
└── unified_srs.py         # NEW: Orchestrates SM-2 + Memory Power

services/
├── srs_service.py         # Database persistence
└── progress_service.py    # CRUD operations
```

### Unified Entry Point

```python
# All learning modes call this:
UnifiedSrsSystem.process_answer(
    user_id=1,
    item_id=42,
    quality=4,
    mode='flashcard'
)

# Returns:
{
    # SM-2 results (scheduling)
    'next_review': datetime(2025, 12, 31, 10, 0, 0),
    'interval_minutes': 2880,
    'status': 'reviewing',
    
    # Memory Power results (UI display)
    'mastery': 0.78,
    'retention': 1.0,
    'memory_power': 0.78,
    
    # Other
    'correct_streak': 5
}
```

---

## 📊 UI Display Guidelines

### During Learning Session

Show Memory Power metrics to motivate users:

```
┌─────────────────────────────┐
│ 📊 Your Progress            │
├─────────────────────────────┤
│ Memory Power:  78%          │
│ └─ Mastery:    80%          │
│ └─ Retention:  97%          │
│                             │
│ Next review: 2 days         │
│ Streak: 🔥 5 correct        │
└─────────────────────────────┘
```

### Dashboard Analytics

Aggregate view across all items:

```
┌────────────────────────────────────┐
│ 📚 TOEIC Vocabulary Set            │
├────────────────────────────────────┤
│ Overall Memory Power: 72%          │
│                                    │
│ Breakdown:                         │
│ 🟢 Strong (80-100%):  45 items     │
│ 🟡 Medium (50-80%):   78 items     │
│ 🔴 Weak (0-50%):      23 items     │
│                                    │
│ 📅 Due today: 12 items             │
└────────────────────────────────────┘
```

### Item Detail View

Show both current stats and progression:

```
Word: "Ubiquitous"

Current Status:
├─ Memory Power: 85% (Strong! 💪)
├─ Mastery: 88%
├─ Retention: 96%
└─ Next review: in 3 days

History:
├─ Studied: 12 times
├─ Current streak: 8 correct
└─ Last reviewed: 2 hours ago

Chart: [Mastery progression over time]
```

---

## 🧪 Testing Strategy

### Unit Tests

Test pure calculations independently:

```python
# Test SM-2
def test_sm2_interval_calculation():
    result = SrsEngine.calculate_next_state(
        current_status='reviewing',
        current_interval=1440,
        current_ef=2.5,
        current_reps=3,
        quality=5
    )
    assert result.new_interval > 1440  # Should increase

# Test Memory Power
def test_memory_power_calculation():
    mastery = 0.8
    retention = 0.9
    mp = MemoryEngine.calculate_memory_power(mastery, retention)
    assert mp == 0.72
```

### Integration Tests

Test full workflow:

```python
def test_unified_answer_processing():
    result = UnifiedSrsSystem.process_answer(
        user_id=1,
        item_id=1,
        quality=5,
        mode='flashcard'
    )
    
    assert 'next_review' in result
    assert 'memory_power' in result
    assert 0 <= result['mastery'] <= 1.0
```

---

## 🚀 Migration Plan

### Phase 1: Parallel Run (2 weeks)
- Keep existing code working
- Add UnifiedSrsSystem alongside
- Test with subset of users

### Phase 2: Progressive Migration (2 weeks)
- Migrate flashcard module
- Migrate quiz module
- Migrate vocabulary modules
- Verify data integrity

### Phase 3: Cleanup (1 week)
- Remove old SRS update methods
- Clean up duplicate code
- Update documentation

---

## 📈 Performance Considerations

### Optimization 1: Batch Calculation

```python
# BAD: N queries
for item_id in item_ids:
    stats = get_stats(item_id)  # N database queries!

# GOOD: 1 query
progress_records = get_all_progress(user_id, container_id)  # 1 query
stats = [calculate_stats(p) for p in progress_records]  # In-memory
```

### Optimization 2: Caching

```python
# Cache mastery calculation (doesn't change often)
@lru_cache(maxsize=1000)
def get_mastery(user_id, item_id):
    # Only recalculates on cache miss
    pass
```

### Optimization 3: Precompute Due Flags

```python
# Background job runs hourly
def update_due_flags():
    now = datetime.now(timezone.utc)
    LearningProgress.query.filter(
        LearningProgress.due_time <= now
    ).update({'is_due': True})
```

---

## ✅ Success Metrics

**Code Quality:**
- [ ] Single source of truth for SRS logic
- [ ] No duplicate calculations
- [ ] 80%+ test coverage

**Performance:**
- [ ] Dashboard loads in <2 seconds
- [ ] Stats calculation <100ms per item
- [ ] No N+1 queries

**User Experience:**
- [ ] Memory Power metrics displayed in all modes
- [ ] Dashboard shows aggregate stats
- [ ] Users understand their progress

---

## 🔗 Related Documents

- [Architecture Overview](./architecture.md)
- [SRS & Statistics Review](./srs_statistics_review.md)
- [Learning Module Review](./learning_module_review.md)

---

**Approved by:** Development Team  
**Implementation Start:** 29/12/2025
