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

            print(f"[EdgeEngine] Generating... Text Start: {text[:100]!r}")
            # Check for SSML
            if text.strip().startswith("<speak"):
                # Use communicate with SSML - edge_tts detects SSML if text starts with <speak>
                # But we still need to pass a voice, though SSML <voice> tags take precedence.
                # However, edge-tts might require a 'voice' argument even for SSML.
                # Usually, we just pass the text.
                communicate = edge_tts.Communicate(text, selected_voice) 
            else:
                communicate = edge_tts.Communicate(text, selected_voice)

            await communicate.save(full_path)
            
            return True
        except Exception as e:
            # In a real app, logging should be used here.
            # Assuming caller handles logging or catches exceptions.
            print(f"[EdgeEngine] Error generating audio: {e}")
            return False
