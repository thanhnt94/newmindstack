"""
Rewrite MCQ session.html header to match Flashcard style exactly

Flashcard style has:
- Row 1: Orange pill "FLASHCARD" left, icon buttons right (AI, Note, Audio, Stats, Settings, Home, Exit)
- Row 2: Stats - Tiến độ | Đã thuộc | Học lại | Bộ thẻ (title)

MCQ will have:
- Row 1: Blue pill "MCQ" left, icon buttons right (Home, Exit only for MCQ)
- Row 2: Stats - Tiến độ | Đúng | Sai | Bộ thẻ (title)
"""

import re

path = r'c:\Code\MindStack\newmindstack\mindstack_app\modules\learning\vocabulary\mcq\templates\mcq\session.html'

with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

# New header CSS - matching Flashcard style exactly
new_header_css = '''
    /* ===== Header - Matching Flashcard Style ===== */
    .session-header {
        position: sticky;
        top: 0;
        z-index: 40;
        background: white;
        border-bottom: 1px solid #e2e8f0;
        padding: 0;
    }

    /* Context Bar - Row 1 */
    .mcq-context-bar {
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 0.5rem 0.75rem;
        background: #f8fafc;
        border-bottom: 1px solid #e2e8f0;
    }

    .mcq-context-pill {
        display: inline-flex;
        align-items: center;
        gap: 0.375rem;
        padding: 0.25rem 0.625rem;
        background: linear-gradient(135deg, #6366f1, #4f46e5);
        color: white;
        font-size: 0.625rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        border-radius: 100px;
    }

    .mcq-nav-btns {
        display: flex;
        gap: 0.5rem;
    }

    .mcq-nav-btn {
        width: 32px;
        height: 32px;
        border-radius: 50%;
        background: #f1f5f9;
        border: none;
        display: flex;
        align-items: center;
        justify-content: center;
        color: #64748b;
        text-decoration: none;
        transition: all 0.2s;
        cursor: pointer;
    }

    .mcq-nav-btn:active {
        background: #e2e8f0;
    }

    /* Stats Row - Row 2 */
    .mcq-stats-row {
        display: flex;
        align-items: center;
        padding: 0.75rem 1rem;
        gap: 0.75rem;
        background: white;
    }

    .mcq-stat-item {
        display: flex;
        flex-direction: column;
        align-items: center;
        flex-shrink: 0;
    }

    .mcq-stat-label {
        font-size: 0.625rem;
        font-weight: 700;
        color: #94a3b8;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }

    .mcq-stat-value {
        font-size: 1rem;
        font-weight: 900;
        color: #1e293b;
        font-variant-numeric: tabular-nums;
    }

    .mcq-stat-value.correct {
        color: #10b981;
    }

    .mcq-stat-value.wrong {
        color: #ef4444;
    }

    .mcq-stat-divider {
        width: 1px;
        height: 24px;
        background: #e2e8f0;
        flex-shrink: 0;
    }

    .mcq-title-group {
        flex: 1;
        display: flex;
        flex-direction: column;
        align-items: center;
        text-align: center;
        overflow: hidden;
    }

    .mcq-title-label {
        font-size: 0.625rem;
        font-weight: 700;
        color: #94a3b8;
        text-transform: uppercase;
    }

    .mcq-title-text {
        font-size: 0.8125rem;
        font-weight: 700;
        color: #334155;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
        max-width: 100%;
    }
'''

# New header HTML - matching Flashcard structure
new_header_html = '''<header class="session-header">
        <!-- Context Bar - Row 1 -->
        <div class="mcq-context-bar">
            <span class="mcq-context-pill">
                <i class="fas fa-list-check"></i>
                <span>MCQ</span>
            </span>
            <div class="mcq-nav-btns">
                <a href="/" class="mcq-nav-btn" title="Trang chủ">
                    <i class="fas fa-house" style="font-size: 0.75rem;"></i>
                </a>
                <a href="{{ url_for('learning.vocabulary.dashboard') }}" class="mcq-nav-btn" title="Thoát">
                    <i class="fas fa-right-from-bracket" style="font-size: 0.75rem;"></i>
                </a>
            </div>
        </div>

        <!-- Stats Row - Row 2 -->
        <div class="mcq-stats-row">
            <div class="mcq-stat-item">
                <span class="mcq-stat-label">Tiến độ</span>
                <span class="mcq-stat-value"><span id="current-q-num">1</span>/<span id="total-q-num">...</span></span>
            </div>
            <div class="mcq-stat-divider"></div>
            <div class="mcq-stat-item">
                <span class="mcq-stat-label">Đúng</span>
                <span class="mcq-stat-value correct" id="live-correct">0</span>
            </div>
            <div class="mcq-stat-divider"></div>
            <div class="mcq-stat-item">
                <span class="mcq-stat-label">Sai</span>
                <span class="mcq-stat-value wrong" id="live-wrong">0</span>
            </div>
            <div class="mcq-stat-divider"></div>
            <div class="mcq-title-group">
                <span class="mcq-title-label">Bộ thẻ</span>
                <span class="mcq-title-text">{{ container.title }}</span>
            </div>
        </div>
    </header>'''

# Replace old header CSS (from "/* Header */" to before "/* Progress Bar */")
old_header_css_pattern = r'/\* Header \*/.*?(?=/\* Progress Bar \*/)'
content = re.sub(old_header_css_pattern, new_header_css + '\n\n    /* Progress Bar */\n', content, flags=re.DOTALL)

# Replace old header HTML
old_header_html_pattern = r'<header class="session-header">.*?</header>'
content = re.sub(old_header_html_pattern, new_header_html, content, flags=re.DOTALL)

# Also need to remove old CSS that's no longer needed (back-btn, progress-container, live-stats, stat-badge)
# These are replaced by mcq-* classes

# Fix main content padding to account for sticky header
content = content.replace(
    '.session-main {',
    '.session-main {\n        padding-top: 1rem; /* Extra padding for sticky header */\n       '
)

with open(path, 'w', encoding='utf-8') as f:
    f.write(content)

# Verify
with open(path, 'r', encoding='utf-8') as f:
    new_content = f.read()

checks = [
    ('mcq-context-bar', 'context bar class'),
    ('mcq-stats-row', 'stats row class'),
    ('mcq-context-pill', 'context pill class'),
    ('id="current-q-num"', 'current question ID'),
    ('id="total-q-num"', 'total question ID'),
]

print("Checking MCQ header update:")
for pattern, desc in checks:
    if pattern in new_content:
        print(f"  ✓ {desc}")
    else:
        print(f"  ✗ {desc}")

print("\nDone!")
