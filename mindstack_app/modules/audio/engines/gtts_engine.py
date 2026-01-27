import asyncio
import os
from gtts import gTTS
from .base import AudioEngine

class GTTSEngine(AudioEngine):
    """
    Audio Engine using Google Text-to-Speech (gTTS library).
    Wraps blocking calls in threads.
    """

    async def generate(self, text: str, voice: str, full_path: str) -> bool:
        try:
            # Create directory if not exists
            directory = os.path.dirname(full_path)
            if not os.path.exists(directory):
                os.makedirs(directory, exist_ok=True)

            # Map 'voice' to gTTS 'lang' (simplified)
            # User might pass 'en-US' or just 'en'
            lang = 'en'
            if voice:
                # Simple heuristic: take first two chars if it looks like a locale
                # e.g. 'en-US' -> 'en', 'vi-VN' -> 'vi'
                parts = voice.split('-')
                if parts:
                    lang = parts[0]
            
            # gTTS save is blocking
            await asyncio.to_thread(self._save_gtts, text, lang, full_path)
            return True
        except Exception as e:
            print(f"[GTTSEngine] Error generating audio: {e}")
            return False

    def _save_gtts(self, text: str, lang: str, path: str):
        """Blocking helper method."""
        tts = gTTS(text=text, lang=lang)
        tts.save(path)
