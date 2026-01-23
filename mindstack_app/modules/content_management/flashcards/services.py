import os
import tempfile
import pandas as pd
import re
import shutil
from flask import current_app
from sqlalchemy.orm.attributes import flag_modified
from mindstack_app.models import db, LearningContainer, LearningItem
from mindstack_app.utils.db_session import safe_commit
from mindstack_app.utils.excel import extract_info_sheet_mapping, format_info_warnings, read_excel_with_formulas
from mindstack_app.utils.media_paths import (
    normalize_media_folder,
    normalize_media_value_for_storage,
)
from mindstack_app.services.flashcard_config_service import FlashcardConfigService
from mindstack_app.core.signals import content_created


class FlashcardExcelService:
    """Service xử lý các nghiệp vụ liên quan đến Excel cho Flashcard."""

    """Service xử lý các nghiệp vụ liên quan đến Excel cho Flashcard."""

    # Helpers for Config Service
    @classmethod
    def get_system_columns(cls):
        return set(FlashcardConfigService.get('FLASHCARD_SYSTEM_COLUMNS'))

    @classmethod
    def get_standard_columns(cls):
        return set(FlashcardConfigService.get('FLASHCARD_STANDARD_COLUMNS'))

    @classmethod
    def get_ai_columns(cls):
        return set(FlashcardConfigService.get('FLASHCARD_AI_COLUMNS'))

    URL_FIELDS = {'front_img', 'back_img', 'front_audio_url', 'back_audio_url'}


    @classmethod
    def analyze_column_structure(cls, filepath: str) -> dict:
        """
        Phân tích cấu trúc cột của sheet 'Data' trong file Excel.
        Trả về dictionary phân loại cột.
        """
        try:
            df = read_excel_with_formulas(filepath, sheet_name='Data')
            columns = set(df.columns)
            
            columns = set(df.columns)
            
            standard_cols = cls.get_standard_columns()
            system_cols = cls.get_system_columns()
            ai_cols = cls.get_ai_columns()

            found_standard = [col for col in columns if col in standard_cols]
            found_system = [col for col in columns if col in system_cols]
            found_ai = [col for col in columns if col in ai_cols]
            
            all_known = system_cols | standard_cols | ai_cols

            found_custom = [col for col in columns if col not in all_known]
            
            missing_required = [col for col in ['front', 'back'] if col not in columns]
            
            return {
                'success': True,
                'total_columns': len(columns),
                'standard_columns': sorted(found_standard),
                'custom_columns': sorted(found_custom),
                'system_columns': sorted(found_system),
                'ai_columns': sorted(found_ai),
                'missing_required': missing_required,
                'all_columns': sorted(list(columns))
            }
        except Exception as e:
            return {'success': False, 'error': str(e)}

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

            df = read_excel_with_formulas(temp_filepath, sheet_name='Data')
            required_cols = FlashcardConfigService.get('FLASHCARD_REQUIRED_COLUMNS') or ['front', 'back']
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

                # [NEW] Process Column Mappings for Learning Modes (Multiple Pairs)
                # Format: "question_col:answer_col | question_col2:answer_col2"
                modes = ['mcq', 'typing', 'matching', 'listening', 'speaking']
                new_settings = dict(flashcard_set.settings) if flashcard_set.settings else {}
                settings_updated = False
                
                for mode in modes:
                    pairs_key = f"{mode}_pairs"
                    pairs_val = info_mapping.get(pairs_key)
                    
                    if pairs_val:
                        if mode not in new_settings:
                            new_settings[mode] = {}
                        
                        # Parse string format: "q1:a1 | q2:a2"
                        pairs_list = []
                        raw_pairs = str(pairs_val).split('|')
                        for raw_pair in raw_pairs:
                            parts = raw_pair.split(':')
                            if len(parts) == 2:
                                q_col = parts[0].strip()
                                a_col = parts[1].strip()
                                if q_col and a_col:
                                    pairs_list.append({'q': q_col, 'a': a_col})
                        
                        if pairs_list:
                            new_settings[mode]['pairs'] = pairs_list
                            # Also update legacy/fallback fields for single-pair compatibility
                            new_settings[mode]['question_column'] = pairs_list[0]['q']
                            new_settings[mode]['answer_column'] = pairs_list[0]['a']
                            settings_updated = True
                
                if settings_updated:
                    flashcard_set.settings = new_settings
                    flag_modified(flashcard_set, 'settings')

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

            def log_debug(msg):
                try:
                    with open(r"c:\Code\MindStack\newmindstack\import_debug.log", "a", encoding="utf-8") as f:
                        f.write(f"{msg}\n")
                except Exception as e:
                     current_app.logger.error(f"Failed to write log: {e}")

            # Define local aliases for usage in processing loops
            standard_columns = cls.get_standard_columns()

            url_fields = cls.URL_FIELDS
            image_folder = media_overrides.get('image') or media_folders.get('image') or 'images'
            audio_folder = media_overrides.get('audio') or media_folders.get('audio') or 'audio'

            # ============ COLUMN CLASSIFICATION ============
            log_debug("--- NEW IMPORT STARTED ---")
            log_debug(f"DataFrame Columns: {list(df.columns)}")
            
            # Detect custom columns using Class Constants
            all_known_columns = cls.get_system_columns() | cls.get_standard_columns() | cls.get_ai_columns()
            custom_columns = [col for col in df.columns if col not in all_known_columns]

            
            if custom_columns:
                current_app.logger.info(f"Phát hiện {len(custom_columns)} cột custom: {custom_columns}")
            else:
                 current_app.logger.info("Không phát hiện cột custom nào.")

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

                    # Build content dict from standard columns
                    content_dict = item.content or {}
                    
                    # Clean up legacy fields from content
                    keys_to_remove = [k for k in content_dict.keys() if k.startswith('supports_')]
                    for k in keys_to_remove:
                        content_dict.pop(k, None)
                        
                    content_dict['front'] = front_content
                    content_dict['back'] = back_content
                    ai_explanation_value = _get_cell(row, 'ai_explanation')
                    content_dict.pop('ai_explanation', None)
                    
                    # Process standard optional columns
                    for field in standard_columns:
                        if field in {'front', 'back'}:
                            continue  # Already handled above
                        cell_value = _get_cell(row, field)
                        if cell_value:
                            if field in url_fields:
                                base_folder = image_folder if field in {'front_img', 'back_img'} else audio_folder
                                content_dict[field] = cls._process_relative_url(cell_value, base_folder)
                            else:
                                content_dict[field] = cell_value
                        else:
                            content_dict.pop(field, None)
                    
                    # Process custom columns into custom_data
                    custom_dict = item.custom_data or {}
                    for col in custom_columns:
                        cell_value = _get_cell(row, col)
                        if cell_value:
                            custom_dict[col] = cell_value
                        else:
                            custom_dict.pop(col, None)
                    
                    item.content = content_dict
                    flag_modified(item, 'content')
                    item.custom_data = custom_dict if custom_dict else None
                    flag_modified(item, 'custom_data')
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

                    # Build content dict from standard columns
                    content_dict = {'front': front_content, 'back': back_content}
                    
                    # [SAFETY] Ensure no legacy fields in new content
                    for k in list(content_dict.keys()):
                        if k.startswith('supports_'):
                            content_dict.pop(k, None)
                            
                    ai_explanation_value = _get_cell(row, 'ai_explanation')
                    
                    # Process standard optional columns
                    for field in standard_columns:
                        if field in {'front', 'back'}:
                            continue  # Already handled above
                        cell_value = _get_cell(row, field)
                        if cell_value:
                            if field in url_fields:
                                base_folder = image_folder if field in {'front_img', 'back_img'} else audio_folder
                                content_dict[field] = cls._process_relative_url(cell_value, base_folder)
                            else:
                                content_dict[field] = cell_value
                    
                    # Process custom columns into custom_data
                    custom_dict = {}
                    for col in custom_columns:
                        cell_value = _get_cell(row, col)
                        if cell_value:
                            custom_dict[col] = cell_value
                    
                    ordered_entries.append({
                        'type': 'new', 
                        'data': content_dict,
                        'custom_data': custom_dict if custom_dict else None,
                        'ai_explanation': ai_explanation_value or None,
                        'order': order_number, 
                        'sequence': index,
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
                        custom_data=entry.get('custom_data'),
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
            
            # Emit signal for other modules (notifications, analytics)
            if stats['created'] > 0 or stats['updated'] > 0:
                content_created.send(
                    None,
                    user_id=flashcard_set.owner_id,
                    content_type='flashcard_import',
                    content_id=container_id,
                    title=flashcard_set.title,
                    items_created=stats['created'],
                    items_updated=stats['updated']
                )
            
            return f'Bộ thẻ đã được xử lý: {summary_text}.'
        finally:
            if temp_filepath and os.path.exists(temp_filepath):
                os.remove(temp_filepath)
