"""Fix MCQ session.html corrupted Jinja syntax"""

import re

path = r'c:\Code\MindStack\newmindstack\mindstack_app\modules\learning\vocabulary\mcq\templates\mcq\session.html'

with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

# Fix custom_pairs corrupted line - find the whole pattern and replace
# Pattern: {{ custom_pairs| tojson if custom_p <newlines/spaces> pairs else 'null' }}
pattern = r"\{\{\s*custom_pairs\|\s*tojson\s+if\s+custom_p.*?pairs\s+else\s*'null'\s*\}\}"
replacement = "{{ custom_pairs|tojson if custom_pairs else 'null' }}"
content = re.sub(pattern, replacement, content, flags=re.DOTALL)

with open(path, 'w', encoding='utf-8') as f:
    f.write(content)

# Verify
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()
    if "custom_pairs|tojson if custom_pairs else" in content:
        print("✓ custom_pairs fixed")
    else:
        print("✗ custom_pairs still broken")
    
    if "{{ container.container_id }};" in content:
        print("✓ container_id correct")
    else:
        print("✗ container_id broken")
