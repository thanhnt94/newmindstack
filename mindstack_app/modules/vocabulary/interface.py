from .services.vocabulary_service import VocabularyService

class VocabularyInterface:
    @staticmethod
    def get_set_detail(user_id, set_id):
        """
        Get details of a vocabulary set.
        Used by other modules to fetch set info without importing the service directly.
        """
        return VocabularyService.get_set_detail(user_id, set_id)
