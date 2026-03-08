from typing import List, Dict
from .services.kanji_service import KanjiService

class KanjiInterface:
    """
    Public API for the Kanji module.
    """
    
    @staticmethod
    def get_components(kanji: str) -> List[str]:
        """
        Decomposes a single Kanji character into its atomic components.
        """
        return KanjiService.get_components(kanji)

    @staticmethod
    def get_similar_kanji(kanji: str, limit: int = 5) -> List[Dict]:
        """
        Finds visually similar Kanji characters.
        Returns a list of dicts with 'kanji' and 'score'.
        """
        return KanjiService.get_similar_kanji(kanji, limit)

    @staticmethod
    def is_supported(kanji: str) -> bool:
        """
        Checks if we have data for this Kanji.
        """
        return KanjiService.is_supported(kanji)

    @staticmethod
    def get_details(kanji: str) -> Dict:
        """
        Returns full details of a Kanji (meanings, readings, hanviet, etc.)
        """
        return KanjiService.get_details(kanji)
