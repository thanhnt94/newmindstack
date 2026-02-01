# File: mindstack_app/modules/audio/interface.py
from typing import Optional
from .services.audio_service import AudioService
from .schemas import AudioRequestDTO, AudioResponseDTO

class AudioInterface:
    @staticmethod
    async def generate_audio(
        text: str,
        engine: str = 'edge',
        voice: Optional[str] = None,
        target_dir: Optional[str] = None,
        custom_filename: Optional[str] = None,
        is_manual: bool = False,
        auto_voice_parsing: bool = False
    ) -> AudioResponseDTO:
        """
        Generate audio from text using the centralized AudioService.
        """
        result = await AudioService.get_audio(AudioRequestDTO(
            text=text,
            engine=engine,
            voice=voice,
            target_dir=target_dir,
            custom_filename=custom_filename,
            is_manual=is_manual,
            auto_voice_parsing=auto_voice_parsing
        ))
        
        return AudioResponseDTO(
            status=result.get('status'),
            url=result.get('url'),
            physical_path=result.get('physical_path'),
            error=result.get('error')
        )

    @staticmethod
    def speech_to_text(audio_source, lang: str = "vi-VN") -> str:
        """
        Transcribe speech to text.
        """
        return AudioService.speech_to_text(audio_source, lang)
