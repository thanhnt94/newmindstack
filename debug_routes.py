import sys
import os

# Add project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from mindstack_app import create_app

app = create_app()

with open('routes_list.txt', 'w') as f:
    for rule in app.url_map.iter_rules():
        if "vocabulary" in str(rule) or "flashcard" in str(rule) or "7" in str(rule):
            f.write(f"{rule} -> {rule.endpoint}\n")
print("Routes written to routes_list.txt")
