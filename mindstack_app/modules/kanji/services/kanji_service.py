from typing import List, Dict
from ..engine.core import KanjiEngine
from ..logics.kanji_data import get_all_supported_kanji
from .decomposition_service import DecompositionService # New import

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

    @staticmethod
    def get_decompositions(kanji: str) -> Dict:
        """
        Returns all levels of decomposition for a Kanji using DecompositionService.
        """
        return DecompositionService.get_all_decompositions(kanji)

    @staticmethod
    def update_decomposition_data() -> str:
        """
        Triggers the update of kanji_db.json with hanzipy decomposition data.
        """
        import os
        import importlib.util

        current_dir = os.path.dirname(__file__)
        kanji_data_dir = os.path.join(current_dir, '..', 'logics')
        kanji_db_file = os.path.join(kanji_data_dir, 'kanji_db.json')

        # Dynamically load the script since 'newmindstack' is not an installed package
        script_path = os.path.abspath(os.path.join(current_dir, '..', '..', '..', '..', 'scripts', 'update_kanji_decomposition.py'))
        
        spec = importlib.util.spec_from_file_location("update_kanji", script_path)
        update_kanji_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(update_kanji_module)

        # Run the update script. Set overwrite_components=False as requested by user.
        update_kanji_module.update_kanji_db_with_hanzipy(kanji_db_file, overwrite_components=False)
        return "Kanji decomposition data update initiated."
