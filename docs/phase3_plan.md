# Phase 3 Plan - UI Integration

## Overview
Implement user-facing UI to display Memory Power metrics across all learning interfaces.

**Sequence:** B → D → A → C (as requested)

---

## 🎯 Phase 3.1: In-Session Stats Display (B)

**Goal:** Show Memory Power metrics while user is learning

**Target:** Flashcard session interface (both desktop and mobile)

### Features to Add

1. **Memory Power Display**
   - Show overall Memory Power % (0-100%)
   - Color-coded: Green (80%+), Yellow (50-80%), Red (<50%)
   - Update after each answer

2. **Mastery & Retention Bars**
   - Separate progress bars for mastery and retention
   - Visual breakdown showing the formula: MP = M × R
   - Tooltips explaining each metric

3. **Real-time Updates**
   - After user answers, show new metrics
   - Smooth transition/animation
   - Celebration for improvements

4. **Mobile Stats Modal**
   - Enhance existing stats modal
   - Add Memory Power tab/section
   - Show current item stats

### UI Mockup (Text)

```
┌─────────────────────────────────────┐
│ 📊 Your Progress                    │
├─────────────────────────────────────┤
│ Memory Power: 78% 🟢                │
│ [████████████████░░░░] 78%          │
│                                     │
│ Breakdown:                          │
│ • Mastery:    [████████████░░] 85% │
│ • Retention:  [████████████░░] 92% │
│                                     │
│ Next review: in 2 days              │
│ Streak: 🔥 5 correct                │
└─────────────────────────────────────┘
```

### Technical Approach

1. **Backend:** Already done! ✅
   - `SrsService.update_unified()` returns `SrsResult`
   - Contains mastery, retention, memory_power

2. **Pass to Frontend:**
   - Return `srs_result` in API response
   - JavaScript receives and displays

3. **Update Templates:**
   - Add Memory Power widget to flashcard templates
   - Update mobile stats modal HTML

---

## 🔌 Phase 3.2: API Endpoints (D)

**Goal:** Create REST APIs for stats consumption

### Endpoints to Create

```python
# Get individual item stats
GET /api/learning/stats/item/<item_id>
Response: {
    "mastery": 0.85,
    "retention": 0.92,
    "memory_power": 0.78,
    "next_review": "2025-12-31T10:00:00Z",
    "is_due": false,
    "status": "reviewing"
}

# Get container aggregate stats
GET /api/learning/stats/container/<container_id>
Response: {
    "total_items": 500,
    "average_memory_power": 0.72,
    "strong_items": 156,
    "medium_items": 278,
    "weak_items": 66,
    "due_items": 45
}

# Batch get multiple items
POST /api/learning/stats/batch
Body: {"item_ids": [1, 2, 3, ...]}
Response: [
    {"item_id": 1, "mastery": 0.8, ...},
    {"item_id": 2, "mastery": 0.6, ...}
]
```

---

## 📊 Phase 3.3: Dashboard Analytics (A)

**Goal:** Overview page showing learning progress

### Dashboard Components

1. **Overall Stats Card**
   - Total items studied
   - Average Memory Power
   - Items due today
   - Current streak

2. **Memory Power Distribution**
   - Pie/bar chart showing strong/medium/weak
   - Percentage breakdown
   - Clickable to filter

3. **Container List**
   - Each flashcard set shows:
     - Average Memory Power
     - Progress bar
     - Due count

4. **Recent Activity**
   - Last 10 reviews
   - Show Memory Power changes
   - Highlight improvements

### UI Mockup

```
┌────────────────────────────────────────────────────┐
│ 📚 Learning Dashboard                              │
├────────────────────────────────────────────────────┤
│                                                    │
│ ┌──────────────┐ ┌──────────────┐ ┌─────────────┐│
│ │ 📈 Avg. MP   │ │ 📅 Due Today │ │ 🔥 Streak   ││
│ │    72%       │ │     45       │ │     12      ││
│ └──────────────┘ └──────────────┘ └─────────────┘│
│                                                    │
│ Memory Power Distribution:                        │
│ 🟢 Strong (80-100%):  156 items (31%)             │
│ 🟡 Medium (50-80%):   278 items (56%)             │
│ 🔴 Weak (0-50%):       66 items (13%)             │
│                                                    │
│ Your Sets:                                         │
│ ┌────────────────────────────────────────────┐   │
│ │ TOEIC Vocabulary                           │   │
│ │ Memory Power: [██████████░░] 78%           │   │
│ │ 45 due • 342 studied                       │   │
│ └────────────────────────────────────────────┘   │
└────────────────────────────────────────────────────┘
```

---

## 🔍 Phase 3.4: Item Detail View (C)

**Goal:** Deep dive into single item metrics

### Features

1. **Current Stats**
   - Current Memory Power %
   - Mastery level
   - Retention rate
   - Next review time with countdown

2. **History Chart**
   - Memory Power over time
   - Show mastery and retention separately
   - Mark review sessions

3. **Review History**
   - List of past reviews
   - Quality scores
   - Time intervals

4. **Actions**
   - "Review Now" button
   - "Reset Progress" option
   - "Mark as Mastered"

---

## 🎨 Design Principles

1. **Progressive Disclosure**
   - Basic view: Just Memory Power %
   - Expanded: Show mastery + retention breakdown
   - Detail view: Full history and charts

2. **Color Coding**
   - 🟢 Green: 80-100% (Strong)
   - 🟡 Yellow: 50-80% (Medium)
   - 🔴 Red: 0-50% (Weak)

3. **Performance**
   - Cache calculated metrics where possible
   - Lazy load charts
   - Batch API requests

4. **Mobile First**
   - Touch-friendly
   - Swipe gestures
   - Compact layouts

---

## Implementation Order

```
Phase 3.1 (B): In-Session Stats
  └─ Flashcard session widget
  └─ Mobile stats modal
  
Phase 3.2 (D): API Endpoints
  └─ Item stats API
  └─ Container stats API
  └─ Batch stats API
  
Phase 3.3 (A): Dashboard
  └─ Overall stats
  └─ Distribution chart
  └─ Container list
  
Phase 3.4 (C): Item Detail
  └─ Detail modal
  └─ History chart
  └─ Actions
```

**Estimated Effort:**
- 3.1: 2-3 hours
- 3.2: 1-2 hours
- 3.3: 3-4 hours
- 3.4: 2-3 hours

**Total: ~10 hours for full Phase 3**

---

Ready to start with 3.1! 🚀
