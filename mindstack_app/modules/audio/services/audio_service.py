import os
import asyncio
from flask import current_app

from ..engines.edge import EdgeEngine
from ..engines.gtts_engine import GTTSEngine
from ..logics.audio_logic import generate_hash_name, get_storage_path

class AudioService:
    """
    Centralized Audio Service for MindStack.
    Handles Text-to-Speech generation, caching, and storage management.
    """
    
    # Engine Registry
    _ENGINES = {
        'edge': EdgeEngine,
        'gtts': GTTSEngine
    }
    
    @classmethod
    async def get_audio(cls, text: str, engine: str = 'edge', voice: str = None, target_dir: str = None, custom_filename: str = None) -> dict:
        """
        Get audio for the given text. Returns existing file or generates new one.
        
        Args:
            text: Text to speak.
            engine: 'edge' or 'gtts'.
            voice: Specific voice ID.
            target_dir: Relative path to store audio (default: static/audio/cache).
            custom_filename: Specific filename (default: auto-hashed).
            
        Returns:
            dict: { 'physical_path': str, 'url': str, 'status': 'exists'|'generated'|'error' }
        """
        
        # 1. Determine Filename
        if custom_filename:
            filename = custom_filename
            # Ensure extension
            if not filename.endswith('.mp3'):
                filename += '.mp3'
        else:
            filename = generate_hash_name(text, engine, voice)
            
        # 2. Determine Target Directory
        if not target_dir:
            target_dir = 'uploads/audio/cache'
            
        # 3. Resolve Paths
        paths = get_storage_path(target_dir, filename)
        physical_path = paths['physical_path']
        url = paths['url']
        
        # 4. Check Existence (Cache Hit)
        if os.path.exists(physical_path):
            return {
                'physical_path': physical_path,
                'url': url,
                'status': 'exists'
            }
            
        # 5. Generate Audio (Cache Miss)
        # Instantiate Engine
        engine_cls = cls._ENGINES.get(engine)
        if not engine_cls:
            current_app.logger.error(f"[AudioService] Unknown engine: {engine}")
            return {'error': f'Unknown engine: {engine}', 'status': 'error'}
            
        generator = engine_cls()
        
        try:
            success = await generator.generate(text, voice, physical_path)
            if success:
                return {
                    'physical_path': physical_path,
                    'url': url,
                    'status': 'generated'
                }
            else:
                 return {'error': 'Generation failed', 'status': 'error'}
        except Exception as e:
            current_app.logger.error(f"[AudioService] Exception: {e}")
            return {'error': str(e), 'status': 'error'}

    @classmethod
    async def prepare_card_audio(cls, text: str, set_id: int, side: str = 'front', engine: str = 'edge', voice: str = None) -> dict:
        """
        Auto-organize audio for a specific flashcard set.
        Target: static/media/sets/{set_id}/audio/
        Filename: {side}_{hash}.mp3 (to allow duplicates of same word on different sides or generally unique)
        Actually, simpler to hash content. But user might want side prefix?
        Let's use just hash, but store in set folder.
        """
        target_dir = f"static/media/sets/{set_id}/audio"
        
        # Optional: Prefix filename with side for easier debugging?
        # But content-based hash is better for deduplication.
        # Let's Stick to standard hash but putting it in the set folder.
        
        # If user wants specific file naming convention?
        # User prompt: "prepare_card_audio(word, set_id, ...) để tự động định hướng lưu vào thư mục của bộ thẻ"
        
        return await cls.get_audio(
            text=text,
            engine=engine,
            voice=voice,
            target_dir=target_dir
        )
