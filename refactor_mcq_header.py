"""Refactor MCQ session.html to use shared header template"""

import re

path = r'c:\Code\MindStack\newmindstack\mindstack_app\modules\learning\vocabulary\mcq\templates\mcq\session.html'

with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Remove old MCQ header CSS (from "/* Header - Flashcard Style */" to before ".back-btn {")
css_pattern = r'/\* Header - Flashcard Style \*/.*?(?=/\* Main Content \*/|\.back-btn \{)'
content = re.sub(css_pattern, '', content, flags=re.DOTALL)

# Also remove old mcq-* CSS classes if still present
mcq_css_pattern = r'\s*/\* Context Bar \*/\s*\.mcq-context-bar.*?\.mcq-title-text \{[^}]+\}\s*'
content = re.sub(mcq_css_pattern, '\n', content, flags=re.DOTALL)

# 2. Replace old header HTML with shared template include
old_header = r'<header class="session-header">.*?</header>'
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
    {% include 'shared/includes/_session_header.html' %}'''

content = re.sub(old_header, new_header, content, flags=re.DOTALL)

with open(path, 'w', encoding='utf-8') as f:
    f.write(content)

# Verify
with open(path, 'r', encoding='utf-8') as f:
    new_content = f.read()
    if "_session_header.html" in new_content:
        print("✓ Shared header include added")
    else:
        print("✗ Include not found")
    
    if "mcq-context-bar" in new_content:
        print("✗ Old mcq CSS still present")
    else:
        print("✓ Old mcq CSS removed")

print("Done!")
