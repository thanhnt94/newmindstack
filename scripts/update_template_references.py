import os
import re

ROOT_DIR = os.path.join(os.getcwd(), 'mindstack_app')
# Patterns to look for in HTML
JINJA_PATTERN = re.compile(r'{%\s*(include|extends|from)\s+[\'"](.*?)[\'"]\s*.*?%}')
# Patterns to look for in Python
PYTHON_PATTERN = re.compile(r'render_template\s*\(\s*[\'"](.*?)[\'"]')

# Ordered replacements (Specific -> General)
REPLACEMENTS = [
    # --- Exact Component Maps (Must be first) ---
    ('dashboard/default/_desktop.html', 'components/dashboard/desktop_view.html'),
    ('dashboard/default/_mobile.html', 'components/dashboard/mobile_view.html'),
    ('dashboard/default/_base.html', 'components/dashboard/base.html'),
    ('flashcard/individual/individual/_sets_list.html', 'components/flashcard/sets_list.html'),
    ('flashcard/individual/individual/_sets_list_desktop.html', 'components/flashcard/sets_list_desktop.html'),
    ('flashcard/individual/individual/_sets_list_mobile.html', 'components/flashcard/sets_list_mobile.html'),
    ('flashcard/individual/individual/_modes_list.html', 'components/flashcard/modes_list.html'),
    ('flashcard/individual/individual/_modes_list_desktop.html', 'components/flashcard/modes_list_desktop.html'),
    ('flashcard/individual/individual/_modes_list_mobile.html', 'components/flashcard/modes_list_mobile.html'),
    ('content_management/_shared_styles.html', 'components/shared/styles.html'),

    # --- Base & Includes ---
    ('base.html', 'base/layout.html'),
    ('_base_desktop.html', 'base/layouts/desktop.html'),
    ('_base_mobile.html', 'base/layouts/mobile.html'),
    ('includes/', 'base/includes/'),

    # --- Pages (Modules) ---
    # Prefix mapping: 'admin/' -> 'pages/admin/'
    ('admin/', 'pages/admin/'),
    ('ai_services/', 'pages/ai_services/'),
    ('auth/', 'pages/auth/'),
    ('collab/', 'pages/collab/'),
    ('content_management/', 'pages/content_management/'),
    ('course/', 'pages/course/'),
    ('dashboard/default/', 'pages/dashboard/'), # Handle leftover
    ('feedback/', 'pages/feedback/'),
    ('flashcard/', 'pages/flashcard/'),
    ('gamification/', 'pages/gamification/'),
    ('goals/', 'pages/goals/'),
    ('landing/', 'pages/landing/'),
    ('learning/', 'pages/learning/'),
    ('notes/', 'pages/notes/'),
    ('notification/', 'pages/notification/'),
    ('practice/', 'pages/practice/'),
    ('quiz/', 'pages/quiz/'),
    ('stats/', 'pages/stats/'),
    ('user_profile/', 'pages/user_profile/'),
    ('vocabulary/', 'pages/vocabulary/'),
]

def update_file(filepath):
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception as e:
        print(f"Skipping binary/error {filepath}: {e}")
        return

    original_content = content
    
    # 1. Update Python render_template
    if filepath.endswith('.py'):
        def replace_py(match):
            path = match.group(1)
            new_path = apply_replacements(path)
            return match.group(0).replace(path, new_path)
        content = PYTHON_PATTERN.sub(replace_py, content)

    # 2. Update HTML Jinja tags
    if filepath.endswith('.html'):
        def replace_html(match):
            tag_type = match.group(1) # extends/include
            path = match.group(2)
            new_path = apply_replacements(path)
            # Reconstruct is hard because of other args, simple replace in string
            return match.group(0).replace(path, new_path)
        content = JINJA_PATTERN.sub(replace_html, content)

    if content != original_content:
        print(f"Updating {filepath}")
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)

def apply_replacements(path):
    # If already fixed (starts with pages/, base/, components/), ignore
    if path.startswith(('pages/', 'base/', 'components/')):
        return path
        
    for old, new in REPLACEMENTS:
        if old in path:
            return path.replace(old, new)
    return path

def main():
    print("Starting bulk update...")
    count = 0 
    for root, dirs, files in os.walk(ROOT_DIR):
        if 'static' in root: continue # Skip static assets
        for file in files:
            if file.endswith(('.py', '.html')):
                update_file(os.path.join(root, file))
                count += 1
    print(f"Scanned {count} files.")

if __name__ == "__main__":
    main()
