"""
Apply all MCQ setup changes via direct Python file manipulation.
This bypasses the multi_replace tool which was corrupting the file.
"""

filepath = r'c:\Code\MindStack\newmindstack\mindstack_app\modules\learning\vocabulary\mcq\templates\mcq\setup.html'

with open(filepath, 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Find and remove stats section (lines between <!-- Learning Statistics --> and <!-- Question-Answer Pairs Section -->)
new_lines = []
skip_mode = False
for i, line in enumerate(lines):
    if '<!-- Learning Statistics -->' in line:
        skip_mode = True
        continue
    if '<!-- Question-Answer Pairs Section -->' in line:
        skip_mode = False
        # Don't skip this line, add it
    if skip_mode:
        continue
    new_lines.append(line)

# Find pairs-container and replace its content with default pair
result_lines = []
for i, line in enumerate(new_lines):
    if '<div class="pairs-container" id="pairs-container">' in line:
        result_lines.append(line)
        # Skip old comment line
        next_line = new_lines[i + 1] if i + 1 < len(new_lines) else ""
        if '<!-- Pairs added by JS -->' in next_line:
            # Add default pair instead
            default_pair = '''                    <!-- Default pair: front -> back -->
                    <div class="pair-row" data-pair-index="0">
                        <div class="pair-col">
                            <div class="pair-col-label">Câu hỏi</div>
                            <select class="pair-q">
                                <option value="">-- Chọn cột --</option>
                                {% for key in available_keys %}
                                <option value="{{ key }}"{% if key == 'front' %} selected{% endif %}>{{ key }}</option>
                                {% endfor %}
                            </select>
                        </div>
                        <span class="pair-arrow"><i class="fas fa-arrow-right"></i></span>
                        <div class="pair-col">
                            <div class="pair-col-label">Đáp án</div>
                            <select class="pair-a">
                                <option value="">-- Chọn cột --</option>
                                {% for key in available_keys %}
                                <option value="{{ key }}"{% if key == 'back' %} selected{% endif %}>{{ key }}</option>
                                {% endfor %}
                            </select>
                        </div>
                        <button type="button" class="pair-delete"><i class="fas fa-times"></i></button>
                    </div>
'''
            result_lines.append(default_pair)
    elif '<!-- Pairs added by JS -->' in line:
        continue  # Skip this line
    else:
        result_lines.append(line)

# Write result
with open(filepath, 'w', encoding='utf-8') as f:
    f.writelines(result_lines)

# Verify Jinja syntax is preserved
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()
    if '{{ container.container_id }};' in content:
        print("✓ container.container_id syntax correct")
    else:
        print("✗ container.container_id may be corrupted")
    
    if '{{ total_items }};' in content:
        print("✓ total_items syntax correct")
    else:
        print("✗ total_items may be corrupted")
    
    if '<!-- Learning Statistics -->' not in content:
        print("✓ Stats section removed")
    else:
        print("✗ Stats section still present")
    
    if 'Default pair: front -> back' in content:
        print("✓ Default pair added")
    else:
        print("✗ Default pair not found")

print("\nDone!")
