from .services.vocabulary_service import VocabularyService

class VocabularyInterface:
    @staticmethod
    def get_set_detail(user_id, set_id):
        """
        Get details of a vocabulary set.
        Used by other modules to fetch set info without importing the service directly.
        """
        return VocabularyService.get_set_detail(user_id, set_id)

    @staticmethod
    def get_global_stats(user_id: int):
        """Get global statistics for vocabulary."""
        from .services.stats_container import VocabularyStatsService
        return VocabularyStatsService.get_global_stats(user_id)

    @staticmethod
    def get_full_stats(user_id: int, container_id: int):
        """Get full statistics for a vocabulary container."""
        from .services.stats_container import VocabularyStatsService
        return VocabularyStatsService.get_full_stats(user_id, container_id)

    @staticmethod
    def get_mode_counts(user_id: int, container_id: int):
        """Get mode counts for a vocabulary container."""
        from .services.stats_container import VocabularyStatsService
        return VocabularyStatsService.get_mode_counts(user_id, container_id)
