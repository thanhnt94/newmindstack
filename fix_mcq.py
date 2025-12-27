import re

filepath = r'c:\Code\MindStack\newmindstack\mindstack_app\modules\learning\vocabulary\mcq\templates\mcq\setup.html'

with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# Fix split container_id line
content = re.sub(r'\{\{\s*container\.container_id\s*\}\s*\n\s*\};', '{{ container.container_id }};', content)

# Fix split total_items line
content = re.sub(r'\{\{\s*total_items\s*\}\s*\n\s*\};', '{{ total_items }};', content)

# Also fix if total_items is at end (no semicolon after)
content = re.sub(r'\{\{\s*total_items\s*\}([^}])', r'{{ total_items }}\1', content)

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)

# Verify changes
with open(filepath, 'r', encoding='utf-8') as f:
    for i, line in enumerate(f, 1):
        if 'total_items' in line or 'container_id' in line:
            print(f"Line {i}: {line.strip()}")
