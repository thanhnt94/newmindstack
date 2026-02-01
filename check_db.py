from mindstack_app import create_app
from mindstack_app.models import ScoreLog
from datetime import datetime, timezone

app = create_app()
with app.app_context():
    print(f"Current UTC time: {datetime.now(timezone.utc)}")
    logs = ScoreLog.query.order_by(ScoreLog.timestamp.desc()).limit(10).all()
    print("--- Recent Score Logs ---")
    for log in logs:
        print(f"ID: {log.log_id}, User: {log.user_id}, Score: {log.score_change}, Time: {log.timestamp}")