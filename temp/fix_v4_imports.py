"""Batch replace v3 references to v4 in all V4 templates."""
import os
import re

V4_PAGES = r"c:\Code\MindStack\newmindstack\mindstack_app\templates\v4\pages"

REPLACEMENTS = [
    ('v3/base.html', 'v4/base.html'),
    ('v3/includes/', 'v4/includes/'),
    ("v3/pages/dashboard/", "v4/pages/dashboard/"),
    ("v3/pages/user_profile/", "v4/pages/user_profile/"),
    ("v3/pages/stats/", "v4/pages/stats/"),
    ("v3/pages/learning/vocabulary/stats/", "v4/pages/learning/vocabulary/stats/"),
    ("v3/pages/learning/vocabulary/dashboard/", "v4/pages/learning/vocabulary/dashboard/"),
]

def replace_in_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    original = content
    for old, new in REPLACEMENTS:
        content = content.replace(old, new)
    
    if content != original:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        return True
    return False

def main():
    count = 0
    for root, dirs, files in os.walk(V4_PAGES):
        # Skip learning_v3_partials folder (it's an archive)
        if 'learning_v3_partials' in root:
            continue
        for fname in files:
            if fname.endswith('.html'):
                fpath = os.path.join(root, fname)
                if replace_in_file(fpath):
                    count += 1
                    print(f"Updated: {fpath}")
    print(f"\nTotal files updated: {count}")

if __name__ == "__main__":
    main()
