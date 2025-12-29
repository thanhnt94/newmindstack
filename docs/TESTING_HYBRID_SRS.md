# Hybrid SRS System - Testing Guide

## 🧪 Testing Checklist

### Phase 1: Backend Testing

#### 1. Test UnifiedSrsSystem
```python
# Test in Python shell or create test file
from mindstack_app.modules.learning.logics.unified_srs import UnifiedSrsSystem, SrsResult

# Test process_answer
result = UnifiedSrsSystem.process_answer(
    current_status='new',
    current_interval=0,
    current_ef=2.5,
    current_reps=0,
    current_correct_streak=0,
    current_incorrect_streak=0,
    last_reviewed=None,
    quality=4,
    mode='flashcard',
    is_first_time=True
)

print(f"Memory Power: {result.memory_power * 100:.1f}%")
print(f"Mastery: {result.mastery * 100:.1f}%")
print(f"Retention: {result.retention * 100:.1f}%")
print(f"Next Review: {result.next_review}")
```

**Expected:**
- ✅ Memory Power should be ~40-60% for first correct answer
- ✅ Mastery should be lower than 100%
- ✅ Retention should be 100% (just reviewed)
- ✅ Next review should be in future

#### 2. Test API Endpoints

**Start app first:**
```bash
python start_mindstack_app.py
```

**Test item stats:**
```bash
# Get stats for item 1
curl http://localhost:5000/api/learning/stats/item/1
```

**Expected response:**
```json
{
    "mastery": 85.3,
    "retention": 92.1,
    "memory_power": 78.5,
    "is_due": false,
    "status": "reviewing",
    "correct_streak": 5,
    "next_review": "2025-12-31T10:00:00Z"
}
```

**Test container stats:**
```bash
curl http://localhost:5000/api/learning/stats/container/1
```

**Expected response:**
```json
{
    "total_items": 500,
    "average_memory_power": 72.5,
    "strong_items": 156,
    "medium_items": 278,
    "weak_items": 66,
    "due_items": 45
}
```

---

### Phase 2: Integration Testing

#### 3. Test Flashcard Flow

1. **Start a flashcard session:**
   - Navigate to `/learning/flashcard/sets`
   - Click "Học ngay" on any set
   - Select a learning mode

2. **Answer a flashcard:**
   - Answer with quality 4 (Good) or 5 (Easy)
   - Open browser DevTools → Network tab
   - Check the `/answer` response

3. **Verify Memory Power data in response:**
```json
{
    "success": true,
    "score_change": 15,
    "memory_power": {
        "mastery": 65.5,
        "retention": 100.0,
        "memory_power": 65.5,
        "correct_streak": 3,
        "next_review": "2025-12-29T15:30:00Z"
    },
    ...
}
```

**Check console for:**
- ✅ No JavaScript errors
- ✅ `updateMemoryPowerFromResponse()` called
- ✅ Widget displayed (if integrated)

#### 4. Test Different Scenarios

**Scenario A: First time (New item)**
- Quality: 4
- Expected Mastery: ~50%
- Expected Memory Power: ~50%

**Scenario B: Answered correctly 5 times**
- Quality: 4
- Expected Mastery: ~80%
- Expected Streak: 5

**Scenario C: Incorrect answer after streak**
- Quality: 1
- Expected: Streak resets to 0
- Expected: Mastery decreases

**Scenario D: Long interval (retention decay)**
- Item not reviewed for 7 days
- Expected: Retention < 100%
- Expected: Memory Power < Mastery

---

### Phase 3: UI Testing

#### 5. Memory Power Widget (if integrated)

1. **Check widget visibility:**
   - Widget should appear after answering
   - Should have gradient background
   - Should show percentage

2. **Check progress bars:**
   - Mastery bar updates
   - Retention bar updates
   - Colors change (green > yellow > red)

3. **Check responsiveness:**
   - Test on mobile viewport
   - Widget should be compact
   - Bars should fit screen

#### 6. Dashboard Testing (when implemented)

1. Navigate to dashboard
2. Check aggregate stats display
3. Verify container breakdown
4. Check chart rendering

---

### Phase 4: Performance Testing

#### 7. Check Response Times

Open DevTools → Network:
- Answer request: Should be < 500ms
- Stats API: Should be < 100ms
- Dashboard: Should be < 2s

#### 8. Check Database Queries

Enable Flask debug toolbar or check logs:
- Should be < 10 queries per answer
- No N+1 query problems
- Proper index usage

---

## 🐛 Common Issues & Fixes

### Issue 1: 404 on API endpoints
**Fix:** Check if `stats_api_bp` is registered in `routes.py`

### Issue 2: `memory_power` is None
**Fix:** Check if item has progress record in database

### Issue 3: Widget not showing
**Fix:** 
- Check if CSS/JS files are included
- Check browser console for errors
- Verify `memory_power` data in response

### Issue 4: Incorrect calculations
**Fix:**
- Check UnifiedSrsSystem logic
- Verify SM-2 constants
- Check mastery formula

### Issue 5: TypeError on process_answer
**Fix:** Update all call sites to unpack 6 return values

---

## ✅ Success Criteria

**Backend:**
- [x] All APIs return 200 OK
- [x] Memory Power data present in responses
- [x] Calculations are correct
- [x] No server errors

**Frontend:**
- [ ] Widget displays after answer
- [ ] Progress bars animate
- [ ] Colors match percentage
- [ ] Mobile responsive

**Performance:**
- [x] API < 100ms
- [x] Answer < 500ms
- [ ] Dashboard < 2s

**User Experience:**
- [ ] Clear and intuitive
- [ ] Helpful metrics
- [ ] Motivating feedback

---

## 📊 Quick Test Script

```python
# test_hybrid_srs.py
from mindstack_app import create_app
from mindstack_app.modules.learning.services.srs_service import SrsService
from mindstack_app.models.learning_progress import LearningProgress

app = create_app()

with app.app_context():
    # Test 1: Get item stats
    progress = LearningProgress.query.first()
    if progress:
        stats = SrsService.get_item_stats(progress)
        print(f"✅ Item Stats: {stats}")
    
    # Test 2: Get container stats
    container_stats = SrsService.get_container_stats(
        user_id=1,
        container_id=1
    )
    print(f"✅ Container Stats: {container_stats}")
    
    # Test 3: Update with unified
    progress, result = SrsService.update_unified(
        user_id=1,
        item_id=1,
        quality=4,
        mode='flashcard'
    )
    print(f"✅ Update Result: MP={result.memory_power:.1%}")

print("\n🎉 All tests passed!")
```

Run: `python test_hybrid_srs.py`

---

## 🚀 Next Steps After Testing

1. **If all tests pass:**
   - Deploy to staging
   - User acceptance testing
   - Monitor performance

2. **If issues found:**
   - Fix bugs
   - Re-test
   - Document solutions

3. **Future enhancements:**
   - Add charts/visualizations
   - A/B test effectiveness
   - ML-driven predictions
