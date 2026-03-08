from typing import List, Dict
from ..engine.core import KanjiEngine
from ..logics.kanji_data import get_all_supported_kanji

class KanjiService:
    """
    Service layer for coordinating Kanji processing.
    """
    
    @staticmethod
    def get_components(kanji: str) -> List[str]:
        return KanjiEngine.decompose(kanji)

    @staticmethod
    def get_similar_kanji(kanji: str, limit: int = 5) -> List[Dict]:
        return KanjiEngine.find_similar(kanji, limit)

    @staticmethod
    def is_supported(kanji: str) -> bool:
        if not kanji or len(kanji) != 1:
            return False
        return kanji in get_all_supported_kanji()

    @staticmethod
    def get_details(kanji: str) -> Dict:
        from ..logics.kanji_data import get_kanji_details
        return get_kanji_details(kanji)
