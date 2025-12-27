"""
Add skeleton loading to MCQ session
Replaces ugly "Đang tải..." with professional skeleton animation
"""

path = r'c:\Code\MindStack\newmindstack\mindstack_app\modules\learning\vocabulary\mcq\templates\mcq\session.html'

with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Add skeleton CSS before </style>
skeleton_css = '''
    /* ===== Skeleton Loading ===== */
    @keyframes shimmer {
        0% { background-position: -200% 0; }
        100% { background-position: 200% 0; }
    }

    .skeleton {
        background: linear-gradient(90deg, #f0f0f0 25%, #e0e0e0 50%, #f0f0f0 75%);
        background-size: 200% 100%;
        animation: shimmer 1.5s infinite;
        border-radius: 8px;
    }

    .skeleton-text {
        height: 2rem;
        width: 80%;
        margin: 0 auto;
    }

    .skeleton-choice {
        height: 60px;
        width: 100%;
        border-radius: 16px;
    }

    .loading-state .question-text {
        display: none;
    }

    .loading-state .skeleton-content {
        display: block;
    }

    .skeleton-content {
        display: none;
        width: 100%;
    }

    .loaded .skeleton-content {
        display: none !important;
    }

    .loaded .question-text {
        display: block !important;
    }
'''

# Insert before </style>
content = content.replace('</style>', skeleton_css + '\n</style>')

# 2. Update HTML to have skeleton instead of "Đang tải..."
old_question_card = '''<div class="question-card" id="question-card">
            <div class="question-text" id="question-text">Đang tải...</div>
        </div>

        <div class="choices-grid" id="choices-grid">
            <!-- Buttons injected by JS -->
        </div>'''

new_question_card = '''<div class="question-card loading-state" id="question-card">
            <div class="question-text" id="question-text"></div>
            <div class="skeleton-content">
                <div class="skeleton skeleton-text"></div>
            </div>
        </div>

        <div class="choices-grid loading-state" id="choices-grid">
            <div class="skeleton skeleton-choice"></div>
            <div class="skeleton skeleton-choice"></div>
            <div class="skeleton skeleton-choice"></div>
            <div class="skeleton skeleton-choice"></div>
        </div>'''

content = content.replace(old_question_card, new_question_card)

# 3. Update JS to remove loading state when data is loaded
# Find the renderQuestion function and add class removal
old_render = "els.qText.textContent = q.question;"
new_render = """// Remove loading state
        document.getElementById('question-card').classList.remove('loading-state');
        document.getElementById('question-card').classList.add('loaded');
        els.qText.textContent = q.question;"""

content = content.replace(old_render, new_render)

with open(path, 'w', encoding='utf-8') as f:
    f.write(content)

# Verify
with open(path, 'r', encoding='utf-8') as f:
    new_content = f.read()

checks = [
    ('skeleton-text', 'skeleton CSS added'),
    ('skeleton skeleton-choice', 'skeleton HTML added'),
    ('loading-state', 'loading state class'),
    ('classList.remove', 'JS removes loading state'),
]

print("Verification:")
for pattern, desc in checks:
    if pattern in new_content:
        print(f"  ✓ {desc}")
    else:
        print(f"  ✗ {desc}")

print("\nDone!")
