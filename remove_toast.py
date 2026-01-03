
import os

file_path = r"c:\Code\MindStack\newmindstack\mindstack_app\templates\v3\pages\learning\vocabulary\flashcard\session\js\ui_manager.js"

with open(file_path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

new_lines = []
skip = False
found = False

for line in lines:
    if "function showScoreToast(scoreChange) {" in line:
        skip = True
        found = True
        continue
    
    if skip:
        if line.strip() == "}":
            skip = False
        continue
    
    new_lines.append(line)

if found:
    print("Found and removed showScoreToast.")
    with open(file_path, 'w', encoding='utf-8') as f:
        f.writelines(new_lines)
else:
    print("Function showScoreToast not found.")
