import re

path = r'c:\Code\MindStack\newmindstack\mindstack_app\modules\learning\vocabulary\mcq\templates\mcq\session.html'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

# Find and fix the broken Jinja pattern
# Look for {{ container.container_id } followed by anything other than }
pattern = r'\{\{\s*container\.container_id\s*\}'
replacement = '{{ container.container_id }}'

matches = list(re.finditer(pattern, content))
print(f"Found {len(matches)} matches for pattern")

if matches:
    content = re.sub(pattern, replacement, content)
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)
    print("Fixed!")
else:
    # Check what's around line 472
    lines = content.split('\n')
    if len(lines) >= 475:
        print("Lines 470-475:")
        for i in range(469, min(475, len(lines))):
            print(f"{i+1}: {lines[i]}")
