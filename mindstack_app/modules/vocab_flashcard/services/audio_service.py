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

from mindstack_app.core.extensions import db
from mindstack_app.models import LearningContainer, LearningItem, User, BackgroundTask
from mindstack_app.core.config import Config
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

    def _safe_remove(self, path: str, retries: int = 3, delay: float = 0.2):
        """Helper to remove file with retries (handling Windows file locking)"""
        if not os.path.exists(path):
            return
            
        for i in range(retries):
            try:
                os.remove(path)
                return
            except OSError as e:
                if i == retries - 1:
                    logger.warning(f"Could not remove file {path} after {retries} attempts: {e}")
                    raise
                import time
                time.sleep(delay)

    async def _generate_concatenated_audio(self, audio_content_string, output_format="mp3", pause_ms=400):
        """
        [DEPRECATED INTERNAL LOGIC]
        Delegates to the Central AudioService to generate the file.
        Returns: (physical_path, success, message)
        """
        from mindstack_app.modules.audio.services.audio_service import AudioService as CentralAudioService
        
        # We use a temp filename, CentralService will return the path
        # But CentralService.get_audio handles caching internally if we don't provide custom path,
        # OR writes to custom path if provided.
        # Here we want a temp file behavior or direct return?
        # The caller of this method (get_cached_or_generate_audio) expects a temp path to then move.
        # Actually, get_cached_or_generate_audio calls this.
        
        # Let's simplify: We can refactor get_cached_or_generate_audio to call Central directly
        # and skip this intermediate temp file generation if possible.
        # But to keep signature compatibility for now, let's implement this wrapper.
        
        try:
            # We want a temp file
            import tempfile
            fd, temp_path = tempfile.mkstemp(suffix=f".{output_format}")
            os.close(fd)
            # We don't want to keep it if generation fails, ensuring cleanup is important
            
            # Call Central Service with auto_voice_parsing=True (enables the new logic)
            # We pass custom_filename (absolute path) as the target so it writes there directly?
            # CentralService.get_audio -> if custom_filename provided -> treats as filename in target_dir?
            # Let's look at CentralService logic:
            # if custom_filename: filename = custom_filename...
            # paths = get_storage_path(target_dir, filename) -> joins target_dir + filename
            
            # So if we want to write to a specific TEMP path, it's tricky with CentralService's path resolution.
            # CentralService expects to manage the directory structure generally.
            
            # ALTERNATIVE: Use the internal helper _generate_concatenated_audio from CentralService?
            # Yes, that is exposed as a classmethod.
            
            success = await CentralAudioService._generate_concatenated_audio(audio_content_string, temp_path)
            if success:
                 return temp_path, True, "Generation success via Central Service"
            else:
                 return None, False, "Generation failed via Central Service"
                 
        except Exception as e:
            return None, False, str(e)

    def _generate_tts_sync(self, text, lang='en'):
         # Deprecated, kept just in case of weird legacy calls, but shouldn't be used if we route via above.
         pass

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

    async def get_or_generate_audio_for_item(self, item, side, force_refresh=False, auto_save_to_db=True):
        """
        Mô tả: Lấy hoặc tạo audio cho một LearningItem cụ thể.
        Naming convention: {side}_{item_id}.mp3
        Storage: container's media_audio_folder if set, else cache.
        [UPDATED] Now also ensures DB consistency if file exists but link is missing.
        """
        log_prefix = f"[ITEM_AUDIO|{item.item_id}|{side}]"
        from sqlalchemy.orm.attributes import flag_modified
        from mindstack_app.utils.db_session import safe_commit

        # 1. Determine content to read
        content_to_read = ""
        url_field = f"{side}_audio_url"
        
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
            target_dir = os.path.join(current_app.config['UPLOAD_FOLDER'], audio_folder)
            os.makedirs(target_dir, exist_ok=True)
            target_path = os.path.join(target_dir, filename)
            stored_value = filename
            full_relative_path = f"{audio_folder}/{filename}"
        else:
            target_dir = self._ensure_cache_dir()
            target_path = os.path.join(target_dir, filename)
            stored_value = f"flashcard/audio/cache/{filename}"
            full_relative_path = stored_value

        # 3. DB & Physical Sync Check
        physical_exists = os.path.exists(target_path)
        db_value = item.content.get(url_field)
        
        # If file exists and NOT forcing refresh
        if not force_refresh and physical_exists:
            # Check if DB needs update
            if db_value != stored_value:
                logger.info(f"{log_prefix} Physical file exists but DB link mismatch ({db_value} vs {stored_value}). Updating DB...")
                if auto_save_to_db:
                    try:
                        item.content[url_field] = stored_value
                        flag_modified(item, 'content')
                        safe_commit(db.session)
                    except Exception as db_exc:
                        logger.warning(f"{log_prefix} Failed to auto-sync DB: {db_exc}")
            
            return stored_value, full_relative_path, True, "Đã tìm thấy file và đồng bộ DB."

        # 4. Generate fresh audio
        logger.info(f"{log_prefix} Generating fresh audio to: {target_path}")
        temp_path, success, msg = await self._generate_concatenated_audio(str(content_to_read))
        
        if success and temp_path:
            try:
                if os.path.exists(target_path):
                    self._safe_remove(target_path) # Use safe remove for Windows
                shutil.move(temp_path, target_path)
                
                # Update DB after successful generation
                if auto_save_to_db and item.content.get(url_field) != stored_value:
                    try:
                        item.content[url_field] = stored_value
                        flag_modified(item, 'content')
                        safe_commit(db.session)
                        logger.info(f"{log_prefix} Successfully created and saved to DB: {target_path}")
                    except Exception as db_exc:
                        logger.warning(f"{log_prefix} File created but DB update failed: {db_exc}")
                else:
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
                # [FIX] Use safe remove to handle Windows file locking
                self._safe_remove(cached_file_path)
                logger.info(f"{log_prefix} Đã xóa file cache cũ (safe): {cache_filename}")

            new_path, success, message = await self.get_cached_or_generate_audio(audio_content, force_refresh=True)
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

    @staticmethod
    def ensure_audio_for_item(item, side='front', auto_save_to_db=True):
        """
        Static helper to trigger audio generation synchronously (handles its own loop).
        Useful for background threads.
        """
        service = AudioService()
        try:
            # asyncio.run is the modern way to run a coroutine in a new loop
            return asyncio.run(service.get_or_generate_audio_for_item(item, side, auto_save_to_db=auto_save_to_db))
        except RuntimeError:
            # Fails if a loop is already running in this thread
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                return loop.run_until_complete(service.get_or_generate_audio_for_item(item, side, auto_save_to_db=auto_save_to_db))
            finally:
                loop.close()
        except Exception as e:
            logger.error(f"[AudioService] Static ensure failed: {e}")
            return None, None, False, str(e)
