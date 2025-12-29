# Integration Plan - Memory Power UI cho Flashcard

## Mục tiêu
Tích hợp Memory Power statistics vào giao diện flashcard để người dùng thấy được:
1. Memory Power % sau mỗi câu trả lời
2. Thanh progress bar cho Mastery/Retention
3. Link đến Dashboard analytics
4. Item detail view (click để xem chi tiết)

---

## Phase 1: Flashcard Session Integration

### 1.1. Thêm Memory Power Widget vào Template

**Files cần edit:**
- `mindstack_app/modules/learning/sub_modules/flashcard/individual/session/default/index.html`

**Changes:**

```html
<!-- Trong <head> section -->
<link rel="stylesheet" href="{{ url_for('static', filename='css/memory_power_widget.css') }}">

<!-- Trong body, sau card display (vị trí hiển thị widget) -->
{% include 'learning/components/_memory_power_widget.html' %}

<!-- Trước </body> -->
<script src="{{ url_for('static', filename='js/memory_power_widget.js') }}"></script>
```

**Vị trí đề xuất:** Đặt widget ở sidebar (desktop) hoặc dưới card (mobile)

---

### 1.2. Update JavaScript Answer Handler

**File:** `mindstack_app/modules/learning/sub_modules/flashcard/individual/session/default/_desktop.html` hoặc JS file tương ứng

**Find:** Đoạn code xử lý answer response (thường là fetch `/answer`)

**Add:**
```javascript
// Sau khi nhận response từ answer endpoint
fetch('/learning/flashcard/answer', {
    method: 'POST',
    body: formData
})
.then(r => r.json())
.then(response => {
    // Existing code: update score, next card, etc...
    
    // NEW: Update Memory Power widget
    if (response.memory_power && window.memoryPowerWidget) {
        memoryPowerWidget.update(response.memory_power);
    }
});
```

---

### 1.3. Add Dashboard Link

**File:** Navigation bar template (navbar hoặc sidebar)

**Add:**
```html
<li class="nav-item">
    <a href="{{ url_for('learning_dashboard.index') }}" class="nav-link">
        <i class="fas fa-chart-line"></i>
        Learning Analytics
    </a>
</li>
```

---

## Phase 2: Stats Modal for Current Card

### 2.1. Thêm Stats Button vào Card

**File:** Card template (trong flashcard session)

**Add button:**
```html
<button class="btn btn-info btn-sm" onclick="showCurrentCardStats({{ current_item_id }})">
    <i class="fas fa-chart-bar"></i> View Stats
</button>
```

---

### 2.2. Include Item Detail Modal

**File:** Session template

**Add:**
```html
<!-- Before </body> -->
{% include 'learning/components/_item_detail_modal.html' %}
```

---

## Phase 3: Dashboard Integration

### 3.1. Add Dashboard to Main Navigation

**Files:**
- `mindstack_app/templates/base.html` (hoặc navbar template)

**Add link:**
```html
<li><a href="/learning/dashboard/">📊 Analytics</a></li>
```

---

### 3.2. Create Dashboard Card on Homepage

**File:** Learning module homepage

**Add card:**
```html
<div class="dashboard-card">
    <h3>Learning Analytics</h3>
    <p>Track your Memory Power and progress</p>
    <a href="/learning/dashboard/" class="btn btn-primary">View Dashboard</a>
</div>
```

---

## Phase 4: Mobile Optimization

### 4.1. Update Mobile Stats Modal

**File:** `_stats_mobile.html`

**Add Memory Power tab:**
```html
<div class="tab-pane" id="memory-power-tab">
    <h6>Memory Power</h6>
    <div id="mobile-mp-display"></div>
</div>
```

**Add JavaScript:**
```javascript
function updateMobileStats(data) {
    if (data.memory_power) {
        document.getElementById('mobile-mp-display').innerHTML = `
            <div class="mp-stat">
                <strong>Memory Power:</strong> ${data.memory_power.memory_power}%
            </div>
            <div class="mp-stat">
                <strong>Mastery:</strong> ${data.memory_power.mastery}%
            </div>
            <div class="mp-stat">
                <strong>Retention:</strong> ${data.memory_power.retention}%
            </div>
        `;
    }
}
```

