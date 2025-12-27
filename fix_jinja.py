import re

filepath = r'c:\Code\MindStack\newmindstack\mindstack_app\modules\learning\vocabulary\mcq\templates\mcq\setup.html'

with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# Fix the split container_id line - match across newlines
pattern = r'\{\{\s*container\.container_id\s*\}\s*\n\s*\};'
replacement = '{{ container.container_id }};'
content = re.sub(pattern, replacement, content)

# Also fix any split total_items line
pattern2 = r'\{\{\s*total_items\s*\}\s*\n\s*\};'
replacement2 = '{{ total_items }};'
content = re.sub(pattern2, replacement2, content)

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)

# Verify
with open(filepath, 'r', encoding='utf-8') as f:
    for i, line in enumerate(f, 1):
        if 'container_id' in line:
            print(f"Line {i}: {line.strip()}")
