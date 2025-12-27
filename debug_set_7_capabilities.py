from mindstack_app import create_app, db
from mindstack_app.models import LearningContainer

app = create_app()

with app.app_context():
    container = LearningContainer.query.get(7)
    with open('debug_output.txt', 'w', encoding='utf-8') as f:
        if container:
            f.write(f"Set ID: {container.container_id}\n")
            f.write(f"Title: {container.title}\n")
            f.write(f"Type: {container.container_type}\n")
            f.write(f"AI Capabilities: {container.ai_capabilities}\n")
            f.write(f"Legacy Settings: {container.legacy_ai_settings}\n")
            f.write(f"Calculated Capability Flags: {container.capability_flags()}\n")
        else:
            f.write("Set 7 not found.\n")
