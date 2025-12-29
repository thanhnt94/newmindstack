import sys

# Read and clean the file
with open(r'c:\Code\MindStack\newmindstack\mindstack_app\modules\learning\sub_modules\vocabulary\templates\vocabulary\dashboard\default\index.html', 'rb') as f:
    content = f.read()

# Remove null bytes
content = content.replace(b'\x00', b'')

# Convert to string
content_str = content.decode('utf-8')

# Check if already has includes
if '_container_stats_modal.html' in content_str:
    print("Stats components already included!")
    sys.exit(0)

# Find the last occurrence of </script> and {% endblock %}
script_end = content_str.rfind('</script>')
endblock = content_str.rfind('{% endblock %}')

if script_end > 0 and endblock > script_end:
    # Insert between </script> and {% endblock %}
    additions = "\n\n{# Include Stats Components #}\n"
    additions += "{% include 'vocabulary/dashboard/default/_container_stats_modal.html' %}\n"
    additions += "{% include 'vocabulary/dashboard/default/_item_stats_charts.html' %}\n"
    additions += "{% include 'vocabulary/dashboard/default/_stats_enhancement.html' %}\n\n"
    
    new_content = content_str[:endblock] + additions + content_str[endblock:]
    
    # Write back
    with open(r'c:\Code\MindStack\newmindstack\mindstack_app\modules\learning\sub_modules\vocabulary\templates\vocabulary\dashboard\default\index.html', 'w', encoding='utf-8') as f:
        f.write(new_content)
    
    print("Successfully added stats component includes!")
else:
    print(f"ERROR: Could not find proper locations. script_end={script_end}, endblock={endblock}")
    sys.exit(1)
