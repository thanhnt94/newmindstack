from abc import ABC, abstractmethod

class AudioEngine(ABC):
    """
    Abstract Base Class for Text-to-Speech engines.
    """
    
    @abstractmethod
    async def generate(self, text: str, voice: str, full_path: str) -> bool:
        """
        Generate audio file from text.
        
        Args:
            text: The text to convert to speech.
            voice: The voice identifier (engine specific).
            full_path: Absolute system path to save the file (including .mp3 extension).
            
        Returns:
            bool: True if generation was successful, False otherwise.
        """
        pass
