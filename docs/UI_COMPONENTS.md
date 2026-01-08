# MindStack UI Components

## Overview

Thư viện UI components tái sử dụng trong MindStack.

---

## 📁 Component Structure

```
templates/v3/includes/
├── ai_services/          # AI-related UI
├── assets/               # Asset includes
├── chat/                 # Chat components
├── modals/               # Modal dialogs
├── navbar/               # Navigation bars
├── notification/         # Notifications
├── pagination/           # Paging controls
└── search/               # Search components
```

---

## 🔔 Notifications

### Score Toast

**Location:** `includes/notification/_score_toast.html`

Hiển thị điểm thưởng khi trả lời đúng.

```jinja
{% include 'v3/includes/notification/_score_toast.html' %}
```

**JavaScript API:**
```javascript
// Show score notification
showScoreToast({
    points: 15,
    reason: 'Trả lời đúng',
    total_score: 1500
});
```

**Styling:**
```css
.score-toast {
    position: fixed;
    top: 20px;
    right: 20px;
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    border-radius: 12px;
    animation: slideIn 0.3s ease-out;
}
```

---

### Memory Power Notification

**Location:** `includes/notification/_memory_power.html`

Hiển thị Memory Power sau mỗi câu trả lời.

```jinja
{% include 'v3/includes/notification/_memory_power.html' %}
```

**JavaScript API:**
```javascript
showMemoryPower({
    current: 0.75,
    previous: 0.60,
    change: 0.15,
    mastery: 0.80,
    retention: 0.94
});
```

**Features:**
- Animated progress bar
- Color-coded levels (green/yellow/red)
- Mastery & Retention breakdown

---

## 🗂️ Modals

### Stats Modal

**Location:** `includes/modals/_modal_stats.html`

Modal hiển thị thống kê chi tiết cho item.

```jinja
{% include 'v3/includes/modals/_modal_stats.html' %}
```

**JavaScript API:**
```javascript
// Open stats modal
openStatsModal(itemId, 'flashcard');

// Close modal
closeStatsModal();
```

**Contents:**
- Item content (front/back)
- SRS status & metrics
- Review history
- AI explanations
- User notes

---

### Generic Modal Pattern

```html
<div class="modal-overlay" id="myModal">
    <div class="modal-container">
        <div class="modal-header">
            <h3>Modal Title</h3>
            <button class="modal-close" onclick="closeModal('myModal')">×</button>
        </div>
        <div class="modal-body">
            <!-- Content -->
        </div>
        <div class="modal-footer">
            <button class="btn btn-secondary" onclick="closeModal('myModal')">Cancel</button>
            <button class="btn btn-primary" onclick="confirmAction()">Confirm</button>
        </div>
    </div>
</div>
```

```css
.modal-overlay {
    position: fixed;
    inset: 0;
    background: rgba(0, 0, 0, 0.5);
    display: flex;
    align-items: center;
    justify-content: center;
    z-index: 1000;
    opacity: 0;
    visibility: hidden;
    transition: all 0.3s ease;
}

.modal-overlay.active {
    opacity: 1;
    visibility: visible;
}

.modal-container {
    background: white;
    border-radius: 16px;
    max-width: 500px;
    width: 90%;
    max-height: 80vh;
    overflow-y: auto;
}
```

---

## 🧭 Navigation

### Session Header

**Location:** `includes/navbar/_session_header.html`

Header cho learning sessions (mobile-optimized).

```jinja
{% include 'v3/includes/navbar/_session_header.html' %}
```

**Props:**
- `set_title` - Tên bộ thẻ
- `mode` - Chế độ học
- `progress` - Tiến độ hiện tại

---

### Standard Navbar

```jinja
{% include 'v3/includes/navbar/_navbar.html' %}
```

**Features:**
- Responsive (mobile/desktop)
- User menu
- Notifications badge
- Search

---

## 📄 Pagination

**Location:** `includes/pagination/`

```jinja
{% include 'v3/includes/pagination/_pagination.html' with context %}
```

**Variables:**
```python
# Trong route
return render_template('page.html',
    pagination={
        'page': 1,
        'per_page': 12,
        'total': 100,
        'pages': 9
    }
)
```

---

## 🔍 Search

**Location:** `includes/search/`

```jinja
{% include 'v3/includes/search/_search_bar.html' %}
```

**Features:**
- Debounced input
- AJAX suggestions
- Category filters

---

## 🎨 Common Patterns

### Button Styles

