"""
Test script to verify stats blueprint registration
"""
import sys
sys.path.insert(0, 'c:/Code/MindStack/newmindstack')

from flask import Flask
from mindstack_app.modules.learning import learning_bp

app = Flask(__name__)
app.register_blueprint(learning_bp, url_prefix='/learning')

print("=" * 60)
print("STATS ROUTES VERIFICATION")
print("=" * 60)

# Filter stats-related routes
stats_routes = []
for rule in app.url_map.iter_rules():
    if 'stats' in rule.rule.lower() or 'stats' in rule.endpoint.lower():
        stats_routes.append((rule.rule, rule.endpoint, [m for m in rule.methods if m not in ['HEAD', 'OPTIONS']]))

# Sort and display
stats_routes.sort()
if stats_routes:
    print(f"\nFound {len(stats_routes)} stats-related routes:\n")
    for rule, endpoint, methods in stats_routes:
        methods_str = ', '.join(methods)
        print(f"  {rule:50} [{methods_str:10}] -> {endpoint}")
else:
    print("\n❌ NO STATS ROUTES FOUND!")
    print("\nAll registered routes:")
    for rule in app.url_map.iter_rules():
        print(f"  {rule.rule} -> {rule.endpoint}")

print("\n" + "=" * 60)
print("Blueprint inspection:")
print(f"  learning_bp blueprints: {list(learning_bp.blueprints.keys()) if hasattr(learning_bp, 'blueprints') else 'N/A'}")
print("=" * 60)
