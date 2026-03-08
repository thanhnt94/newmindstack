import logging
from hanzipy.decomposer import HanziDecomposer
from typing import List, Dict

logger = logging.getLogger(__name__)

class DecompositionService:
    _decomposer = None

    @classmethod
    def _get_decomposer(cls):
        if cls._decomposer is None:
            try:
                cls._decomposer = HanziDecomposer()
            except Exception as e:
                logger.error(f"Failed to initialize HanziDecomposer: {e}", exc_info=True)
                cls._decomposer = None # Ensure it's reset if init fails
        return cls._decomposer

    @classmethod
    def decompose_kanji(cls, kanji: str, level: int = 2) -> Dict:
        """
        Decomposes a single Kanji character into its components using hanzipy.
        Level 1: Immediate decomposition
        Level 2: Radical decomposition
        Level 3: Graphical decomposition (lowest forms/strokes)
        """
        decomposer = cls._get_decomposer()
        if not decomposer:
            return {"character": kanji, "components": []}

        try:
            return decomposer.decompose(kanji, level)
        except Exception as e:
            logger.warning(f"Could not decompose kanji '{kanji}' at level {level}: {e}")
            return {"character": kanji, "components": []}

    @classmethod
    def get_all_decompositions(cls, kanji: str) -> Dict[str, Dict]:
        """
        Returns all levels of decomposition for a Kanji.
        """
        return {
            "level1_immediate": cls.decompose_kanji(kanji, 1),
            "level2_radicals": cls.decompose_kanji(kanji, 2),
            "level3_strokes": cls.decompose_kanji(kanji, 3)
        }
