from mindstack_app import create_app
from mindstack_app.models import LearningItem

app = create_app()
with app.app_context():
    count = LearningItem.query.filter_by(container_id=4).filter(
        LearningItem.item_type.in_(['FLASHCARD', 'VOCABULARY'])
    ).count()
    print(f"Items in set 4: {count}")
