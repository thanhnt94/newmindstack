from start_mindstack_app import app
from mindstack_app.models import db, AiContent

with app.app_context():
    try:
        num = AiContent.query.delete()
        db.session.commit()
        print(f"Successfully deleted {num} records from ai_contents.")
    except Exception as e:
        db.session.rollback()
        print(f"Error: {e}")
