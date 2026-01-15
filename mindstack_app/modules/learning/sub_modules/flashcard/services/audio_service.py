# File: newmindstack/mindstack_app/modules/learning/flashcard_learning/audio_service.py
# Phiên bản: 1.1
# Mục đích: Cung cấp dịch vụ tạo và cache file âm thanh từ văn bản (Text-to-Speech)
#           cho các thẻ ghi nhớ (flashcards).
# ĐÃ SỬA: Cập nhật hàm generate_cache_for_all_cards để phản ánh trạng thái tác vụ nền
#         và xử lý yêu cầu dừng từ admin.

import os
import logging
import tempfile
import hashlib
import shutil
import asyncio
import random
import time
from flask import current_app

from mindstack_app.logics.voice_engine import VoiceEngine

from mindstack_app.db_instance import db
from mindstack_app.models import LearningContainer, LearningItem, User, BackgroundTask
from mindstack_app.config import Config
logger = logging.getLogger(__name__)

class AudioService:
    def __init__(self):
        """
        Mô tả: Khởi tạo dịch vụ AudioService.
        """
        self.voice_service = VoiceEngine()

    def _get_cache_dir(self) -> str:
        from mindstack_app.services.config_service import get_runtime_config
        return get_runtime_config('FLASHCARD_AUDIO_CACHE_DIR', Config.FLASHCARD_AUDIO_CACHE_DIR)

    def _ensure_cache_dir(self) -> str:
        cache_dir = self._get_cache_dir()
        os.makedirs(cache_dir, exist_ok=True)
        return cache_dir

    def _generate_tts_sync(self, text, lang='en'):
        """
        Mô tả: Tạo file audio Text-to-Speech (TTS) sử dụng VoiceEngine.
        """
        log_prefix = "[GENERATE_TTS_SYNC]"
        try:
            temp_path = self.voice_service.text_to_speech(text, lang)
            return temp_path, True, "Tạo TTS thành công."
        except Exception as e:
            logger.error(f"{log_prefix} Lỗi tạo TTS: {e}")
            return None, False, str(e)

    async def _generate_concatenated_audio(self, audio_content_string, output_format="mp3", pause_ms=400):
        """
        Mô tả: Ghép nhiều đoạn audio TTS thành một file duy nhất.
               Hỗ trợ định dạng 'lang: text' cho từng dòng hoặc inline.
        Args:
            audio_content_string (str): Chuỗi chứa nội dung audio.
            output_format (str): Định dạng đầu ra của file audio (mặc định là 'mp3').
            pause_ms (int): Thời gian tạm dừng giữa các đoạn audio khi ghép (miligiây).
        Returns:
            tuple: (đường dẫn file tạm thời cuối cùng, thành công (bool), thông báo lỗi/thành công).
                   Trả về (None, False, message) nếu có lỗi.
        """
        log_prefix = "[GEN_CONCAT_AUDIO]"
        if not audio_content_string or not audio_content_string.strip():
            logger.warning(f"{log_prefix} Chuỗi nội dung audio rỗng. Không cần ghép.")
            return None, True, "Nội dung audio rỗng, không cần ghép."

        import re
        
        # [FIX] Normalize content: replace full-width colon, remove BOM, and normalize newlines
        normalized_content = audio_content_string.replace('\ufeff', '').replace('：', ':').strip()
        normalized_content = normalized_content.replace('\r\n', '\n').replace('\r', '\n')
        
        # [NEW] Language code normalization map
        lang_map = {
            'vn': 'vi',
            'jp': 'ja',
            'kr': 'ko',
            'cn': 'zh-cn',
            'tw': 'zh-tw'
        }

        segments = []

        # --- PHASE 1: BRACKET FORMAT [lang:text] ---
        # Matches patterns like [ja: content] [vi: content]
        # We handle optional spaces around colon and ignore nested brackets
        bracket_pattern = re.compile(r'\[([a-z]{2,3}(?:-[a-z]{2,4})?)\s*:\s*([^\]]+)\]', re.IGNORECASE)
        bracket_matches = list(bracket_pattern.finditer(normalized_content))
        
        if bracket_matches:
            logger.debug(f"{log_prefix} Found {len(bracket_matches)} bracketed segments. Using Priority Parsing.")
            for m in bracket_matches:
                raw_lang = m.group(1).lower()
                lang_code = lang_map.get(raw_lang, raw_lang)
                text = m.group(2).strip()
                if text:
                    segments.append((lang_code, text))
        else:
            # --- PHASE 2: FALLBACK TO MARKER FORMAT lang: text ---
            # [FIX] Robust regex to find language markers. 
            # Using negative lookbehind to ensure we don't match markers inside another ASCII word/id.
            lang_pattern = re.compile(r'(?<![a-z0-9])([a-z]{2,3}(?:-[a-z]{2,4})?)\s*:', re.IGNORECASE)
            
            # Find all language markers
            matches = list(lang_pattern.finditer(normalized_content))
            
            logger.debug(f"{log_prefix} No brackets found. Fallback to MARKER logic (Found {len(matches)}).")

            if not matches:
                # Case: No language markers found at all. Treat whole text as default 'en'
                segments.append(('en', normalized_content))
            else:
                # Check if there is text BEFORE the first marker
                if matches[0].start() > 0:
                    pre_text = normalized_content[0:matches[0].start()].strip()
                    # If there's a delimiter at the start, remove it
                    pre_text = re.sub(r'^[|\s]+', '', pre_text).strip()
                    if pre_text:
                        segments.append(('en', pre_text)) 

                for i, match in enumerate(matches):
                    raw_lang = match.group(1).lower()
                    # Normalize language code
                    lang_code = lang_map.get(raw_lang, raw_lang)
                    
                    start_text_pos = match.end()
                    
                    # End of this segment is start of next match or end of string
                    end_text_pos = matches[i+1].start() if (i + 1 < len(matches)) else len(normalized_content)
                    
                    text_content = normalized_content[start_text_pos:end_text_pos].strip()
                    
                    # [FIX] Aggressive cleanup to remove leaked markers:
                    # 1. Remove trailing delimiters
                    text_content = re.sub(r'[|\s]+$', '', text_content).strip()
                    
                    # 2. [FIX] Remove any 2-3 letter combo that looks like a marker at the end
                    # but ONLY if it follows a non-ASCII character or a boundary.
                    text_content = re.sub(r'(?<![a-z])[a-z]{2,3}\s*:?$', '', text_content, flags=re.IGNORECASE).strip()

                    if text_content:
                        segments.append((lang_code, text_content))
                        logger.debug(f"{log_prefix} Segment {i+1}: [{lang_code}] (was {raw_lang}) -> '{text_content}'")
        
        if not segments:
            logger.warning(f"{log_prefix} Không tìm thấy segments hợp lệ nào sau khi parse.")
            return None, True, "Không có nội dung hợp lệ để tạo TTS."

        temp_files = []
        final_temp_path = None
        loop = asyncio.get_running_loop()
        overall_success = True
        overall_message = "Ghép audio thành công."

        try:
            tasks = []
            for lang_code, text_to_read in segments:
                try:
                    # Sanity check on lang_code if needed, but gTTS handles validation
                    # Add random jitter to emulate human-like request spacing?
                    delay = random.uniform(0.1, 0.5) 
                    tasks.append(loop.run_in_executor(None, self._generate_tts_sync, text_to_read, lang_code))
                except Exception as e_prep:
                    logger.error(f"{log_prefix} Lỗi chuẩn bị TTS cho segment '{text_to_read[:20]}...': {e_prep}", exc_info=True)
                    overall_success = False
                    overall_message = f"Lỗi chuẩn bị audio cho một phần: {e_prep}"

            if not tasks:
                return None, False, "Không có tác vụ TTS nào được tạo."

            logger.info(f"{log_prefix} Đang đợi {len(tasks)} tác vụ TTS.")
            # Execute sequentially or parallel? Parallel is faster but might hit rate limits faster.
            # VoiceEngine uses gTTS which calls Google API. 
            # We should probably run them.
            generated_files_results = await asyncio.gather(*tasks)
            
            for path, success, msg in generated_files_results:
                if not success:
                    overall_success = False
                    overall_message = msg
                if path:
                    temp_files.append(path)

            if not overall_success:
                logger.error(f"{log_prefix} {overall_message}")
                return None, False, overall_message
            
            if len(temp_files) == 0:
                 return None, False, "Không có file audio nào được tạo."
            elif len(temp_files) == 1:
                final_temp_path = temp_files[0]
                return final_temp_path, True, "Tạo audio thành công."
            
            def concatenate_sync_internal():
                try:
                    return self.voice_service.concatenate_audio_files(temp_files, output_format, pause_ms), True, "Ghép audio thành công."
                except Exception as e_concat:
                    logger.error(f"{log_prefix} Lỗi khi ghép đồng bộ: {e_concat}", exc_info=True)
                    return None, False, f"Lỗi khi ghép các đoạn audio: {e_concat}"

            final_temp_path, success, msg = await loop.run_in_executor(None, concatenate_sync_internal)
            return final_temp_path, success, msg
        except Exception as e:
            logger.critical(f"{log_prefix} Lỗi nghiêm trọng: {e}", exc_info=True)
            return None, False, f"Lỗi nghiêm trọng: {e}"
        finally:
            if temp_files:
                logger.debug(f"{log_prefix} Dọn dẹp {len(temp_files)} file TTS tạm...")
                for f in temp_files:
                    if f and os.path.exists(f) and f != final_temp_path:
                        try:
                            os.remove(f)
                        except Exception as e_remove:
                            logger.error(f"{log_prefix} Lỗi xóa file tạm {f}: {e_remove}")

    async def get_cached_or_generate_audio(self, audio_content_string, output_format="mp3", force_refresh=False):
        """
        Mô tả: Lấy đường dẫn đến file audio đã cache hoặc tạo mới nếu chưa có.
        Args:
            audio_content_string (str): Nội dung cần tạo audio.
            output_format (str): Định dạng file.
            force_refresh (bool): Nếu True, bỏ qua cache và tạo mới, đồng thời ghi đè cache cũ.
        """
        log_prefix = "[GET_OR_GEN_AUDIO]"
        if not audio_content_string or not audio_content_string.strip():
            logger.debug(f"{log_prefix} Nội dung audio rỗng hoặc chỉ chứa khoảng trắng. Trả về None.")
            return None, True, "Nội dung audio rỗng."
        
        try:
            content_hash = hashlib.sha1(audio_content_string.encode('utf-8')).hexdigest()
            cache_filename = f"{content_hash}.{output_format}"
            cache_dir = self._ensure_cache_dir()
            cached_file_path = os.path.join(cache_dir, cache_filename)
            
            if not force_refresh and os.path.exists(cached_file_path):
                logger.info(f"{log_prefix} Cache HIT: {cached_file_path}")
                return cached_file_path, True, "Đã tìm thấy trong cache."
            
            if force_refresh:
                logger.info(f"{log_prefix} Force refresh requested cho hash {content_hash}. Đang tạo mới...")
            else:
                logger.info(f"{log_prefix} Cache MISS cho hash {content_hash}. Đang tạo audio...")
            temp_generated_path, success, message = await self._generate_concatenated_audio(audio_content_string, output_format)
            
            if success and temp_generated_path and os.path.exists(temp_generated_path):
                logger.info(f"{log_prefix} Tạo thành công file tạm: {temp_generated_path}. Chuẩn bị cache...")
                try:
                    shutil.move(temp_generated_path, cached_file_path)
                    logger.info(f"[SYNC_CACHE] Cache thành công: {cached_file_path}")
                    return cached_file_path, True, "Tạo và cache audio thành công."
                except Exception as e_sync:
                    error_message = f"Lỗi copy/move vào cache từ {temp_generated_path} đến {cached_file_path}: {e_sync}"
                    logger.error(f"[SYNC_CACHE] {error_message}", exc_info=True)
                    if os.path.exists(temp_generated_path):
                        try:
                            os.remove(temp_generated_path)
                        except OSError as e_remove:
                            logger.error(f"[SYNC_CACHE] Lỗi xóa file tạm {temp_generated_path} sau khi copy lỗi: {e_remove}")
                    return None, False, f"Lỗi khi lưu file audio vào cache: {e_sync}"
            else:
                logger.error(f"{log_prefix} Tạo audio cho hash {content_hash} thất bại hoặc file tạm không tồn tại. Thông báo: {message}")
                return None, False, message
        except Exception as e:
            error_message = f"Lỗi nghiêm trọng trong quá trình lấy/tạo/cache audio: {e}"
            logger.critical(f"{log_prefix} {error_message}", exc_info=True)
            return None, False, error_message

    async def get_or_generate_audio_for_item(self, item, side, force_refresh=False):
        """
        Mô tả: Lấy hoặc tạo audio cho một LearningItem cụ thể.
        Naming convention: {side}_{item_id}.mp3
        Storage: container's media_audio_folder if set, else cache.
        """
        log_prefix = f"[ITEM_AUDIO|{item.item_id}|{side}]"
        
        # 1. Determine content to read
        content_to_read = ""
        if side == 'front':
            content_to_read = item.content.get('front_audio_content') or item.content.get('front')
        elif side == 'back':
            content_to_read = item.content.get('back_audio_content') or item.content.get('back')
            
        if not content_to_read or not str(content_to_read).strip():
            logger.warning(f"{log_prefix} Không có nội dung để tạo audio.")
            return None, False, "Không có nội dung để tạo audio."

        # 2. Determine target folder and paths
        container = item.container
        audio_folder = getattr(container, 'media_audio_folder', None)
        
        filename = f"{side}_{item.item_id}.mp3"
        
        if audio_folder:
            # Absolute path for FS operations
            target_dir = os.path.join(current_app.static_folder, audio_folder)
            os.makedirs(target_dir, exist_ok=True)
            target_path = os.path.join(target_dir, filename)
            # [STAKE] Store ONLY filename in DB if folder is set
            stored_value = filename
            full_relative_path = f"{audio_folder}/{filename}"
        else:
            # Fallback to general cache
            target_dir = self._ensure_cache_dir()
            target_path = os.path.join(target_dir, filename)
            # Store full relative path for generic cache
            stored_value = f"flashcard/audio/cache/{filename}"
            full_relative_path = stored_value

        # 3. Lookup: check physically if exists
        if not force_refresh and os.path.exists(target_path):
            logger.info(f"{log_prefix} Found existing file: {target_path}")
            return stored_value, full_relative_path, True, "Đã tìm thấy file."

        # 4. Generate fresh audio
        logger.info(f"{log_prefix} Generating fresh audio to: {target_path}")
        temp_path, success, msg = await self._generate_concatenated_audio(str(content_to_read))
        
        if success and temp_path:
            try:
                if os.path.exists(target_path):
                    os.remove(target_path)
                shutil.move(temp_path, target_path)
                logger.info(f"{log_prefix} Successfully created: {target_path}")
                return stored_value, full_relative_path, True, "Tạo thành công."
            except Exception as move_exc:
                logger.error(f"{log_prefix} Lỗi di chuyển file: {move_exc}", exc_info=True)
                return None, None, False, f"Lỗi lưu file: {move_exc}"
        
        return None, None, False, msg

    async def generate_cache_for_all_cards(self, task, container_ids=None):
        """
        Mô tả: Quét database theo phạm vi đã chọn, tạo các file audio còn thiếu và cập nhật trạng thái vào DB.
        """
        log_prefix = f"[{task.task_name}]"
        logger.info(f"{log_prefix} Bắt đầu tác vụ tạo cache audio.")

        try:
            normalized_container_ids = None
            scope_label = "tất cả bộ thẻ Flashcard"

            if container_ids:
                if not isinstance(container_ids, (list, tuple, set)):
                    container_ids = [container_ids]

                try:
                    normalized_container_ids = [int(cid) for cid in container_ids if cid is not None]
                except (TypeError, ValueError):
                    logger.warning(f"{log_prefix} Nhận được container_ids không hợp lệ: {container_ids}")
                    normalized_container_ids = None

            containers_in_scope = []
            if normalized_container_ids:
                containers_in_scope = LearningContainer.query.filter(LearningContainer.container_id.in_(normalized_container_ids)).all()
                if containers_in_scope:
                    if len(containers_in_scope) == 1:
                        c = containers_in_scope[0]
                        scope_label = f"bộ thẻ \"{c.title}\" (ID {c.container_id})"
                    else:
                        joined_titles = ", ".join([f"\"{c.title}\" (ID {c.container_id})" for c in containers_in_scope])
                        scope_label = f"{len(containers_in_scope)} bộ thẻ đã chọn: {joined_titles}"
                else:
                    scope_label = "các bộ thẻ đã chọn"

            task.message = f"Đang quét dữ liệu cho {scope_label}..."
            db.session.commit()

            all_audio_contents = set()
            cards_query = LearningItem.query.filter(
                LearningItem.item_type == 'FLASHCARD',
                (LearningItem.content['front_audio_content'] != None) & (LearningItem.content['front_audio_content'] != '') |
                (LearningItem.content['back_audio_content'] != None) & (LearningItem.content['back_audio_content'] != '')
            )

            if normalized_container_ids:
                cards_query = cards_query.filter(LearningItem.container_id.in_(normalized_container_ids))

            cards_with_audio = cards_query.all()

            for card in cards_with_audio:
                if card.content.get('front_audio_content'):
                    all_audio_contents.add(card.content.get('front_audio_content').strip())
                if card.content.get('back_audio_content'):
                    all_audio_contents.add(card.content.get('back_audio_content').strip())

            cache_dir = self._ensure_cache_dir()
            contents_to_generate = []
            for content in all_audio_contents:
                content_hash = hashlib.sha1(content.encode('utf-8')).hexdigest()
                cached_file_path = os.path.join(cache_dir, f"{content_hash}.mp3")
                if not os.path.exists(cached_file_path):
                    contents_to_generate.append(content)

            task.total = len(contents_to_generate)
            task.progress = 0
            task.status = 'running'
            db.session.commit()
            logger.info(f"{log_prefix} Tìm thấy {task.total} nội dung audio mới cần tạo cache trong {scope_label}.")

            if task.total == 0:
                task.message = f"Hoàn tất! Không có audio mới nào cần tạo trong {scope_label}."
                task.status = 'completed'
                db.session.commit()
                return

            created_count = 0
            for content in contents_to_generate:
                db.session.refresh(task)
                if task.stop_requested:
                    task.message = f"Đã dừng. Xử lý được {created_count}/{task.total} file trong {scope_label}."
                    task.status = 'completed'
                    logger.info(f"{log_prefix} Nhận được yêu cầu dừng.")
                    break

                task.message = f"Đang xử lý '{content[:40]}...' ({task.progress + 1}/{task.total}) trong {scope_label}"
                db.session.commit()

                try:
                    _, success, message = await self.get_cached_or_generate_audio(content)
                    if success:
                        created_count += 1
                    else:
                        logger.error(f"{log_prefix} Lỗi khi xử lý nội dung: '{content[:50]}...': {message}")
                        task.message = f"Lỗi: {message} ({task.progress + 1}/{task.total}) trong {scope_label}"
                        task.status = 'error'
                        db.session.commit()
                        return # Dừng tác vụ nếu gặp lỗi nghiêm trọng
                except Exception as e:
                    logger.error(f"{log_prefix} Lỗi không mong muốn khi xử lý: '{content[:50]}...': {e}", exc_info=True)
                    task.message = f"Lỗi không mong muốn: {str(e)} ({task.progress + 1}/{task.total}) trong {scope_label}"
                    task.status = 'error'
                    db.session.commit()
                    return # Dừng tác vụ nếu gặp lỗi nghiêm trọng
                finally:
                    task.progress += 1
                    db.session.commit()

            if not task.stop_requested:
                task.message = f"Hoàn tất! Đã tạo thành công {created_count}/{task.total} file audio mới trong {scope_label}."
                task.status = 'completed'
                logger.info(f"{log_prefix} {task.message}")

        except Exception as e:
            task.message = f"Lỗi nghiêm trọng trong {scope_label}: {e}"
            task.status = 'error'
            logger.error(f"{log_prefix} {task.message}", exc_info=True)
        
        finally:
            if task.status == 'running':
                task.status = 'idle'
            task.is_enabled = False
            task.stop_requested = False
            db.session.commit()

    def clean_orphan_audio_cache(self, task):
        """
        Mô tả: Dọn dẹp các file audio trong cache không còn được liên kết với bất kỳ flashcard nào.
        """
        log_prefix = f"[{task.task_name}]"
        logger.info(f"{log_prefix} Bắt đầu quá trình dọn dẹp cache audio.")
        
        task.status = 'running'
        task.message = 'Đang quét và dọn dẹp cache...'
        task.progress = 0
        task.total = 0 # Không thể biết trước tổng số file, nên sẽ cập nhật sau
        db.session.commit()

        try:
            active_audio_contents = set()
            cards_with_audio = LearningItem.query.filter(
                LearningItem.item_type == 'FLASHCARD',
                (LearningItem.content['front_audio_content'] != None) & (LearningItem.content['front_audio_content'] != '') |
                (LearningItem.content['back_audio_content'] != None) & (LearningItem.content['back_audio_content'] != '')
            ).all()

            for card in cards_with_audio:
                if task.stop_requested: break
                if card.content.get('front_audio_content'):
                    active_audio_contents.add(card.content.get('front_audio_content').strip())
                if card.content.get('back_audio_content'):
                    active_audio_contents.add(card.content.get('back_audio_content').strip())

            valid_cache_files = set()
            for content in active_audio_contents:
                content_hash = hashlib.sha1(content.encode('utf-8')).hexdigest()
                valid_cache_files.add(f"{content_hash}.mp3")

            logger.info(f"{log_prefix} Tìm thấy {len(valid_cache_files)} file cache hợp lệ trong database.")

            deleted_count = 0
            cache_dir = self._get_cache_dir()
            if not os.path.exists(cache_dir):
                logger.warning(f"{log_prefix} Thư mục cache không tồn tại: {cache_dir}")
                task.message = f"Thư mục cache không tồn tại. Hoàn tất."
                task.status = 'completed'
                db.session.commit()
                return

            all_files = os.listdir(cache_dir)
            task.total = len(all_files)
            db.session.commit()

            for filename in all_files:
                if task.stop_requested:
                    task.message = f"Đã dừng. Dọn dẹp được {deleted_count} file."
                    task.status = 'completed'
                    break

                if filename.endswith('.mp3') and filename not in valid_cache_files:
                    try:
                        file_path = os.path.join(cache_dir, filename)
                        os.remove(file_path)
                        deleted_count += 1
                        logger.info(f"{log_prefix} Đã xóa file cache mồ côi: {filename}")
                    except OSError as e:
                        logger.error(f"{log_prefix} Lỗi khi xóa file {filename}: {e}")
                
                task.progress += 1
                db.session.commit()
            
            if not task.stop_requested:
                task.message = f"Hoàn tất. Đã xóa {deleted_count} file cache không hợp lệ."
                task.status = 'completed'
                logger.info(f"{log_prefix} {task.message}")

        except Exception as e:
            task.message = f"Lỗi nghiêm trọng: {e}"
            task.status = 'error'
            logger.error(f"{log_prefix} {task.message}", exc_info=True)
        
        finally:
            if task.status == 'running':
                task.status = 'idle'
            task.is_enabled = False
            task.stop_requested = False
            db.session.commit()

    async def regenerate_audio_for_card(self, flashcard_id, side):
        """
        Mô tả: Tái tạo file audio cho một mặt cụ thể của một flashcard.
        Args:
            flashcard_id (int): ID của flashcard.
            side (str): 'front' hoặc 'back'.
        Returns:
            tuple: (thành công (bool), thông báo lỗi/thành công).
                   Trả về (False, message) nếu có lỗi.
        """
        log_prefix = f"[AUDIO_SERVICE|Regenerate|Card:{flashcard_id}|Side:{side}]"
        logger.info(f"{log_prefix} Bắt đầu tái tạo audio.")

        card = LearningItem.query.filter_by(item_id=flashcard_id, item_type='FLASHCARD').first()
        if not card:
            logger.error(f"{log_prefix} Không tìm thấy flashcard.")
            return False, "Không tìm thấy flashcard."

        audio_content = None
        if side == 'front':
            audio_content = card.content.get('front_audio_content')
        elif side == 'back':
            audio_content = card.content.get('back_audio_content')
        
        if not audio_content or not audio_content.strip():
            logger.warning(f"{log_prefix} Không có nội dung audio để tái tạo.")
            return False, "Không có nội dung audio để tái tạo."

        try:
            content_hash = hashlib.sha1(audio_content.encode('utf-8')).hexdigest()
            cache_filename = f"{content_hash}.mp3"
            cache_dir = self._ensure_cache_dir()
            cached_file_path = os.path.join(cache_dir, cache_filename)
            if os.path.exists(cached_file_path):
                os.remove(cached_file_path)
                logger.info(f"{log_prefix} Đã xóa file cache cũ: {cache_filename}")

            new_path, success, message = await self.get_cached_or_generate_audio(audio_content)
            if success:
                logger.info(f"{log_prefix} Tái tạo audio thành công.")
                return True, "Tái tạo audio thành công."
            else:
                logger.error(f"{log_prefix} Tái tạo audio thất bại. Thông báo: {message}")
                return False, message
        except Exception as e:
            error_message = f"Lỗi nghiêm trọng khi tái tạo audio: {e}"
            logger.error(f"{log_prefix} {error_message}", exc_info=True)
            return False, error_message