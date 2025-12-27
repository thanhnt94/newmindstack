"""Comprehensive fix for MCQ session.html Jinja syntax issues"""

path = r'c:\Code\MindStack\newmindstack\mindstack_app\modules\learning\vocabulary\mcq\templates\mcq\session.html'

with open(path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

fixed_lines = []
i = 0
while i < len(lines):
    line = lines[i]
    
    # Fix 1: container_id split across lines
    if '{{ container.container_id }' in line and '};' not in line:
        # Check if next line has the closing
        if i + 1 < len(lines) and '};' in lines[i + 1]:
            # Merge and fix
            fixed_line = line.rstrip() + '};\n'
            fixed_line = fixed_line.replace('{{ container.container_id }};', '{{ container.container_id }};')
            fixed_lines.append(fixed_line)
            i += 2  # Skip next line
            continue
    
    # Fix 2: count|default split with spaces
    if 'count|default' in line and '(' in line:
        line = line.replace('count|default (10)', 'count|default(10)')
        line = line.replace('count | default (10)', 'count|default(10)')
        line = line.replace('count | default(10)', 'count|default(10)')
    
    # Fix 3: choices|default split with spaces
    if 'choices|default' in line:
        line = line.replace('choices|default (4)', 'choices|default(4)')
        line = line.replace('choices | default (4)', 'choices|default(4)')
        line = line.replace('choices | default(4)', 'choices|default(4)')
    
    # Fix 4: custom_pairs split across multiple lines
    if 'custom_pairs|' in line and 'tojson' in line and 'custom_p' in line:
        # This line is corrupted, look ahead for the rest
        combined = line.rstrip()
        j = i + 1
        while j < len(lines) and "else 'null'" not in combined:
            combined += ' ' + lines[j].strip()
            j += 1
        # Now fix the combined line
        combined = '    const customPairs = {{ custom_pairs|tojson if custom_pairs else \'null\' }};\n'
        fixed_lines.append(combined)
        i = j
        continue
    
    fixed_lines.append(line)
    i += 1

# Write fixed content
with open(path, 'w', encoding='utf-8') as f:
    f.writelines(fixed_lines)

# Verify
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()
    
checks = [
    ('{{ container.container_id }};', 'container_id correct'),
    ('count|default(10)', 'count correct'),
    ('choices|default(4)', 'choices correct'),
    ("custom_pairs|tojson if custom_pairs else 'null'", 'custom_pairs correct')
]

all_passed = True
for pattern, desc in checks:
    if pattern in content:
        print(f"✓ {desc}")
    else:
        print(f"✗ {desc}")
        all_passed = False

print("\nDone!" if all_passed else "\nSome issues remain - check file manually")
