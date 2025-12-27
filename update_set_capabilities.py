from mindstack_app import create_app, db
from mindstack_app.models import LearningContainer

app = create_app()

FULL_CAPABILITIES = [
    'supports_flashcard',
    'supports_quiz',
    'supports_listening',
    'supports_writing',
    'supports_matching',
    'supports_speed',
    'supports_srs'
]

with app.app_context():
    # Update Set 7 specifically
    container = LearningContainer.query.get(7)
    if container:
        print(f"Updating Set {container.container_id} ({container.title})...")
        print(f"Old Capabilities: {container.ai_capabilities}")
        
        container.ai_capabilities = FULL_CAPABILITIES
        db.session.commit()
        
        print(f"New Capabilities: {container.ai_capabilities}")
        print("Update successful!")
    else:
        print("Set 7 not found.")
