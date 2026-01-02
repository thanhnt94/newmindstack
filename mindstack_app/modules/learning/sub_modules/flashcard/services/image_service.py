"""
Dịch vụ hỗ trợ tìm kiếm và tải ảnh minh họa cho flashcard mà không cần API khóa.
"""

import asyncio
import glob
import hashlib
import logging
import mimetypes
import os
import time
from typing import Iterable, Optional, Tuple
from urllib.parse import urlparse

import requests

try:  # Ưu tiên package mới "ddgs" sau khi được đổi tên
    from ddgs import DDGS  # type: ignore[import-not-found]
    from ddgs import exceptions as _ddgs_exceptions  # type: ignore[import-not-found]
    DuckDuckGoSearchException = getattr(  # type: ignore[assignment]
        _ddgs_exceptions,
        "DuckDuckGoSearchException",
        getattr(_ddgs_exceptions, "DDGSearchException", Exception),
    )
except ModuleNotFoundError:  # Fallback cho môi trường chưa nâng cấp
    from duckduckgo_search import DDGS  # type: ignore[import-not-found]
    from duckduckgo_search.exceptions import (  # type: ignore[import-not-found]
        DuckDuckGoSearchException,
    )
from sqlalchemy.orm.attributes import flag_modified

from mindstack_app.config import Config
from mindstack_app.db_instance import db
from mindstack_app.models import LearningContainer, LearningItem

logger = logging.getLogger(__name__)