```css
/* Primary Button */
.btn-primary {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    color: white;
    padding: 12px 24px;
    border-radius: 8px;
    border: none;
    cursor: pointer;
    transition: transform 0.2s, box-shadow 0.2s;
}

.btn-primary:hover {
    transform: translateY(-2px);
    box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4);
}

/* Secondary Button */
.btn-secondary {
    background: #f0f0f0;
    color: #333;
    padding: 12px 24px;
    border-radius: 8px;
}

/* Icon Button */
.btn-icon {
    width: 40px;
    height: 40px;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
}
```

---

### Card Styles

```css
.card {
    background: white;
    border-radius: 16px;
    box-shadow: 0 4px 20px rgba(0, 0, 0, 0.08);
    padding: 20px;
    transition: transform 0.3s, box-shadow 0.3s;
}

.card:hover {
    transform: translateY(-4px);
    box-shadow: 0 8px 30px rgba(0, 0, 0, 0.12);
}

.card-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 16px;
}

.card-body {
    color: #666;
}
```

---

### Loading States

```html
<!-- Skeleton Loader -->
<div class="skeleton">
    <div class="skeleton-line"></div>
    <div class="skeleton-line short"></div>
</div>

<!-- Spinner -->
<div class="spinner"></div>
```

```css
.skeleton-line {
    height: 16px;
    background: linear-gradient(90deg, #f0f0f0 25%, #e0e0e0 50%, #f0f0f0 75%);
    background-size: 200% 100%;
    animation: shimmer 1.5s infinite;
    border-radius: 4px;
    margin-bottom: 8px;
}

@keyframes shimmer {
    0% { background-position: -200% 0; }
    100% { background-position: 200% 0; }
}

.spinner {
    width: 40px;
    height: 40px;
    border: 3px solid #f0f0f0;
    border-top-color: #667eea;
    border-radius: 50%;
    animation: spin 1s linear infinite;
}

@keyframes spin {
    to { transform: rotate(360deg); }
}
```

---

## 📱 Responsive Patterns

### Mobile-First Grid

```css
.grid {
    display: grid;
    gap: 16px;
    grid-template-columns: 1fr;
}

@media (min-width: 640px) {
    .grid {
        grid-template-columns: repeat(2, 1fr);
    }
}

@media (min-width: 1024px) {
    .grid {
        grid-template-columns: repeat(3, 1fr);
    }
}
```

### Hide/Show by Device

```css
/* Mobile only */
.mobile-only {
    display: block;
}
@media (min-width: 1024px) {
    .mobile-only { display: none; }
}

/* Desktop only */
.desktop-only {
    display: none;
}
@media (min-width: 1024px) {
    .desktop-only { display: block; }
}
```

---

## 🎭 Animations

### Micro-interactions

```css
/* Button press */
.btn:active {
    transform: scale(0.95);
}

/* Card hover lift */
.card:hover {
    transform: translateY(-4px);
}

/* Fade in */
@keyframes fadeIn {
    from { opacity: 0; transform: translateY(10px); }
    to { opacity: 1; transform: translateY(0); }
}

.fade-in {
    animation: fadeIn 0.3s ease-out;
}

/* Slide in from right */
@keyframes slideInRight {
    from { transform: translateX(100%); }
    to { transform: translateX(0); }
}
```

---

## 📚 Usage Examples

### Complete Modal Example

```jinja
{# In your template #}
<button onclick="openConfirmModal()">Delete Item</button>

<div class="modal-overlay" id="confirmModal">
    <div class="modal-container">
        <div class="modal-header">
            <h3>Xác nhận xóa</h3>
            <button class="modal-close" onclick="closeModal('confirmModal')">×</button>
        </div>
        <div class="modal-body">
            <p>Bạn có chắc muốn xóa item này?</p>
        </div>
        <div class="modal-footer">
            <button class="btn btn-secondary" onclick="closeModal('confirmModal')">
                Hủy
            </button>
            <button class="btn btn-danger" onclick="confirmDelete()">
                Xóa
            </button>
        </div>
    </div>
</div>

<script>
function openModal(id) {
    document.getElementById(id).classList.add('active');
}

function closeModal(id) {
    document.getElementById(id).classList.remove('active');
}

function openConfirmModal() {
    openModal('confirmModal');
}

function confirmDelete() {
    // Delete logic
    closeModal('confirmModal');
}
</script>
```

---

## 📚 References

- [coding_standards.md](../standards/coding_standards.md) - Template patterns
- [ARCHITECTURE.md](ARCHITECTURE.md) - System overview
