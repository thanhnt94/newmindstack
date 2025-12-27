import re

filepath = r'c:\Code\MindStack\newmindstack\mindstack_app\modules\learning\vocabulary\mcq\templates\mcq\setup.html'

with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# Fix the split total_items line
content = re.sub(
    r'\{\{ total_items \}\s*\n\s*\}; // Use all items',
    '{{ total_items }}; // Use all items',
    content
)

# Fix corrupted choices line
content = re.sub(
    r"document\.getElementById\('choices-select'\)\s*\n+\s*\)\.value;",
    "document.getElementById('choices-select').value;",
    content
)

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)

print('Fixed')