class ImageService:
    """Cung cấp tiện ích tìm kiếm, cache và dọn dẹp ảnh minh họa cho flashcard."""

    USER_AGENT = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"
    )
    MAX_IMAGE_SIZE_BYTES = 5 * 1024 * 1024  # 5 MB
    SUPPORTED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp"}

    def __init__(self) -> None:
        self._relative_cache_dir = "flashcard/images/cache" # Default value

    # ------------------------------------------------------------------
    # Các hàm tiện ích nội bộ
    # ------------------------------------------------------------------
    def _get_cache_dir(self) -> str:
        from mindstack_app.services.config_service import get_runtime_config
        return get_runtime_config('FLASHCARD_IMAGE_CACHE_DIR', Config.FLASHCARD_IMAGE_CACHE_DIR)

    def _get_upload_dir(self) -> str:
        from mindstack_app.services.config_service import get_runtime_config
        return get_runtime_config('UPLOAD_FOLDER', Config.UPLOAD_FOLDER)

    def _ensure_cache_dir(self) -> str:
        cache_dir = self._get_cache_dir()
        os.makedirs(cache_dir, exist_ok=True)
        try:
             self._relative_cache_dir = os.path.relpath(cache_dir, self._get_upload_dir()).replace(os.path.sep, "/")
        except Exception:
             pass # Stick to default if path rel fails
        return cache_dir

    def _find_existing_cache(self, content_hash: str) -> Optional[str]:
        pattern = os.path.join(self._get_cache_dir(), f"{content_hash}.*")
        matches = glob.glob(pattern)
        if matches:
            matches.sort(key=os.path.getmtime, reverse=True)
            return matches[0]
        return None

    def _guess_extension(self, image_url: str, content_type: Optional[str]) -> str:
        if content_type:
            guessed = mimetypes.guess_extension(content_type.split(";")[0].strip())
            if guessed:
                guessed = guessed.lower()
                if guessed == ".jpe":
                    guessed = ".jpg"
                if guessed in self.SUPPORTED_EXTENSIONS:
                    return guessed
        path_ext = os.path.splitext(urlparse(image_url).path)[1].lower()
        if path_ext in self.SUPPORTED_EXTENSIONS:
            return ".jpg" if path_ext == ".jpe" else path_ext
        return ".jpg"

    def _download_image(self, image_url: str, content_hash: str) -> Tuple[Optional[str], bool, str]:
        headers = {"User-Agent": self.USER_AGENT}
        try:
            response = requests.get(image_url, timeout=20, stream=True, headers=headers)
            response.raise_for_status()
        except requests.RequestException as exc:  # pylint: disable=broad-except
            logger.debug("Không thể tải ảnh %s: %s", image_url, exc)
            return None, False, f"Không thể tải ảnh: {exc}"

        content_type = response.headers.get("Content-Type", "").lower()
        if "image" not in content_type and not os.path.splitext(urlparse(image_url).path)[1]:
            return None, False, "Không xác định được định dạng ảnh."

        extension = self._guess_extension(image_url, content_type)
        cache_path = os.path.join(self._ensure_cache_dir(), f"{content_hash}{extension}")

        total_bytes = 0
        try:
            with open(cache_path, "wb") as file_handle:
                for chunk in response.iter_content(chunk_size=32768):
                    if not chunk:
                        continue
                    total_bytes += len(chunk)
                    if total_bytes > self.MAX_IMAGE_SIZE_BYTES:
                        raise ValueError("Kích thước ảnh vượt quá giới hạn 5MB")
                    file_handle.write(chunk)
        except Exception as exc:  # pylint: disable=broad-except
            if os.path.exists(cache_path):
                try:
                    os.remove(cache_path)
                except OSError:
                    pass
            logger.debug("Lỗi khi ghi ảnh %s: %s", image_url, exc, exc_info=True)
            return None, False, str(exc)

        return cache_path, True, "Đã tải ảnh thành công."

    def _normalize_stored_path(self, stored_path: Optional[str]) -> Optional[str]:
        if not stored_path:
            return None
        normalized = str(stored_path).strip().lstrip("/")
        if normalized.startswith("uploads/"):
            normalized = normalized[len("uploads/"):]
        return normalized

    def _to_relative_cache_path(self, absolute_path: str) -> Optional[str]:
        try:
            relative_path = os.path.relpath(absolute_path, self._get_upload_dir())
            return relative_path.replace(os.path.sep, "/")
        except ValueError:
            logger.error(
                "Không thể chuyển đường dẫn ảnh %s về tương đối từ %s",
                absolute_path,
                self._get_upload_dir(),
            )
            return None

    # ------------------------------------------------------------------
    # API công khai
    # ------------------------------------------------------------------
    def get_cached_or_download_image(self, text_to_search: str, *, max_results: int = 8) -> Tuple[Optional[str], bool, str]:
        """Tìm ảnh theo nội dung và cache kết quả nếu cần."""
        log_prefix = "[IMAGE_CACHE]"
        if not text_to_search or not text_to_search.strip():
            return None, False, "Nội dung tìm kiếm rỗng."

        normalized_text = " ".join(text_to_search.strip().split())
        content_hash = hashlib.sha1(normalized_text.encode("utf-8")).hexdigest()

        cached_path = self._find_existing_cache(content_hash)
        if cached_path and os.path.exists(cached_path):
            logger.info("%s Cache HIT cho hash %s", log_prefix, content_hash)
            return cached_path, True, "Đã tìm thấy ảnh trong cache."

        logger.info("%s Cache MISS cho hash %s. Đang tìm ảnh...", log_prefix, content_hash)
        retry_attempts = 3
        retry_delay_seconds = 3
        friendly_retry_message = "Dịch vụ tìm kiếm ảnh đang bận, vui lòng thử lại sau."

        for attempt in range(1, retry_attempts + 1):
            try:
                with DDGS() as ddgs:
                    results: Iterable[dict] = ddgs.images(
                        normalized_text,
                        safesearch="moderate",
                        region="wt-wt",
                        size="Medium",
                        max_results=max_results,
                    )
                    for result in results:
                        image_url = result.get("image") or result.get("thumbnail")
                        if not image_url:
                            continue
                        downloaded_path, success, message = self._download_image(image_url, content_hash)
                        if success and downloaded_path:
                            logger.info("%s Đã tải ảnh mới cho hash %s", log_prefix, content_hash)
                            return downloaded_path, True, "Đã tìm và lưu ảnh thành công."
                        logger.debug("%s Không thể dùng ảnh từ %s: %s", log_prefix, image_url, message)
                break
            except DuckDuckGoSearchException as exc:  # pylint: disable=broad-except
                logger.warning(
                    "%s DuckDuckGo trả về lỗi tạm thời (lần %s/%s): %s",
                    log_prefix,
                    attempt,
                    retry_attempts,
                    exc,
                )
                if attempt < retry_attempts:
                    time.sleep(retry_delay_seconds)
                    continue
                return None, False, friendly_retry_message
            except Exception as exc:  # pylint: disable=broad-except
                message_lower = str(exc).lower()
                if "rate limit" in message_lower or "http 202" in message_lower or "status code 202" in message_lower:
                    logger.warning(
                        "%s DuckDuckGo phản hồi đang bị giới hạn (lần %s/%s): %s",
                        log_prefix,
                        attempt,
                        retry_attempts,
                        exc,
                    )
                    if attempt < retry_attempts:
                        time.sleep(retry_delay_seconds)
                        continue
                    return None, False, friendly_retry_message
                logger.error("%s Lỗi khi tìm ảnh: %s", log_prefix, exc, exc_info=True)
                return None, False, f"Lỗi khi tìm ảnh: {exc}"

        return None, False, "Không tìm thấy ảnh phù hợp."

    async def generate_images_for_missing_cards(self, task, container_ids: Optional[Iterable[int]] = None) -> None:
        """Quét các thẻ thiếu ảnh và tự động bổ sung."""
        log_prefix = f"[{task.task_name}]"
        logger.info("%s Bắt đầu tạo ảnh minh họa cho các thẻ thiếu ảnh.", log_prefix)

        try:
            normalized_ids = None
            scope_label = "tất cả bộ thẻ Flashcard"

            if container_ids:
                normalized_ids = []
                for cid in container_ids:
                    try:
                        normalized_ids.append(int(cid))
                    except (TypeError, ValueError):
                        logger.warning("%s Bỏ qua container_id không hợp lệ: %s", log_prefix, cid)
                if normalized_ids:
                    containers = LearningContainer.query.filter(
                        LearningContainer.container_id.in_(normalized_ids)
                    ).all()
                    if containers:
                        if len(containers) == 1:
                            ctn = containers[0]
                            scope_label = f"bộ thẻ \"{ctn.title}\" (ID {ctn.container_id})"
                        else:
                            scope_label = f"{len(containers)} bộ thẻ được chọn"

            task.status = "running"
            task.message = f"Đang quét dữ liệu cho {scope_label}..."
            task.progress = 0
            db.session.commit()

            cards_query = LearningItem.query.filter(LearningItem.item_type == "FLASHCARD")
            if normalized_ids:
                cards_query = cards_query.filter(LearningItem.container_id.in_(normalized_ids))

            target_cards = []
            for card in cards_query.all():
                content = card.content or {}
                front_text = (content.get("front") or "").strip()
                has_image = bool(content.get("front_img") and str(content.get("front_img")).strip())
                if front_text and not has_image:
                    target_cards.append((card, front_text))

            task.total = len(target_cards)
            db.session.commit()

            if task.total == 0:
                task.message = f"Hoàn tất! Không có thẻ nào thiếu ảnh trong {scope_label}."
                task.status = "completed"
                db.session.commit()
                return

            created_count = 0
            for card, front_text in target_cards:
                db.session.refresh(task)
                if task.stop_requested:
                    task.message = (
                        f"Đã dừng. Đã xử lý {task.progress}/{task.total} thẻ trong {scope_label}."
                    )
                    task.status = "completed"
                    db.session.commit()
                    logger.info("%s Nhận được yêu cầu dừng, kết thúc sớm.", log_prefix)
                    break

                task.message = (
                    f"Đang xử lý thẻ ID {card.item_id} ({task.progress + 1}/{task.total}) trong {scope_label}"
                )
                db.session.commit()

                try:
                    cached_path, success, message = await asyncio.to_thread(
                        self.get_cached_or_download_image, front_text
                    )
                    if success and cached_path:
                        relative_path = self._to_relative_cache_path(cached_path)
                        if relative_path:
                            card.content["front_img"] = relative_path
                            flag_modified(card, "content")
                            db.session.commit()
                            created_count += 1
                        else:
                            logger.error(
                                "%s Không thể chuyển đường dẫn ảnh cho thẻ %s", log_prefix, card.item_id
                            )
                    else:
                        logger.warning(
                            "%s Không thể tạo ảnh cho thẻ %s: %s", log_prefix, card.item_id, message
                        )
                except Exception as exc:  # pylint: disable=broad-except
                    logger.error(
                        "%s Lỗi không mong muốn khi xử lý thẻ %s: %s",
                        log_prefix,
                        card.item_id,
                        exc,
                        exc_info=True,
                    )
                finally:
                    task.progress += 1
                    db.session.commit()

            if not task.stop_requested:
                task.message = (
                    f"Hoàn tất! Đã cập nhật ảnh cho {created_count}/{task.total} thẻ trong {scope_label}."
                )
                task.status = "completed"
                db.session.commit()

        except Exception as exc:  # pylint: disable=broad-except
            task.message = f"Lỗi nghiêm trọng: {exc}"
            task.status = "error"
            db.session.commit()
            logger.error("%s %s", log_prefix, task.message, exc_info=True)
        finally:
            if task.status == "running":
                task.status = "idle"
            task.is_enabled = False
            task.stop_requested = False
            db.session.commit()

    def clean_orphan_image_cache(self, task) -> None:
        """Xóa các ảnh cache không còn được tham chiếu bởi flashcard nào."""
        log_prefix = f"[{task.task_name}]"
        logger.info("%s Bắt đầu dọn dẹp cache ảnh.", log_prefix)

        task.status = "running"
        task.message = "Đang quét và dọn dẹp cache ảnh..."
        task.progress = 0
        task.total = 0
        db.session.commit()

        try:
            cache_dir = self._get_cache_dir()
            if not os.path.exists(cache_dir):
                task.message = "Thư mục cache ảnh không tồn tại."
                task.status = "completed"
                db.session.commit()
                return

            active_filenames = set()
            cards = LearningItem.query.filter(LearningItem.item_type == "FLASHCARD").all()
            for card in cards:
                content = card.content or {}
                for key in ("front_img", "back_img"):
                    relative_path = self._normalize_stored_path(content.get(key))
                    if relative_path and relative_path.startswith(self._relative_cache_dir):
                        active_filenames.add(os.path.basename(relative_path))

            all_files = [name for name in os.listdir(cache_dir) if os.path.isfile(os.path.join(cache_dir, name))]
            task.total = len(all_files)
            db.session.commit()

            deleted_count = 0
            for filename in all_files:
                db.session.refresh(task)
                if task.stop_requested:
                    task.message = f"Đã dừng. Đã xóa {deleted_count} ảnh cache."
                    task.status = "completed"
                    db.session.commit()
                    return

                if filename not in active_filenames:
                    try:
                        os.remove(os.path.join(cache_dir, filename))
                        deleted_count += 1
                    except OSError as exc:
                        logger.error(
                            "%s Không thể xóa file %s: %s", log_prefix, filename, exc
                        )
                task.progress += 1
                db.session.commit()

            task.message = f"Hoàn tất. Đã xóa {deleted_count} ảnh cache không dùng."
            task.status = "completed"
            db.session.commit()
        except Exception as exc:  # pylint: disable=broad-except
            task.message = f"Lỗi khi dọn dẹp cache: {exc}"
            task.status = "error"
            db.session.commit()
            logger.error("%s %s", log_prefix, task.message, exc_info=True)
        finally:
            if task.status == "running":
                task.status = "idle"
            task.is_enabled = False
            task.stop_requested = False
            db.session.commit()

    # ------------------------------------------------------------------
    # Hàm tiện ích dùng chung bên ngoài dịch vụ
    # ------------------------------------------------------------------
    def convert_to_static_url(self, absolute_path: str) -> Optional[str]:
        """Trả về đường dẫn tương đối (dùng với url_for('static', ...))."""
        relative_path = self._to_relative_cache_path(absolute_path)
        if relative_path:
            return relative_path
        return None
