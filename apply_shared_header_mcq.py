"""Apply shared header template to MCQ session.html safely"""

import re

path = r'c:\Code\MindStack\newmindstack\mindstack_app\modules\learning\vocabulary\mcq\templates\mcq\session.html'

with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

# Step 1: Find and replace the header HTML block
old_header_pattern = r'<header class="session-header">.*?</header>'
new_header = '''{% set session_config = {
        'type': 'mcq',
        'label': 'Trắc nghiệm',
        'icon': 'fas fa-list-check',
        'color': 'linear-gradient(135deg, #6366f1, #4f46e5)',
        'exit_url': url_for('learning.vocabulary.dashboard')
    } %}
    {% set session_stats = [
        {'label': 'Tiến độ', 'id': 'progress-display', 'value': '1/...', 'class': ''},
        {'label': 'Đúng', 'id': 'live-correct', 'value': '0', 'class': 'correct'},
        {'label': 'Sai', 'id': 'live-wrong', 'value': '0', 'class': 'wrong'}
    ] %}
    {% set container_title = container.title %}
    {% include 'includes/_session_header.html' %}'''

content = re.sub(old_header_pattern, new_header, content, flags=re.DOTALL)

# Step 2: Update JS to remove old element references and use new ones
# Remove old elements from els object
old_els = r'''const els = \{
        qNum: document\.getElementById\('current-q-num'\),
        tNum: document\.getElementById\('total-q-num'\),
        pBar: document\.getElementById\('progress-bar'\),
        pPer: document\.getElementById\('progress-percent'\),
        lCorrect: document\.getElementById\('live-correct'\),
        lWrong: document\.getElementById\('live-wrong'\),
        qText: document\.getElementById\('question-text'\),
        cGrid: document\.getElementById\('choices-grid'\),
        nextBtn: document\.getElementById\('next-btn'\),
        result: document\.getElementById\('result-overlay'\)
    \};'''

new_els = '''const els = {
        progressDisplay: document.getElementById('progress-display'),
        lCorrect: document.getElementById('live-correct'),
        lWrong: document.getElementById('live-wrong'),
        qText: document.getElementById('question-text'),
        cGrid: document.getElementById('choices-grid'),
        nextBtn: document.getElementById('next-btn'),
        result: document.getElementById('result-overlay')
    };'''

content = re.sub(old_els, new_els, content)

# Step 3: Update init() to not use tNum
old_init = r"els\.tNum\.textContent = questions\.length;"
new_init = "// Total question count is shown in progressDisplay as 1/N format"
content = re.sub(old_init, new_init, content)

# Step 4: Update renderQuestion to not use qNum, pBar, pPer
old_render = r'''// Update UI
        els\.qNum\.textContent = currentIndex \+ 1;
        const percent = Math\.round\(\(\(currentIndex\) / questions\.length\) \* 100\);
        els\.pBar\.style\.width = `\$\{percent\}%`;
        els\.pPer\.textContent = `\$\{percent\}%`;'''

new_render = '''// Update UI - progress display
        if (els.progressDisplay) {
            els.progressDisplay.textContent = `${currentIndex + 1}/${questions.length}`;
        }'''

content = re.sub(old_render, new_render, content)

# Step 5: Update showResult to not use pBar, pPer
old_show = r'''els\.pBar\.style\.width = '100%';
        els\.pPer\.textContent = '100%';'''

new_show = '''// Final progress display
        if (els.progressDisplay) {
            els.progressDisplay.textContent = `${questions.length}/${questions.length}`;
        }'''

content = re.sub(old_show, new_show, content)

with open(path, 'w', encoding='utf-8') as f:
    f.write(content)

# Verify
with open(path, 'r', encoding='utf-8') as f:
    new_content = f.read()

checks = [
    ("{% include 'includes/_session_header.html' %}", "shared header include"),
    ("progressDisplay: document.getElementById('progress-display')", "progressDisplay in els"),
    ("qNum:" not in new_content, "qNum removed"),
    ("pBar:" not in new_content, "pBar removed"),
    ("pPer:" not in new_content, "pPer removed"),
]

all_good = True
for check in checks:
    if isinstance(check[0], bool):
        if check[0]:
            print(f"✓ {check[1]}")
        else:
            print(f"✗ {check[1]}")
            all_good = False
    elif check[0] in new_content:
        print(f"✓ {check[1]}")
    else:
        print(f"✗ {check[1]}")
        all_good = False

print("\nDone!" if all_good else "\nSome issues remain")
