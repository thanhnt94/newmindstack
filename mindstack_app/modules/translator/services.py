import logging
from deep_translator import GoogleTranslator
from mindstack_app.core.extensions import db
from .models import TranslationHistory

logger = logging.getLogger(__name__)

class TranslatorService:
    @staticmethod
    def translate_text(text, source='auto', target='vi', user_id=None):
        """
        Translate text using Google Translate (free).
        If user_id is provided, save the result to TranslationHistory.
        """
        try:
            translator = GoogleTranslator(source=source, target=target)
            result = translator.translate(text)
            
            if result and user_id:
                try:
                    history = TranslationHistory(
                        user_id=user_id,
                        original_text=text,
                        translated_text=result,
                        source_lang=source,
                        target_lang=target
                    )
                    db.session.add(history)
                    db.session.commit()
                except Exception as e_db:
                    logger.error(f"Failed to save translation history: {e_db}")
                    db.session.rollback()
            
            return result
        except Exception as e:
            # Log error properly
            logger.error(f"Translation Error: {e}", exc_info=True)
            return None

    @staticmethod
    def get_user_history(user_id, limit=50):
        """Fetch translation history for a specific user."""
        return TranslationHistory.query.filter_by(user_id=user_id).order_by(TranslationHistory.created_at.desc()).limit(limit).all()