---

## Phase 5: Container List Integration

### 5.1. Add Memory Power to Flashcard Set List

**File:** Flashcard set list template

**Modify each set card to show:**
```html
<div class="set-stats">
    <span class="memory-power" data-container-id="{{ set.id }}">
        Loading...
    </span>
</div>

<script>
// Fetch container stats
fetch(`/api/learning/stats/container/{{ set.id }}`)
    .then(r => r.json())
    .then(data => {
        document.querySelector(`[data-container-id="{{ set.id }}"]`).innerHTML = `
            <span class="badge ${getColorClass(data.average_memory_power)}">
                ${data.average_memory_power}% Memory Power
            </span>
        `;
    });
</script>
```

---

## Implementation Checklist

### Priority 1 (Core functionality)
- [ ] Add Memory Power widget to session template
- [ ] Update answer handler JavaScript
- [ ] Test widget updates after answering
- [ ] Verify mobile responsiveness

### Priority 2 (Enhanced UX)
- [ ] Add stats button to card
- [ ] Include item detail modal
- [ ] Add dashboard link to navbar
- [ ] Test modal functionality

### Priority 3 (Dashboard)
- [ ] Create dashboard homepage link
- [ ] Test dashboard page
- [ ] Verify all charts load correctly
- [ ] Add loading states

### Priority 4 (Polish)
- [ ] Mobile stats modal enhancement
- [ ] Container list integration
- [ ] Performance optimization
- [ ] Cross-browser testing

---

## Quick Start Guide

### Minimal Integration (15 minutes)

1. **Add widget to session:**
   ```html
   <!-- In flashcard session index.html -->
   <link rel="stylesheet" href="{{ url_for('static', filename='css/memory_power_widget.css') }}">
   {% include 'learning/components/_memory_power_widget.html' %}
   <script src="{{ url_for('static', filename='js/memory_power_widget.js') }}"></script>
   ```

2. **Update answer handler:**
   ```javascript
   // Find existing answer handler, add:
   if (response.memory_power) {
       updateMemoryPowerFromResponse(response);
   }
   ```

3. **Test:** Answer a flashcard → Widget should update

---

## Files to Modify

### Templates
1. `individual/session/default/index.html` - Main session template
2. `individual/session/default/_desktop.html` - Desktop layout
3. `individual/session/default/_mobile.html` - Mobile layout
4. `templates/base.html` - Add dashboard link
5. Set list template - Add Memory Power badges

### JavaScript
1. Answer handler - Add widget update call
2. Mobile stats - Add Memory Power display

### CSS (Optional)
1. Custom styles for widget positioning
2. Responsive adjustments

---

## Testing Plan

### 1. Widget Display
- [ ] Widget appears after first answer
- [ ] Progress bars animate correctly
- [ ] Colors change based on percentage
- [ ] Mobile layout is readable

### 2. Data Flow
- [ ] API returns memory_power data
- [ ] JavaScript receives and processes data
- [ ] Widget updates with correct values
- [ ] No console errors

### 3. Navigation
- [ ] Dashboard link works
- [ ] Modal opens correctly
- [ ] Stats load properly
- [ ] Back navigation works

### 4. Performance
- [ ] Widget update < 100ms
- [ ] No layout shift
- [ ] Smooth animations
- [ ] No memory leaks

---

## Rollback Plan

If issues occur:
1. Comment out widget include
2. Remove JavaScript update call
3. System works as before (backward compatible)

---

## Next Steps After Flashcard

Once flashcard integration is complete:
1. Apply same pattern to Quiz
2. Add to Vocabulary modules
3. Create unified learning navbar
4. Add cross-module analytics

---

**Estimated Time:**
- Phase 1: 30 minutes
- Phase 2: 20 minutes  
- Phase 3: 15 minutes
- Phase 4: 30 minutes
- Phase 5: 20 minutes

**Total: ~2 hours for full integration**

**Minimum viable: 15 minutes (Phase 1 only)**
