from mindstack_app import create_app
app = create_app()
with app.app_context():
    print(f"{'Endpoint':<60} {'Methods':<20} {'URL'}")
    print("-" * 100)
    for rule in sorted(app.url_map.iter_rules(), key=lambda x: x.endpoint):
        methods = ', '.join(rule.methods)
        print(f"{rule.endpoint:<60} {methods:<20} {rule.rule}")
