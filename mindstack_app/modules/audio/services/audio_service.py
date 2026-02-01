import os
import asyncio
from flask import current_app

from mindstack_app.models import AppSettings
from ..config import AudioModuleDefaultConfig
from ..engines.edge import EdgeEngine
from ..engines.gtts_engine import GTTSEngine
from ..logics.audio_logic import generate_hash_name, get_storage_path
from ..schemas import AudioRequestDTO

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
    async def get_audio(cls, request_dto: AudioRequestDTO) -> dict:
        """
        Get audio for the given text. Returns existing file or generates new one.
        """
        text = request_dto.text
        engine = request_dto.engine
        voice = request_dto.voice
        target_dir = request_dto.target_dir
        custom_filename = request_dto.custom_filename
        is_manual = request_dto.is_manual
        auto_voice_parsing = request_dto.auto_voice_parsing

        # --- Pre-processing: Voice Parsing and Config ---
        final_text = text
        is_concatenation_needed = False
        
        # 1. Determine Filename (Logic differs if hashing text vs custom)
        if custom_filename:
            filename = custom_filename
            if not filename.endswith('.mp3'):
                filename += '.mp3'
        else:
            # Apply Defaults
            if not engine:
                engine = AppSettings.get('AUDIO_DEFAULT_ENGINE', 
                                        current_app.config.get('AUDIO_DEFAULT_ENGINE', 
                                                              AudioModuleDefaultConfig.AUDIO_DEFAULT_ENGINE))
            
            if not voice and not auto_voice_parsing:
                if engine == 'edge':
                    voice = AppSettings.get('AUDIO_DEFAULT_VOICE_EDGE', 
                                           current_app.config.get('AUDIO_DEFAULT_VOICE_EDGE', 
                                                                 AudioModuleDefaultConfig.AUDIO_DEFAULT_VOICE_EDGE))
                elif engine == 'gtts':
                    voice = AppSettings.get('AUDIO_DEFAULT_VOICE_GTTS', 
                                           current_app.config.get('AUDIO_DEFAULT_VOICE_GTTS', 
                                                                 AudioModuleDefaultConfig.AUDIO_DEFAULT_VOICE_GTTS))
                else:
                    voice = 'default'

            # Hash generation
            # If auto-parsing, we hash the RAW text because the logic handles the same input consistently
            filename = generate_hash_name(text, engine, voice if voice else 'auto')
            
        # 2. Determine Target Directory
        if not target_dir:
            target_dir = 'uploads/audio/cache'
            
        # 3. Resolve Paths
        paths = get_storage_path(target_dir, filename)
        physical_path = paths['physical_path']
        url = paths['url']
        
        # 4. Check Existence (Cache Hit)
        if os.path.exists(physical_path) and not is_manual:
             return {'physical_path': physical_path, 'url': url, 'status': 'exists'}
            
        # 5. Generate Audio
        try:
            success = False
            
            if auto_voice_parsing and engine == 'edge':
                # --- Concatenation Strategy (User Requested) ---
                 success = await cls._generate_concatenated_audio(text, physical_path)
            else:
                # --- Standard Single Generation ---
                # Strip tags if not using concatenation but auto_voice_parsing was requested (e.g. gTTS)
                if auto_voice_parsing:
                     from ..logics.voice_parser import VoiceParser
                     final_text = VoiceParser.strip_prompts(text)

                engine_cls = cls._ENGINES.get(engine)
                if not engine_cls:
                    return {'error': f'Unknown engine: {engine}', 'status': 'error'}
                
                generator = engine_cls()
                success = await generator.generate(final_text, voice, physical_path)

            if success:
                return {'physical_path': physical_path, 'url': url, 'status': 'generated'}
            else:
                 return {'error': 'Generation failed', 'status': 'error'}
                 
        except Exception as e:
            current_app.logger.error(f"[AudioService] Exception: {e}")
            return {'error': str(e), 'status': 'error'}

    @classmethod
    async def _generate_concatenated_audio(cls, text: str, output_path: str) -> bool:
        """
        Parses text, generates segments using Edge TTS, and concatenates them.
        """
        import os
        import tempfile
        import asyncio
        from ..logics.voice_parser import VoiceParser
        from mindstack_app.modules.audio.logics.voice_engine import VoiceEngine # Reuse for pydub logic
        
        segments = VoiceParser.parse_segments(text)
        if not segments:
            return False
            
        temp_files = []
        mapping = AppSettings.get('AUDIO_VOICE_MAPPING_GLOBAL', 
                                  current_app.config.get('AUDIO_VOICE_MAPPING_GLOBAL', 
                                                        AudioModuleDefaultConfig.AUDIO_VOICE_MAPPING_GLOBAL))
        if isinstance(mapping, str):
            import json
            try:
                mapping = json.loads(mapping)
            except:
                mapping = {}
        
        default_voice_edge = AppSettings.get('AUDIO_DEFAULT_VOICE_EDGE', 
                                            current_app.config.get('AUDIO_DEFAULT_VOICE_EDGE', 
                                                                  AudioModuleDefaultConfig.AUDIO_DEFAULT_VOICE_EDGE))
        
        try:
            # 1. Generate Parts
            
            for i, seg in enumerate(segments):
                seg_text = seg['text']
                if not seg_text.strip():
                    continue
                    
                lang = seg['lang']
                gender = seg['gender']
                
                # Resolve Identity (Engine + Voice)
                # Default identity
                resolved_engine = 'edge'
                resolved_voice = default_voice_edge
                
                if lang:
                    key_gender = f"{lang}-{gender}" if gender else lang
                    key_generic = lang
                    
                    found_val = None
                    if key_gender in mapping:
                        found_val = mapping[key_gender]
                    elif key_generic in mapping:
                        found_val = mapping[key_generic]
                    
                    if found_val:
                        # Format is 'engine:voice' (e.g. 'edge:vi-VN-Na', 'gtts:vi')
                        if ':' in found_val:
                            resolved_engine, resolved_voice = found_val.split(':', 1)
                        else:
                            # Legacy or edge-only format
                            resolved_voice = found_val
                            
                current_app.logger.info(f"[AudioConcatenation] Segment '{seg_text[:10]}...': Key={lang}-{gender} -> {resolved_engine}:{resolved_voice}")

                # Instantiate Engine for this segment
                engine_cls = cls._ENGINES.get(resolved_engine)
                if not engine_cls:
                     # Fallback to Edge if unknown
                     engine_cls = cls._ENGINES['edge']
                
                gen_instance = engine_cls()
                
                # Create Temp File
                fd, temp_path = tempfile.mkstemp(suffix=f"_{i}.mp3")
                os.close(fd)
                
                # Generate Sync (Using the instance method, awaiting if it's async compatible wrapper, 
                # but our .generate is async def)
                success = await gen_instance.generate(seg_text, resolved_voice, temp_path)
                
                if success:
                    temp_files.append(temp_path)
                else:
                    raise Exception(f"Failed to generate segment: {seg_text} with {resolved_engine}")
            
            if not temp_files:
                return False
                
            # 2. Concatenate
            # Use VoiceEngine's logic which uses Pydub
            # It's synchronous, so run in executor to avoid blocking async loop
            loop = asyncio.get_running_loop()
            
            # VoiceEngine.concatenate_audio_files(file_paths, output_format, pause_ms)
            # We need to construct it or make the method static. It's an instance method currently.
            ve = VoiceEngine()
            
            # We only want to save to 'output_path', but 'concatenate_audio_files' generates its own temp path.
            # We can use it and then move/copy, or use pydub directly here. 
            # Reusing is cleaner code-wise but slightly inefficient (double write).
            # Let's use pydub directly here for full control over destination 'output_path'.
            
            def concat_task():
                from pydub import AudioSegment
                combined = AudioSegment.empty()
                pause = AudioSegment.silent(duration=300) # 300ms pause between segments
                
                first = True
                for tf in temp_files:
                    if not first:
                        combined += pause
                    combined += AudioSegment.from_file(tf)
                    first = False
                    
                combined.export(output_path, format="mp3")
                
            await loop.run_in_executor(None, concat_task)
            return True
            
        except Exception as e:
            current_app.logger.error(f"[ConcactGen] Error: {e}")
            return False
        finally:
            # Cleanup
            for tf in temp_files:
                if os.path.exists(tf):
                    try:
                        os.remove(tf)
                    except:
                        pass

    @classmethod
    def speech_to_text(cls, audio_source, lang: str = "vi-VN") -> str:
        """
        Transcribes speech to text.
        Delegate to VoiceEngine logic (which handles Google Speech Recognition).
        """
        from ..logics.voice_engine import VoiceEngine
        engine = VoiceEngine()
        return engine.speech_to_text(audio_source, lang)

