import os
import tempfile
import pandas as pd
import re
import shutil
from flask import current_app
from sqlalchemy.orm.attributes import flag_modified
from mindstack_app.models import db, LearningContainer, LearningItem
from mindstack_app.modules.shared.utils.db_session import safe_commit
from mindstack_app.modules.shared.utils.excel import extract_info_sheet_mapping, format_info_warnings
from mindstack_app.modules.shared.utils.media_paths import (
    normalize_media_folder,
    normalize_media_value_for_storage,
)

class FlashcardExcelService:
    """Service xử lý các nghiệp vụ liên quan đến Excel cho Flashcard."""

    @staticmethod
    def _process_relative_url(url, media_folder=None):
        """Helper local: Chuẩn hóa dữ liệu URL/đường dẫn."""
        if url is None:
            return None
        normalized = str(url).strip()
        if not normalized:
            return ''
        if normalized.startswith(('http://', 'https://')):
            return normalized
        return normalize_media_value_for_storage(normalized, media_folder)

    @staticmethod
    def _get_media_folders_from_container(container) -> dict[str, str]:
        if not container:
            return {}
        folders = getattr(container, 'media_folders', {}) or {}
        if folders:
            return dict(folders)
        return {}

    @classmethod
    def process_import(cls, container_id: int, excel_file) -> str:
        """
        Xử lý logic import dữ liệu từ file Excel vào bộ Flashcard.
        Trả về thông báo kết quả (string).
        """
        temp_filepath = None
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx') as tmp_file:
                excel_file.save(tmp_file.name)
                temp_filepath = tmp_file.name

            df = pd.read_excel(temp_filepath, sheet_name='Data')
            required_cols = ['front', 'back']
            if not all(col in df.columns for col in required_cols):
                raise ValueError(
                    f"File Excel (sheet 'Data') phải có các cột bắt buộc: {', '.join(required_cols)}."
                )

            flashcard_set = LearningContainer.query.get(container_id)
            if not flashcard_set:
                raise ValueError("Không tìm thấy bộ thẻ.")

            info_notices: list[str] = []
            media_overrides: dict[str, str] = {}
            cover_value = None
            info_mapping, info_warnings = extract_info_sheet_mapping(temp_filepath)
            
            if info_mapping:
                image_folder_override = normalize_media_folder(info_mapping.get('image_base_folder'))
                audio_folder_override = normalize_media_folder(info_mapping.get('audio_base_folder'))
                cover_value = info_mapping.get('cover_image')
                if image_folder_override:
                    media_overrides['image'] = image_folder_override
                if audio_folder_override:
                    media_overrides['audio'] = audio_folder_override
            if info_warnings:
                info_notices.extend(info_warnings)

            if media_overrides:
                flashcard_set.set_media_folders(media_overrides)

            media_folders = cls._get_media_folders_from_container(flashcard_set)
            image_folder = media_folders.get('image')
            audio_folder = media_folders.get('audio')

            if cover_value is not None:
                flashcard_set.cover_image = cls._process_relative_url(str(cover_value), image_folder)

            existing_items = (
                LearningItem.query.filter_by(container_id=container_id, item_type='FLASHCARD')
                .order_by(LearningItem.order_in_container, LearningItem.item_id)
                .all()
            )
            existing_map = {item.item_id: item for item in existing_items}
            processed_ids = set()
            delete_ids = set()
            ordered_entries = []

            optional_fields = [
                'front_audio_content', 'back_audio_content', 'front_img', 'back_img',
                'front_audio_url', 'back_audio_url', 'ai_prompt',
                'supports_pronunciation', 'supports_writing', 'supports_quiz',
                'supports_essay', 'supports_listening', 'supports_speaking',
            ]
            url_fields = {'front_img', 'back_img', 'front_audio_url', 'back_audio_url'}
            capability_fields = {
                'supports_pronunciation', 'supports_writing', 'supports_quiz',
                'supports_essay', 'supports_listening', 'supports_speaking'
            }
            
            # Logic lấy capabilities từ container (đơn giản hóa)
            container_capabilities = set()
            if hasattr(flashcard_set, 'capability_flags'):
                container_capabilities = set(flashcard_set.capability_flags())

            stats = {'updated': 0, 'created': 0, 'deleted': 0, 'skipped': 0, 'reordered': 0}

            action_aliases = {
                'delete': {'delete', 'remove'},
                'skip': {'skip', 'keep', 'none', 'ignore', 'nochange', 'unchanged', 'giu nguyen', 'giu-nguyen', 'giu_nguyen'},
                'create': {'create', 'new', 'add', 'insert'},
                'update': {'update', 'upsert', 'edit', 'modify'},
            }

            def _normalize_action(raw_action: str | None, *, has_item_id: bool) -> str:
                value = (raw_action or '').strip().lower()
                if value:
                    for normalized, alias_values in action_aliases.items():
                        if value in alias_values:
                            if normalized == 'create' and has_item_id: return 'update'
                            if normalized == 'update' and not has_item_id: return 'create'
                            return normalized
                return 'update' if has_item_id else 'create'

            def _get_cell(row_data, column_name):
                if column_name not in df.columns: return None
                value = row_data[column_name]
                if pd.isna(value): return None
                return str(value).strip()

            for index, row in df.iterrows():
                item_id_value = _get_cell(row, 'item_id')
                order_value = _get_cell(row, 'order_in_container')
                order_number = None
                if order_value:
                    try:
                        order_number = int(float(order_value))
                        stats['reordered'] += 1
                    except (TypeError, ValueError):
                        raise ValueError(f"Hàng {index + 2}: order_in_container '{order_value}' không hợp lệ.")

                front_content = _get_cell(row, 'front')
                back_content = _get_cell(row, 'back')

                item_id = None
                if item_id_value:
                    try:
                        item_id = int(float(item_id_value))
                    except (TypeError, ValueError):
                        raise ValueError(f"Hàng {index + 2}: item_id '{item_id_value}' không hợp lệ.")

                action_value = _normalize_action(_get_cell(row, 'action'), has_item_id=bool(item_id))

                if item_id:
                    item = existing_map.get(item_id)
                    if not item:
                        raise ValueError(f"Hàng {index + 2}: Không tìm thấy thẻ với ID {item_id}.")

                    if action_value == 'delete':
                        delete_ids.add(item_id)
                        stats['deleted'] += 1
                        continue

                    if action_value == 'skip':
                        ordered_entries.append({
                            'type': 'existing', 'item': item,
                            'order': order_number if order_number is not None else (item.order_in_container or 0),
                            'sequence': index,
                        })
                        processed_ids.add(item_id)
                        stats['skipped'] += 1
                        continue

                    if not front_content or not back_content:
                        raise ValueError(f"Hàng {index + 2}: Thẻ với ID {item_id} thiếu dữ liệu front/back.")

                    content_dict = item.content or {}
                    content_dict['front'] = front_content
                    content_dict['back'] = back_content
                    ai_explanation_value = _get_cell(row, 'ai_explanation')
                    content_dict.pop('ai_explanation', None)
                    
                    for field in optional_fields:
                        cell_value = _get_cell(row, field)
                        if cell_value:
                            if field in url_fields:
                                base_folder = image_folder if field in {'front_img', 'back_img'} else audio_folder
                                content_dict[field] = cls._process_relative_url(cell_value, base_folder)
                            elif field in capability_fields:
                                content_dict[field] = cell_value.lower() in {'true', '1', 'yes', 'y', 'on'}
                            else:
                                content_dict[field] = cell_value
                        else:
                            if field in capability_fields:
                                content_dict[field] = False
                            else:
                                content_dict.pop(field, None)
                                
                    for capability_flag in container_capabilities:
                        content_dict.setdefault(capability_flag, True)
                        
                    item.content = content_dict
                    flag_modified(item, 'content')
                    item.ai_explanation = ai_explanation_value or None
                    
                    # Update search text index
                    if hasattr(item, 'update_search_text'):
                        item.update_search_text()

                    ordered_entries.append({
                        'type': 'existing', 'item': item,
                        'order': order_number if order_number is not None else (item.order_in_container or 0),
                        'sequence': index,
                    })
                    processed_ids.add(item_id)
                    stats['updated'] += 1
                else:
                    if action_value in ('delete', 'skip'):
                        stats['skipped'] += 1
                        continue
                    if not front_content or not back_content:
                        stats['skipped'] += 1
                        continue

                    content_dict = {'front': front_content, 'back': back_content}
                    ai_explanation_value = _get_cell(row, 'ai_explanation')
                    for field in optional_fields:
                        cell_value = _get_cell(row, field)
                        if cell_value:
                            if field in url_fields:
                                base_folder = image_folder if field in {'front_img', 'back_img'} else audio_folder
                                content_dict[field] = cls._process_relative_url(cell_value, base_folder)
                            elif field in capability_fields:
                                content_dict[field] = cell_value.lower() in {'true', '1', 'yes', 'y', 'on'}
                            else:
                                content_dict[field] = cell_value
                        else:
                            if field in capability_fields:
                                content_dict[field] = False
                            else:
                                content_dict.pop(field, None)
                    for capability_flag in container_capabilities:
                        content_dict.setdefault(capability_flag, True)
                    ordered_entries.append({
                        'type': 'new', 'data': content_dict,
                        'ai_explanation': ai_explanation_value or None,
                        'order': order_number, 'sequence': index,
                    })
                    stats['created'] += 1

            untouched_items = [
                item for item in existing_items
                if item.item_id not in processed_ids and item.item_id not in delete_ids
            ]
            for offset, item in enumerate(untouched_items, start=len(df) + 1):
                ordered_entries.append({
                    'type': 'existing', 'item': item,
                    'order': item.order_in_container or 0, 'sequence': offset,
                })

            for delete_id in delete_ids:
                if delete_id in existing_map:
                    db.session.delete(existing_map[delete_id])

            ordered_entries.sort(key=lambda entry: (
                entry['order'] if entry['order'] is not None else float('inf'),
                entry['sequence'],
            ))

            next_order = 1
            for entry in ordered_entries:
                if entry['type'] == 'existing':
                    entry['item'].order_in_container = next_order
                else:
                    new_item = LearningItem(
                        container_id=container_id,
                        item_type='FLASHCARD',
                        content=entry['data'],
                        ai_explanation=entry.get('ai_explanation'),
                        order_in_container=next_order,
                    )
                    # Update search text index for new item
                    if hasattr(new_item, 'update_search_text'):
                        new_item.update_search_text()
                    db.session.add(new_item)
                next_order += 1

            summary_parts = [
                f"{stats['updated']} cập nhật",
                f"{stats['created']} thêm mới",
                f"{stats['deleted']} xoá",
                f"{stats['skipped']} giữ nguyên",
            ]
            if stats['reordered']:
                summary_parts.append(f"{stats['reordered']} dòng có sắp xếp lại")
            summary_text = ', '.join(summary_parts)
            if info_notices:
                summary_text += ' Lưu ý: ' + format_info_warnings(info_notices)
            return f'Bộ thẻ đã được xử lý: {summary_text}.'
        finally:
            if temp_filepath and os.path.exists(temp_filepath):
                os.remove(temp_filepath)
