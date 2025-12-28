from mindstack_app import create_app, db
from mindstack_app.models.user import ReviewLog

app = create_app()

with app.app_context():
    print("Checking latest ReviewLogs...")
    logs = ReviewLog.query.order_by(ReviewLog.timestamp.desc()).limit(10).all()
    
    if not logs:
        print("No logs found.")
    else:
        print(f"{'ID':<5} | {'Mode':<15} | {'Duration (ms)':<15} | {'User Answer':<20} | {'Timestamp'}")
        print("-" * 80)
        for log in logs:
            answer = log.user_answer if log.user_answer else "(None)"
            if len(str(answer)) > 20:
                answer = str(answer)[:17] + "..."
            print(f"{log.log_id:<5} | {log.review_type:<15} | {log.duration_ms:<15} | {answer:<20} | {log.timestamp}")
