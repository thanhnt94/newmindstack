from mindstack_app import create_app
app = create_app()
with app.app_context():
    routes = []
    for rule in app.url_map.iter_rules():
        if 'mcq' in rule.rule:
            routes.append(f"{rule.endpoint}: {rule.rule}")
    print("\n".join(sorted(routes)))
