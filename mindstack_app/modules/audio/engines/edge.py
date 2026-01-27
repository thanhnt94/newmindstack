import edge_tts
import os
from .base import AudioEngine

class EdgeEngine(AudioEngine):
    """
    Audio Engine using Microsoft Edge TTS (edge-tts library).
    """

    async def generate(self, text: str, voice: str, full_path: str) -> bool:
        """
        Generate audio using edge-tts.
        """
        try:
            # Create directory if not exists (security measure)
            directory = os.path.dirname(full_path)
            if not os.path.exists(directory):
                os.makedirs(directory, exist_ok=True)

            # Default voice if None
            selected_voice = voice if voice else "en-US-ChristopherNeural"

            communicate = edge_tts.Communicate(text, selected_voice)
            await communicate.save(full_path)
            
            return True
        except Exception as e:
            # In a real app, logging should be used here.
            # Assuming caller handles logging or catches exceptions.
            print(f"[EdgeEngine] Error generating audio: {e}")
            return False
