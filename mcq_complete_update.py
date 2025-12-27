"""
Complete MCQ Header Update Script
Applies Flashcard-style header AND fixes all JS references in one go
"""

path = r'c:\Code\MindStack\newmindstack\mindstack_app\modules\learning\vocabulary\mcq\templates\mcq\session.html'

with open(path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Build new content line by line
new_lines = []
in_header_css = False
skip_until_progress = False
in_old_header_html = False
skip_header_html = False

i = 0
while i < len(lines):
    line = lines[i]
    
    # === Part 1: Replace Header CSS ===
    if '/* Header */' in line:
        # Insert new header CSS
        new_header_css = '''
    /* ===== Header - Flashcard Style 2-Row Layout ===== */
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
        new_lines.append(new_header_css)
        skip_until_progress = True
        i += 1
        continue
    
    if skip_until_progress:
        if '/* Progress Bar */' in line or '.back-btn' in line:
            skip_until_progress = False
            # Skip old header CSS section entirely
            while i < len(lines) and '.back-btn' not in lines[i]:
                i += 1
            # Now skip .back-btn section too
            while i < len(lines) and '.progress-container {' not in lines[i]:
                i += 1
            # Skip progress-container section
            while i < len(lines) and '/* Live Stats in Header */' not in lines[i]:
                i += 1
            # Skip live-stats section
            while i < len(lines) and '/* Main Content */' not in lines[i]:
                i += 1
            continue
        else:
            i += 1
            continue
    
    # === Part 2: Replace Header HTML ===
    if '<header class="session-header">' in line:
        # Add new header HTML
        new_header_html = '''    <header class="session-header">
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
    </header>
'''
        new_lines.append(new_header_html)
        # Skip old header HTML
        while i < len(lines) and '</header>' not in lines[i]:
            i += 1
        i += 1  # Skip </header> line
        continue
    
    # === Part 3: Fix JS - Remove pBar and pPer ===
    if "pBar: document.getElementById('progress-bar')" in line:
        i += 1  # Skip this line
        continue
    
    if "pPer: document.getElementById('progress-percent')" in line:
        i += 1  # Skip this line
        continue
    
    # Remove pBar.style.width and pPer.textContent usage in renderQuestion
    if 'els.pBar.style.width' in line:
        i += 1
        continue
    if 'els.pPer.textContent' in line:
        i += 1
        continue
    
    new_lines.append(line)
    i += 1

# Write back
with open(path, 'w', encoding='utf-8') as f:
    f.writelines(new_lines)

# Verify
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

checks = [
    ('mcq-context-bar', 'New context bar CSS'),
    ('mcq-stats-row', 'New stats row CSS'),
    ('<span class="mcq-context-pill">', 'New header HTML'),
    ('id="current-q-num"', 'Current Q num ID kept'),
    ('id="total-q-num"', 'Total Q num ID kept'),
    ('pBar' not in content, 'pBar removed'),
    ('pPer' not in content, 'pPer removed'),
]

print("Verification:")
all_ok = True
for check in checks:
    if isinstance(check[0], bool):
        if check[0]:
            print(f"  ✓ {check[1]}")
        else:
            print(f"  ✗ {check[1]}")
            all_ok = False
    elif check[0] in content:
        print(f"  ✓ {check[1]}")
    else:
        print(f"  ✗ {check[1]}")
        all_ok = False

print("\n✓ All done!" if all_ok else "\n⚠ Some issues remain")
