from deep_translator import GoogleTranslator

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
            # Log error but don't crash
            print(f"Translation Error: {e}")
            return None
