import os
import sys
from datetime import datetime, timedelta, timezone, date

# Add project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from mindstack_app import create_app
from mindstack_app.models import db, ScoreLog, User
from mindstack_app.modules.fsrs.models import ItemMemoryState
from mindstack_app.modules.learning.services.learning_metrics_service import LearningMetricsService

def diagnostic():
    app = create_app()
    with app.app_context():
        user = User.query.first()
        if not user:
            print("No user found.")
            return
            
        user_id = user.user_id
        with open('diag_results.txt', 'w', encoding='utf-8') as f:
            f.write(f"Analyzing stats for User: {user.username} (ID: {user_id})\n")
            
            # Get extended stats
            stats = LearningMetricsService.get_extended_dashboard_stats(user_id)
            
            labels = stats['charts']['labels']
            reviews = stats['charts']['datasets']['reviews']
            new_items = stats['charts']['datasets']['new_items']
            
            f.write("\nDate\t\tReviews (Corr)\tNew Items\tTotal (interactions)\n")
            f.write("-" * 70 + "\n")
            
            for i in range(len(labels)):
                if reviews[i] > 0 or new_items[i] > 0:
                    f.write(f"{labels[i]}\t\t{reviews[i]}\t\t{new_items[i]}\t\t{reviews[i] + new_items[i]}\n")
            
            f.write("\nObservation:\n")
            f.write("Reviews should now be (Total - New).\n")

if __name__ == '__main__':
    diagnostic()
