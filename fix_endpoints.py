import os

path = r"c:\Code\MindStack\newmindstack\mindstack_app\themes\aura_mobile\templates\aura_mobile\modules\learning\vocab_matching\session\index.html"

# Read current content
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

# Fix the total line first (ensure it has the brace)
content = content.replace('var total = {{ game.total }', '        var total = {{ game.total }};')

# Fix endpoint names
content = content.replace('vocabulary.matching.end_session', 'vocab_matching.matching_end_session')
content = content.replace('vocabulary.matching.setup', 'vocabulary.modes_selection_page')

with open(path, 'w', encoding='utf-8') as f:
    f.write(content)

print(f"Successfully updated endpoints in {path}")
