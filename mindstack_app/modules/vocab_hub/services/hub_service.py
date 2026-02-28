# mindstack_app/modules/vocab_hub/services/hub_service.py
from mindstack_app.modules.vocabulary.interface import VocabularyInterface
from mindstack_app.modules.stats.interface import StatsInterface
from mindstack_app.modules.fsrs.interface import FSRSInterface

class HubService:
    """Service to aggregate data for the Vocab Hub."""
    
    @staticmethod
    def get_global_hub_data(user_id):
        """Aggregate high-level vocabulary stats for the Global Hub."""
        # 1. Get global retention and progress from Stats module
        global_stats = VocabularyInterface.get_global_stats(user_id)
        
        # 2. Get top difficult items to focus on
        # We can ask StatsInterface for this
        difficult_items = StatsInterface.get_difficult_items_overview(user_id, limit=10)
        
        # 3. Get recent activity heatmap data
        activity = StatsInterface.get_user_activity_heatmap(user_id)
        
        # 4. Get Mastery Distribution (anonymized counts for New, Learning, Review, Mastered)
        mastery_dist = StatsInterface.get_mastery_distribution(user_id)
        
        # 5. Get 7-day Retention Trend
        retention_trend = StatsInterface.get_retention_trend(user_id, days=7)
        
        return {
            'overview': global_stats,
            'difficult_items': difficult_items,
            'activity': activity,
            'mastery_distribution': mastery_dist,
            'retention_trend': retention_trend
        }
    
    @staticmethod
    def get_item_insight(user_id, item_id):
        """Aggregate data for a specific vocabulary item."""
        return StatsInterface.get_vocab_item_stats(user_id, item_id)
