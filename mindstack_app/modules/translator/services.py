import logging
from deep_translator import GoogleTranslator

logger = logging.getLogger(__name__)

class TranslatorService:
    @staticmethod
    def translate_text(text, source='auto', target='vi'):
        """
        Translate text using Google Translate (free).
        Fallback to returning original text if failed.
        """
        try:
            translator = GoogleTranslator(source=source, target=target)
            return translator.translate(text)
        except Exception as e:
            # Log error properly
            logger.error(f"Translation Error: {e}", exc_info=True)
            return None
