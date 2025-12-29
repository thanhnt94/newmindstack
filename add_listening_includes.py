import re

file_path = r'c:\Code\MindStack\newmindstack\mindstack_app\modules\learning\sub_modules\vocabulary\listening\templates\listening\session\default\index.html'

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Find {% endblock %} at end
pattern = r'{%\s*endblock\s*%}\s*$'
replacement = '''{# Include Stats Components from stats module #}
{% include "stats/components/_chart_lib.html" %}
{% include "stats/components/_item_charts.html" %}

{% endblock %}'''

content = re.sub(pattern, replacement, content)

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)

print("Added stats component includes!")
