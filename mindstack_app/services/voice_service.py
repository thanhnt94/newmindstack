
import os
import logging
import tempfile
import asyncio
from typing import List, Tuple, Optional
from gtts import gTTS
from pydub import AudioSegment
import speech_recognition as sr

logger = logging.getLogger(__name__)

class VoiceService:
    """
    Service handling Voice operations: Text-to-Speech (TTS) and Speech-to-Text (STT).
    """

    def __init__(self):
        pass

    def text_to_speech(self, text: str, lang: str = 'en') -> str:
        """
        Synchronous TTS generation for a single text segment.
        Returns the path to the temporary audio file.
        """
        if not text or not text.strip():
            raise ValueError("Text content is empty")

        try:
            # gTTS default is 'en', slow=False
            tts = gTTS(text=text, lang=lang, slow=False)
            with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmpfile:
                temp_path = tmpfile.name
            tts.save(temp_path)
            logger.debug(f"Generated TTS file: {temp_path} (lang={lang})")
            return temp_path
        except Exception as e:
            logger.error(f"Error in text_to_speech: {e}")
            if 'temp_path' in locals() and os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                except OSError:
                    pass
            raise

    def concatenate_audio_files(self, file_paths: List[str], output_format: str = "mp3", pause_ms: int = 400) -> str:
        """
        Concatenates multiple audio files into one.
        Returns the path to the combined temporary audio file.
        """
        if not file_paths:
            raise ValueError("No file paths provided for concatenation")
        
        if len(file_paths) == 1:
            # Just copy the single file to a new temp location to be consistent, or return it?
            # Returning it is fine but caller expects a new file potentially? 
            # Let's just process it to ensure format/bitrate consistency if needed, 
            # but for optimization, just returning it is okay if format matches.
            # However, pydub export ensures format.
            pass

        try:
            combined = AudioSegment.from_file(file_paths[0])
            silence = AudioSegment.silent(duration=pause_ms) if pause_ms > 0 else None
            
            for fpath in file_paths[1:]:
                if silence:
                    combined += silence
                combined += AudioSegment.from_file(fpath)
            
            with tempfile.NamedTemporaryFile(suffix=f".{output_format}", delete=False) as tmp:
                output_path = tmp.name
            
            combined.export(output_path, format=output_format)
            logger.debug(f"Concatenated audio saved to: {output_path}")
            return output_path
        except Exception as e:
            logger.error(f"Error in concatenate_audio_files: {e}")
            if 'output_path' in locals() and os.path.exists(output_path):
                try:
                    os.remove(output_path)
                except OSError:
                    pass
            raise

    async def generate_dialogue_audio(self, segments: List[Tuple[str, str]], pause_ms: int = 400) -> str:
        """
        Orchestrates the generation of a dialogue (list of lang, text tuples).
        Handles parallel generation of TTS parts and sequential concatenation.
        Returns path to final audio file.
        """
        loop = asyncio.get_running_loop()
        temp_files = []
        
        try:
            # 1. Generate all parts in parallel
            tasks = []
            for lang, text in segments:
                # Add random jitter to sleep if needed to avoid rate limits? 
                # The original code had random sleep.
                # We will just schedule them. Caller can handle rate limit logic if needed, 
                # but to replicate original behavior we might want to be careful.
                # Original code: await asyncio.sleep(random.uniform(0.5, 2.0))
                # We'll execute them.
                tasks.append(loop.run_in_executor(None, self.text_to_speech, text, lang))
            
            # Wait for all
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Check for errors
            for res in results:
                if isinstance(res, Exception):
                    raise res
                temp_files.append(res)
            
            # 2. Concatenate
            if not temp_files:
                raise ValueError("No audio generated")
                
            final_path = await loop.run_in_executor(None, self.concatenate_audio_files, temp_files, "mp3", pause_ms)
            return final_path

        except Exception as e:
            logger.error(f"Error in generate_dialogue_audio: {e}")
            raise
        finally:
            # Cleanup temp fragments
            for f in temp_files:
                if f and os.path.exists(f):
                    try:
                        os.remove(f)
                    except OSError:
                        pass

    def speech_to_text(self, audio_source, lang: str = "vi-VN") -> str:
        """
        Transcribes speech to text using Google Speech Recognition (Free API).
        
        Args:
            audio_source: Path to audio file.
            lang: Language code (default 'vi-VN').
            
        Returns:
            Transcribed text.
        """
        recognizer = sr.Recognizer()
        
        # Check if file exists
        if not os.path.exists(audio_source):
             raise FileNotFoundError(f"Audio file not found: {audio_source}")

        # Pre-process audio if not wav (SpeechRecognition works best/natively with WAV)
        # We allow pydub to handle conversion
        temp_wav_path = None
        try:
            # Detect format and convert to wav if necessary
            if not audio_source.lower().endswith('.wav'):
                logger.debug(f"Converting {audio_source} to WAV for STT processing...")
                audio = AudioSegment.from_file(audio_source)
                with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
                    temp_wav_path = tmp.name
                audio.export(temp_wav_path, format="wav")
                source_path = temp_wav_path
            else:
                source_path = audio_source

            with sr.AudioFile(source_path) as source:
                # record the audio data from the file
                audio_data = recognizer.record(source)
                
                logger.info(f"Sending audio data to Google Speech Recognition (lang={lang})...")
                text = recognizer.recognize_google(audio_data, language=lang)
                logger.info(f"STT Result: {text}")
                return text

        except sr.UnknownValueError:
            logger.warning("Google Speech Recognition could not understand audio")
            return "" # Return empty string or raise custom exception
        except sr.RequestError as e:
            logger.error(f"Could not request results from Google Speech Recognition service; {e}")
            raise RuntimeError(f"STT Service Error: {e}")
        except Exception as e:
             logger.error(f"Error in speech_to_text: {e}")
             raise
        finally:
            if temp_wav_path and os.path.exists(temp_wav_path):
                try:
                    os.remove(temp_wav_path)
                except OSError:
                    pass
