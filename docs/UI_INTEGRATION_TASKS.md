# UI Integration Task Breakdown

## Phase 4.1: Session Widget Integration (Priority 1) ⭐

**Goal:** Add Memory Power widget to flashcard session

**Time:** 30 minutes

### Tasks:

1. **Edit session template**
   - File: `mindstack_app/modules/learning/sub_modules/flashcard/individual/session/default/index.html`
   - Add CSS link in `<head>`
   - Include widget component
   - Add JS file before `</body>`

2. **Position widget**
   - Desktop: Right sidebar or below card
   - Mobile: Below card content
   - Test both layouts

3. **Verify**
   - Widget HTML renders
   - CSS loads correctly
   - JS initializes without errors

---

## Phase 4.2: JavaScript Update (Priority 1) ⭐

**Goal:** Wire up widget to update after answer

**Time:** 20 minutes

### Tasks:

1. **Find answer handler**
   - Locate fetch/AJAX call to answer endpoint
   - Usually in `_desktop.html` or separate JS file

2. **Add widget update**
   ```javascript
   if (response.memory_power) {
       updateMemoryPowerFromResponse(response);
   }
   ```

3. **Test**
   - Answer flashcard
   - Check widget updates
   - Verify console for errors

---

## Phase 4.3: Navigation (Priority 2)

**Goal:** Add links to dashboard

**Time:** 15 minutes

### Tasks:

1. **Main navbar**
   - Add "Analytics" link
   - Icon: `<i class="fas fa-chart-line"></i>`

2. **Flashcard dashboard**
   - Add dashboard card/link
   - Quick stats preview

3. **Test navigation**
   - Links work
   - Active states correct

---

## Phase 4.4: Stats Modal (Priority 2)

**Goal:** Show detailed stats for current card

**Time:** 20 minutes

### Tasks:

1. **Add button to card**
   - "View Stats" button
   - Only show when item has progress

2. **Include modal**
   - Add `{% include '_item_detail_modal.html' %}`

3. **Wire up function**
   - `showItemDetail(itemId)`
   - Fetch from API
   - Display in modal

---

## Phase 4.5: Mobile (Priority 3)

**Goal:** Optimize for mobile

**Time:** 30 minutes

### Tasks:

1. **Update mobile stats modal**
   - Add Memory Power section
   - Format for small screens

2. **Test layouts**
   - Widget responsive
   - Modal readable
   - Buttons touch-friendly

---

## Phase 4.6: Container List (Priority 3)

**Goal:** Show Memory Power on set list

**Time:** 20 minutes

### Tasks:

1. **Add badge to each set**
   - Fetch container stats
   - Display colored badge
   - Show percentage

2. **Loading states**
   - Show "Loading..." initially
   - Handle errors gracefully

---

## Quick Implementation Order

### Minimal (15 min) - Get it working
1. Add widget to template (4.1)
2. Update answer handler (4.2)
3. Test!

### Standard (1 hour) - Good UX
1. Minimal +
2. Add navigation (4.3)
3. Stats modal (4.4)

### Complete (2 hours) - Full features
1. Standard +
2. Mobile optimization (4.5)
3. Container list (4.6)

---

## Files to Edit

### Priority 1 (Must have)
1. `individual/session/default/index.html` - Main template
2. Answer handler JS - Update response handling

### Priority 2 (Should have)
3. `base.html` or navbar - Add dashboard link
4. Session template - Add stats button
5. Session template - Include modal

### Priority 3 (Nice to have)
6. `_stats_mobile.html` - Mobile stats
7. Set list template - Add badges

---

## Testing Checklist

After each phase:
- [ ] No console errors
- [ ] Widget displays correctly
- [ ] Data is accurate
- [ ] Mobile responsive
- [ ] Performance good (<100ms)

---

## Ready to Start!

**Recommend:** Start with Phase 4.1 + 4.2 (minimal 15 min implementation)

This will get Memory Power displaying immediately! 🚀
