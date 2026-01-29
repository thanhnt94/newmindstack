
import os
import tempfile
import pandas as pd
import re
import shutil
import io
import copy
import math
from typing import Optional
from flask import current_app, url_for
from sqlalchemy.orm.attributes import flag_modified
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.datavalidation import DataValidation
from mindstack_app.models import db, LearningContainer, LearningItem, LearningGroup, User, Note, ContainerContributor
from mindstack_app.utils.db_session import safe_commit
from mindstack_app.utils.excel import extract_info_sheet_mapping, format_info_warnings, read_excel_with_formulas
from mindstack_app.utils.media_paths import (
    normalize_media_folder,
    normalize_media_value_for_storage,
    build_relative_media_path,
)
from mindstack_app.config import Config
from mindstack_app.services.config_service import get_runtime_config
from mindstack_app.services.quiz_config_service import QuizConfigService


# Constants exported from here

# Valid actions for import
ACTION_OPTIONS = ['None', 'Update', 'Create', 'Delete', 'Skip']

GROUP_SHARED_COMPONENT_MAP = {
    'question': 'question',
    'pre_question_text': 'pre_question_text',
    'correct_answer': 'correct_answer',
    'explanation': 'explanation',
    'image': 'question_image_file',
    'audio': 'question_audio_file',
    'prompt': 'ai_prompt',
}


def parse_shared_components(raw_value) -> set[str]:
    """Parse a comma-separated string of shared component tokens."""
    if raw_value is None:
        return set()
    tokens = [
        token.strip().lower() for token in str(raw_value).split(',') if token and str(token).strip()
    ]
    return {token for token in tokens if token in GROUP_SHARED_COMPONENT_MAP}

class QuizExcelService:
    """Service handling Excel operations for Quiz Content Management."""
    
    @classmethod
    def get_data_columns(cls) -> list[str]:
        """Construct the full list of columns for the Data sheet."""
        # Fixed order to match typical user expectation, derived from config
        # We can implement a smarter ordering or just concatenate
        # Ideally: System -> Standard -> AI
        
        # However, for UX, standard columns (question, options) should be first.
        # System columns like item_id, action should be at start or very end?
        # Let's simple hardcode an order strategy based on available config keys.
        
        standard = QuizConfigService.get('QUIZ_STANDARD_COLUMNS')
        ai = QuizConfigService.get('QUIZ_AI_COLUMNS')
        system = QuizConfigService.get('QUIZ_SYSTEM_COLUMNS')
        
        # Preferred order: item_id, order_in_container ... standard ... ai ... action
        
        columns = []
        
        # Add specific system columns first strictly
        first_cols = ['item_id', 'order_in_container']
        for col in first_cols:
            columns.append(col)
            
        # Add standard
        for col in standard:
            if col not in columns:
                columns.append(col)
                
        # Add AI
        for col in ai:
            if col not in columns:
                columns.append(col)
                
        # Add remaining system columns (like action)
        for col in system:
            if col not in columns:
                columns.append(col)
                
        return columns

    @classmethod
    def analyze_column_structure(cls, filepath: str) -> dict:
        """
        Phân tích cấu trúc cột của sheet 'Data' trong file Excel.
        Trả về dictionary phân loại cột.
        """
        try:
            df = read_excel_with_formulas(filepath, sheet_name='Data')
            columns = set(df.columns)
            
            standard_def = set(QuizConfigService.get('QUIZ_STANDARD_COLUMNS'))
            system_def = set(QuizConfigService.get('QUIZ_SYSTEM_COLUMNS'))
            ai_def = set(QuizConfigService.get('QUIZ_AI_COLUMNS'))
            
            # Additional implicit system columns that might not be in config explicitly 
            # but are handled by logic (e.g., order_in_container is often handled together)
            system_def.add('order_in_container') 
            
            found_standard = [col for col in columns if col in standard_def]
            found_system = [col for col in columns if col in system_def]
            found_ai = [col for col in columns if col in ai_def]
            
            all_known = system_def | standard_def | ai_def
            found_custom = [col for col in columns if col not in all_known]
            
            required_cols = set(QuizConfigService.get('QUIZ_REQUIRED_COLUMNS'))
            missing_required = [col for col in required_cols if col not in columns]
            
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


    @classmethod
    def get_info_keys(cls) -> list[str]:
        return [
            'title', 'description', 'cover_image', 'tags',
            'is_public', 'image_base_folder', 'audio_base_folder', 'ai_prompt',
        ]

    # [REMOVED] resolve_correct_answer_letter
    # Actually, resolve_correct_answer_letter is static logic, keep it.
    # But I need to anchor properly.

    @staticmethod
    def resolve_correct_answer_letter(content: dict) -> str:

        """Return the answer letter (A-D) even if the stored value is option text."""
        if not isinstance(content, dict):
            return ''

        options = content.get('options') or {}
        raw_answer = content.get('correct_answer') or ''
        normalized_answer = str(raw_answer).strip()
        upper_answer = normalized_answer.upper()

        if upper_answer in {'A', 'B', 'C', 'D'}:
            return upper_answer

        for letter in ('A', 'B', 'C', 'D'):
            option_text = options.get(letter)
            if option_text is None:
                continue
            if normalized_answer and normalized_answer == str(option_text).strip():
                return letter

        return ''

    @staticmethod
    def _apply_action_dropdown(worksheet, data_columns):
        try:
            action_index = data_columns.index('action') + 1
        except ValueError:
            return

        action_letter = get_column_letter(action_index)
        validation = DataValidation(
            type='list',
            formula1=f'"{",".join(ACTION_OPTIONS)}"',
            allow_blank=True,
            showDropDown=False,
        )
        validation.errorTitle = 'Hành động không hợp lệ'
        validation.error = 'Vui lòng chọn một hành động hợp lệ hoặc để None nếu không thay đổi.'
        validation.promptTitle = 'Chọn hành động'
        validation.prompt = 'Chọn hành động bạn muốn áp dụng cho dòng này.'
        worksheet.add_data_validation(validation)
        validation.add(f"{action_letter}2:{action_letter}1048576")

    @classmethod
    def create_quiz_excel(cls, info_rows, data_rows, *, output_path: Optional[str] = None, readme_rows: Optional[list[tuple[str, str]]] = None):
        """Generates an Excel file for Quiz import/export."""
        info_df = pd.DataFrame(info_rows, columns=['Key', 'Value'])
        if not info_df.empty:
            info_df['Value'] = info_df['Value'].apply(lambda value: '' if value is None else str(value))
        else:
            info_df = pd.DataFrame(columns=['Key', 'Value'])

        data_cols = cls.get_data_columns()
        data_df = pd.DataFrame(data_rows, columns=data_cols)
        if data_df.empty:
            data_df = pd.DataFrame(columns=data_cols)

        else:
            data_df = data_df.fillna('')

        if 'action' in data_df.columns:
            data_df['action'] = data_df['action'].replace({None: 'None', '': 'None'})
        else:
            data_df['action'] = 'None'

        target = output_path or io.BytesIO()
        with pd.ExcelWriter(target, engine='openpyxl') as writer:
            info_df.to_excel(writer, sheet_name='Info', index=False)
            data_df.to_excel(writer, sheet_name='Data', index=False)
            data_sheet = writer.sheets.get('Data')
            if data_sheet is not None:
                cls._apply_action_dropdown(data_sheet, cls.get_data_columns())

            if readme_rows:
                readme_df = pd.DataFrame(readme_rows, columns=['Hướng dẫn', 'Chi tiết'])
                readme_df.to_excel(writer, sheet_name='ReadMe', index=False)

        if output_path:
            return output_path

        target.seek(0)
        return target

    @staticmethod
    def build_sample_quiz_template():
        """Generates sample data for a blank Quiz template."""
        info_rows = [
            ('title', 'Mẫu bộ Quiz - thay tiêu đề ở đây'),
            ('description', 'Ví dụ ngắn để minh hoạ bộ 3 cột group_id/group_shared_components/group_item_order'),
            ('cover_image', 'Đường dẫn ảnh cover (URL hoặc uploads/...)'),
            ('tags', 'sample,template'),
            ('is_public', 'False'),
            ('image_base_folder', 'quiz/images'),
            ('audio_base_folder', 'quiz/audio'),
            ('ai_prompt', ''),
        ]

        def _row(**kwargs):
            base = {column: '' for column in cls.get_data_columns()}
            base.update(kwargs)
            return base

        data_rows = [
            _row(
                order_in_container=1,
                question='Câu hỏi độc lập (không thuộc group)',
                option_a='Đáp án A',
                option_b='Đáp án B',
                correct_answer_text='A',
                guidance='Giải thích riêng cho câu hỏi này',
                ai_explanation='',
                question_image_file='uploads/quiz/images/question-1.png',
                action='create',
            ),
            _row(
                order_in_container=2,
                question='Bước 1 trong group chung',
                option_a='Lựa chọn 1',
                option_b='Lựa chọn 2',
                correct_answer_text='A',
                guidance='Giải thích chung cho cả group',
                ai_explanation='',
                question_image_file='uploads/quiz/images/shared.png',
                question_audio_file='uploads/quiz/audio/shared.mp3',
                ai_prompt='Gợi ý dùng chung cho cả group',
                group_id=1001,
                group_shared_components='question,pre_question_text,correct_answer,explanation,image,audio,prompt',
                group_item_order=1,
                action='create',
            ),
            _row(
                order_in_container=3,
                question='Bước 2 trong group chung (kế thừa media/prompt)',
                option_a='Lựa chọn 1',
                option_b='Lựa chọn 2',
                correct_answer_text='B',
                ai_explanation='',
                group_id=1001,
                group_shared_components='question,pre_question_text,correct_answer,explanation,image,audio,prompt',
                group_item_order=2,
                action='create',
            ),
        ]

        return info_rows, data_rows

    @staticmethod
    def build_quiz_readme_rows():
        """Generates the ReadMe sheet content."""
        shared_tokens = ', '.join(sorted(GROUP_SHARED_COMPONENT_MAP.keys()))
        return [
            (
                'Mục đích file',
                'Sử dụng sheet Data để thêm/sửa/xoá câu hỏi; sheet Info để cập nhật thông tin bộ Quiz.',
            ),
            (
                'Cấu trúc bắt buộc',
                'Data phải có option_a, option_b, correct_answer_text. Mỗi dòng (trừ Delete/Skip) cần đủ các cột này.',
            ),
            (
                'group_id',
                'Dùng để gom các câu hỏi thành một nhóm. Có thể là số hoặc chuỗi. Khi trùng group_id/external_id sẽ gộp chung.',
            ),
            (
                'group_shared_components',
                f'Theo danh sách hợp lệ: {shared_tokens}. Có thể ghi nhiều giá trị, ngăn cách bằng dấu phẩy.',
            ),
            (
                'Cách hoạt động shared components',
                'Nhập giá trị một lần ở bất kỳ dòng nào của group; các dòng khác có thể để trống cột tương ứng nếu đã đánh dấu chia sẻ.',
            ),
            (
                'group_item_order',
                'Thứ tự trong cùng group (khác với order_in_container). Có thể để trống nếu không cần sắp xếp nội bộ.',
            ),
            (
                'Hành động',
                "Cột action hỗ trợ: None/Update (mặc định), Create, Delete, Skip. Không phân biệt hoa thường.",
            ),
            (
                'Đường dẫn media',
                "Nếu dùng thư mục cơ sở (image_base_folder/audio_base_folder) trong sheet Info, chỉ cần nhập tên file, hệ thống sẽ tự ghép đường dẫn.",
            ),
        ]

    # ... Helper methods for media processing (copied/adapted from routes or flashcard service) ...
    @staticmethod
    def _get_media_folders_from_container(container) -> dict[str, str]:
        if not container:
            return {}
        folders = getattr(container, 'media_folders', {}) or {}
        if folders:
            return dict(folders)
        return {}

    @staticmethod
    def _process_relative_url(url, media_folder: Optional[str] = None):
        if url is None:
            return None
        normalized = str(url).strip()
        if not normalized:
            return ''
        return normalize_media_value_for_storage(normalized, media_folder)
        
    @staticmethod
    def _resolve_local_media_path(path_value: str, *, media_folder: Optional[str] = None):
        if not path_value:
            return None

        normalized = str(path_value).strip()
        if not normalized or normalized.startswith(('http://', 'https://')):
            return None

        normalized = normalized.lstrip('/')
        if normalized.startswith('uploads/'):
            normalized = normalized[len('uploads/'):]

        base_static = os.path.join(current_app.root_path, 'static')
        upload_folder = get_runtime_config('UPLOAD_FOLDER', Config.UPLOAD_FOLDER)
        candidates = []

        relative_candidates = [normalized]
        folder_normalized = normalize_media_folder(media_folder)
        if folder_normalized:
            if '/' not in normalized:
                relative_candidates.insert(0, f"{folder_normalized}/{normalized}")
            else:
                relative_candidates.insert(0, normalized)

        for rel_path in relative_candidates:
            if upload_folder:
                candidates.append(os.path.join(upload_folder, rel_path))
            candidates.append(os.path.join(base_static, rel_path))

        for candidate in candidates:
            if candidate and os.path.isfile(candidate):
                return candidate

        return None
        
    @classmethod
    def _copy_media_into_package(
        cls,
        original_path: str,
        media_dir: Optional[str],
        existing_map: dict,
        media_subdir: Optional[str] = None,
        media_folder: Optional[str] = None,
        export_mode: str = 'zip',
    ) -> str:
        if original_path in (None, ''):
            return original_path

        if export_mode == 'excel':
            return original_path

        normalized = str(original_path).strip()
        if not normalized:
            return ''

        if normalized.startswith(('http://', 'https://')):
            return normalized

        local_path = cls._resolve_local_media_path(normalized, media_folder=media_folder)
        if not local_path and os.path.isabs(normalized) and os.path.isfile(normalized):
            local_path = normalized

        display_value = normalized
        if os.path.isabs(normalized):
            display_value = os.path.basename(normalized)

        if not local_path:
            return display_value

        cache_key = (
            local_path,
            media_folder,
            media_subdir,
            display_value,
        )
        if cache_key in existing_map:
            return display_value

        if not media_dir:
            existing_map[cache_key] = True
            return display_value

        folder_normalized = normalize_media_folder(media_folder)

        sanitized = normalized.replace('\\', '/').lstrip('/')
        segments = [segment for segment in sanitized.split('/') if segment and segment not in {'.', '..'}]

        # Drop uploads prefix if present
        while segments and segments[0].lower() == 'uploads':
            segments.pop(0)

        if folder_normalized:
            folder_segments = [seg for seg in folder_normalized.split('/') if seg]
            if segments[: len(folder_segments)] == folder_segments:
                segments = segments[len(folder_segments) :]

        if os.path.isabs(normalized):
            segments = [os.path.basename(local_path)]

        if not segments:
            segments = [os.path.basename(local_path)]

        base_segments: list[str] = []
        if folder_normalized:
            base_segments.extend(folder_normalized.split('/'))
        elif media_subdir:
            base_segments.append(media_subdir)

        destination_parts = base_segments + segments
        destination_full = os.path.join(media_dir, *destination_parts)
        destination_relative = '/'.join(['uploads'] + destination_parts)

        os.makedirs(os.path.dirname(destination_full), exist_ok=True)
        if not os.path.exists(destination_full):
            shutil.copy2(local_path, destination_full)

        existing_map[cache_key] = destination_relative
        return display_value
    
    @classmethod
    def build_quiz_export_payload(
        cls,
        quiz_set,
        items,
        groups,
        *,
        export_mode: str,
        media_dir: Optional[str],
        media_cache: Optional[dict],
        image_folder: Optional[str],
        audio_folder: Optional[str],
    ):
        media_cache = media_cache or {}

        ai_settings_payload = quiz_set.ai_settings if hasattr(quiz_set, 'ai_settings') else None
        ai_prompt_value = getattr(quiz_set, 'ai_prompt', None)
        if not ai_prompt_value and isinstance(ai_settings_payload, dict):
            ai_prompt_value = ai_settings_payload.get('custom_prompt', '')

        info_mapping = {
            'title': quiz_set.title or '',
            'description': quiz_set.description or '',
            'cover_image': quiz_set.cover_image or '',
            'tags': quiz_set.tags or '',
            'is_public': 'True' if quiz_set.is_public else 'False',
            'image_base_folder': image_folder or '',
            'audio_base_folder': audio_folder or '',
            'ai_prompt': ai_prompt_value or '',
        }

        info_rows = [
            {'Key': key, 'Value': info_mapping.get(key, '')}
            for key in cls.get_info_keys()
        ]

        group_shared_tracker: dict[int, set[str]] = {}
        data_rows = []
        for item in items:
            content = item.content or {}
            group = groups.get(item.group_id) if item.group_id else None
            group_content = group.content if group else {}
            shared_components = set()
            if isinstance(group_content, dict):
                shared_components = set(group_content.get('shared_components') or [])

            row = {column: '' for column in cls.get_data_columns()}

            row['item_id'] = item.item_id
            row['order_in_container'] = item.order_in_container if item.order_in_container is not None else ''
            row['question'] = content.get('question') or ''
            row['pre_question_text'] = content.get('pre_question_text') or ''
            options = content.get('options') or {}
            row['option_a'] = options.get('A') or ''
            row['option_b'] = options.get('B') or ''
            row['option_c'] = options.get('C') or ''
            row['option_d'] = options.get('D') or ''
            row['correct_answer_text'] = content.get('correct_answer') or ''
            row['guidance'] = content.get('explanation') or ''
            row['ai_explanation'] = item.ai_explanation or ''

            def _shared_value(token: str, field_name: str, raw_value):
                if not group or token not in shared_components:
                    return raw_value
                seen = group_shared_tracker.setdefault(group.group_id, set())
                canonical_value = group_content.get(field_name) or raw_value or ''
                if token in seen:
                    return ''
                seen.add(token)
                return canonical_value

            row['question'] = _shared_value('question', 'question', row['question'])
            row['pre_question_text'] = _shared_value('pre_question_text', 'pre_question_text', row['pre_question_text'])
            row['correct_answer_text'] = _shared_value('correct_answer', 'correct_answer', row['correct_answer_text'])
            row['guidance'] = _shared_value('explanation', 'explanation', row['guidance'])
            row['question_image_file'] = _shared_value(
                'image',
                'question_image_file',
                cls._copy_media_into_package(
                    content.get('question_image_file'),
                    media_dir,
                    media_cache,
                    media_subdir='images',
                    media_folder=image_folder,
                    export_mode=export_mode,
                ) or ''
            )
            row['question_audio_file'] = _shared_value(
                'audio',
                'question_audio_file',
                cls._copy_media_into_package(
                    content.get('question_audio_file'),
                    media_dir,
                    media_cache,
                    media_subdir='audio',
                    media_folder=audio_folder,
                    export_mode=export_mode,
                ) or ''
            )
            row['ai_prompt'] = _shared_value('prompt', 'ai_prompt', content.get('ai_prompt') or '')

            row['group_id'] = (group_content.get('external_id') if group_content else None) or (group.group_id if group else '')
            if shared_components:
                row['group_shared_components'] = ','.join(sorted(shared_components))
            row['group_item_order'] = content.get('group_item_order') if content.get('group_item_order') is not None else ''

            # [NEW] Export custom data columns
            custom_data = item.custom_data or {}
            for key, value in custom_data.items():
                row[key] = value

            row['action'] = 'None'
            data_rows.append(row)

        return info_rows, data_rows

    @classmethod
    def process_import(cls, container_id: int, excel_file) -> str:
        """Process Excel file import for updating/creating Quiz items."""
        temp_filepath = None
        try:
            quiz_set = LearningContainer.query.get(container_id)

            with tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx') as tmp_file:
                excel_file.save(tmp_file.name)
                temp_filepath = tmp_file.name

            df = read_excel_with_formulas(temp_filepath, sheet_name='Data')

            required_cols = QuizConfigService.get('QUIZ_REQUIRED_COLUMNS', ['option_a', 'option_b', 'correct_answer_text'])
            if not all(col in df.columns for col in required_cols):
                raise ValueError(
                    f"File Excel (sheet 'Data') phải có các cột bắt buộc: {', '.join(required_cols)}."
                )

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
                quiz_set.set_media_folders(media_overrides)

            media_folders = cls._get_media_folders_from_container(quiz_set)
            image_folder = media_folders.get('image')
            audio_folder = media_folders.get('audio')

            if cover_value is not None:
                quiz_set.cover_image = cls._process_relative_url(str(cover_value), image_folder)

            existing_items = (
                LearningItem.query.filter_by(container_id=container_id, item_type='QUIZ_MCQ')
                .order_by(LearningItem.order_in_container, LearningItem.item_id)
                .all()
            )
            existing_map = {item.item_id: item for item in existing_items}
            existing_groups = {
                group.group_id: group
                for group in LearningGroup.query.filter_by(container_id=container_id).all()
            }
            existing_groups_by_external = {
                (group.content or {}).get('external_id'): group
                for group in existing_groups.values()
                if (group.content or {}).get('external_id') not in (None, '')
            }

            processed_ids = set()
            delete_ids = set()
            ordered_entries = []
            stats = {
                'updated': 0,
                'created': 0,
                'deleted': 0,
                'skipped': 0,
                'reordered': 0,
            }

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
                            if normalized == 'create' and has_item_id:
                                return 'update'
                            if normalized == 'update' and not has_item_id:
                                return 'create'
                            return normalized
                return 'update' if has_item_id else 'create'

            def _get_cell(row_data, column_name):
                if column_name not in df.columns:
                    return None
                value = row_data[column_name]
                if pd.isna(value):
                    return None
                return str(value).strip()

            def _parse_int(value, row_index, field_name):
                if value is None or value == '':
                    return None
                try:
                    return int(float(value))
                except (TypeError, ValueError):
                    raise ValueError(f"Hàng {row_index}: {field_name} '{value}' không hợp lệ.")

            def _parse_excel_group_id(value, row_index, field_name):
                if value is None:
                    return None

                value_str = str(value).strip()
                if value_str in ('', 'nan', 'NaN', 'None'):
                    return None

                return value_str
            


            group_state = {}

            def _normalize_numeric_group_id(raw_value: str):
                try:
                    numeric_value = float(raw_value)
                except (TypeError, ValueError):
                    return None

                if math.isnan(numeric_value):
                    return None
                if numeric_value.is_integer():
                    return int(numeric_value)
                return None

            def _get_or_create_group(group_id_value):
                if group_id_value in (None, ''):
                    return None

                if group_id_value in group_state:
                    return group_state[group_id_value]

                numeric_group_id = _normalize_numeric_group_id(group_id_value)
                existing_group = None
                if numeric_group_id is not None and numeric_group_id in existing_groups:
                    existing_group = existing_groups[numeric_group_id]
                elif group_id_value in existing_groups_by_external:
                    existing_group = existing_groups_by_external[group_id_value]

                if existing_group:
                    content_dict = dict(existing_group.content or {})
                    entry = {
                        'group': existing_group,
                        'shared_components': set(content_dict.get('shared_components') or []),
                        'shared_values': {
                            field: content_dict.get(field)
                            for field in GROUP_SHARED_COMPONENT_MAP.values()
                            if content_dict.get(field) is not None
                        },
                        'external_id': content_dict.get('external_id') or group_id_value
                    }
                    if content_dict.get('external_id') in (None, ''):
                        content_dict['external_id'] = group_id_value
                        existing_group.content = content_dict
                        flag_modified(existing_group, 'content')
                    group_state[group_id_value] = entry
                    return entry

                new_group = LearningGroup(
                    container_id=container_id,
                    group_type='PASSAGE',
                    content={'external_id': group_id_value},
                )
                db.session.add(new_group)
                db.session.flush()
                entry = {
                    'group': new_group,
                    'shared_components': set(),
                    'shared_values': {},
                    'external_id': group_id_value,
                }
                group_state[group_id_value] = entry
                return entry

            for index, row in df.iterrows():
                row_number = index + 2
                item_id_value = _get_cell(row, 'item_id')
                order_value = _get_cell(row, 'order_in_container')
                order_number = _parse_int(order_value, row_number, 'order_in_container') if order_value else None
                if order_number is not None:
                    stats['reordered'] += 1

                question_text = _get_cell(row, 'question') or ''
                option_a = _get_cell(row, 'option_a')
                option_b = _get_cell(row, 'option_b')
                option_c = _get_cell(row, 'option_c')
                option_d = _get_cell(row, 'option_d')
                correct_answer = _get_cell(row, 'correct_answer_text')
                group_item_order = _parse_int(_get_cell(row, 'group_item_order'), row_number, 'group_item_order')
                shared_components = parse_shared_components(_get_cell(row, 'group_shared_components'))
                group_id_value = _parse_excel_group_id(_get_cell(row, 'group_id'), row_number, 'group_id')
                if order_number is None and group_id_value not in (None, ''):
                    order_number = index + 1
                    stats['reordered'] += 1
                group_entry = _get_or_create_group(group_id_value)
                if group_entry and shared_components:
                    group_entry['shared_components'].update(shared_components)

                item_id = None
                if item_id_value:
                    item_id = _parse_int(item_id_value, row_number, 'item_id')

                action_value = _normalize_action(_get_cell(row, 'action'), has_item_id=bool(item_id))

                def _has_value_or_shared(token: str, field_name: str, raw_value):
                    if raw_value not in (None, ''):
                        return True
                    if not group_entry or token not in group_entry['shared_components']:
                        return False
                    return group_entry['shared_values'].get(field_name) not in (None, '')

                has_correct_answer = _has_value_or_shared('correct_answer', 'correct_answer', correct_answer)
                if not (option_a and option_b and has_correct_answer) and action_value not in {'delete', 'skip'}:
                    raise ValueError(f"Hàng {row_number}: Thiếu option A/B hoặc đáp án đúng.")

                if item_id:
                    item = existing_map.get(item_id)
                    if not item:
                        raise ValueError(f"Hàng {row_number}: Không tìm thấy câu hỏi với ID {item_id}.")

                    if action_value == 'delete':
                        delete_ids.add(item_id)
                        stats['deleted'] += 1
                        continue

                    if action_value == 'skip':
                        ordered_entries.append({
                            'type': 'existing',
                            'item': item,
                            'order': order_number if order_number is not None else (item.order_in_container or 0),
                            'sequence': index,
                        })
                        processed_ids.add(item_id)
                        stats['skipped'] += 1
                        continue

                    content_dict = item.content or {}
                    content_dict.setdefault('options', {})
                    content_dict['options']['A'] = option_a
                    content_dict['options']['B'] = option_b
                    content_dict['options']['C'] = option_c
                    content_dict['options']['D'] = option_d

                    def _value_with_group_inner_update(token: str, field_name: str, raw_value):
                        if not group_entry or token not in group_entry['shared_components']:
                            return raw_value
                        cached_value = group_entry['shared_values'].get(field_name)
                        chosen = raw_value if raw_value not in (None, '') else cached_value
                        if chosen not in (None, ''):
                            group_entry['shared_values'][field_name] = chosen
                        return chosen

                    guidance_value = _get_cell(row, 'guidance')
                    pre_question_value = _get_cell(row, 'pre_question_text')
                    image_value = _get_cell(row, 'question_image_file')
                    audio_value = _get_cell(row, 'question_audio_file')
                    ai_prompt_value = _get_cell(row, 'ai_prompt')
                    ai_explanation_value = _get_cell(row, 'ai_explanation')

                    content_dict['question'] = _value_with_group_inner_update('question', 'question', question_text)
                    content_dict['correct_answer'] = _value_with_group_inner_update('correct_answer', 'correct_answer', correct_answer)
                    content_dict['explanation'] = _value_with_group_inner_update('explanation', 'explanation', guidance_value)
                    content_dict['pre_question_text'] = _value_with_group_inner_update('pre_question_text', 'pre_question_text', pre_question_value)
                    image_processed = cls._process_relative_url(image_value, image_folder) if image_value else None
                    audio_processed = cls._process_relative_url(audio_value, audio_folder) if audio_value else None
                    content_dict['question_image_file'] = _value_with_group_inner_update('image', 'question_image_file', image_processed)
                    content_dict['question_audio_file'] = _value_with_group_inner_update('audio', 'question_audio_file', audio_processed)
                    content_dict.pop('ai_explanation', None)

                    prompt_value = _value_with_group_inner_update('prompt', 'ai_prompt', ai_prompt_value)
                    if prompt_value:
                        content_dict['ai_prompt'] = prompt_value
                    else:
                        content_dict.pop('ai_prompt', None)

                    if group_item_order is not None:
                        content_dict['group_item_order'] = group_item_order
                    else:
                        content_dict.pop('group_item_order', None)

                    item.group_id = group_entry['group'].group_id if group_entry else None
                    item.ai_explanation = ai_explanation_value or None

                    item.content = content_dict
                    flag_modified(item, 'content')

                    # Process custom columns
                    known_quiz_columns_set = {
                        'item_id', 'order_in_container', 'action', 'group_id', 'group_item_order', 'group_shared_components',
                        'question', 'pre_question_text', 'correct_answer_text', 'guidance',
                        'option_a', 'option_b', 'option_c', 'option_d',
                        'question_image_file', 'question_audio_file',
                        'ai_prompt', 'ai_explanation'
                    }
                    custom_cols = [c for c in df.columns if c not in known_quiz_columns_set]
                    custom_dict = item.custom_data or {}
                    for col in custom_cols:
                        val = _get_cell(row, col)
                        if val:
                            custom_dict[col] = val
                        elif col in custom_dict:
                            custom_dict.pop(col)
                    
                    item.custom_data = custom_dict if custom_dict else None
                    flag_modified(item, 'custom_data')

                    ordered_entries.append({
                        'type': 'existing',
                        'item': item,
                        'order': order_number if order_number is not None else (item.order_in_container or 0),
                        'sequence': index,
                    })
                    processed_ids.add(item_id)
                    stats['updated'] += 1
                    if action_value == 'skip':
                        stats['skipped'] += 1
                        continue

                    # For New items (non-update path) logic follows...
                else: 
                     # This is a NEW item (no ID)
                    if action_value in ('delete', 'skip'):
                        stats['skipped'] += 1
                        continue
                    if not (option_a and option_b): # New items MUST have options even if correct answer is missing? (Checked above broadly)
                        stats['skipped'] += 1
                        continue

                    def _value_with_group_inner_new(token: str, field_name: str, raw_value):
                        if not group_entry or token not in group_entry['shared_components']:
                            return raw_value
                        cached_value = group_entry['shared_values'].get(field_name)
                        chosen = raw_value if raw_value not in (None, '') else cached_value
                        if chosen not in (None, ''):
                            group_entry['shared_values'][field_name] = chosen
                        return chosen

                    image_value = _get_cell(row, 'question_image_file')
                    audio_value = _get_cell(row, 'question_audio_file')
                    ai_prompt_value = _get_cell(row, 'ai_prompt')
                    ai_explanation_value = _get_cell(row, 'ai_explanation')
                    guidance_value = _get_cell(row, 'guidance')
                    pre_question_value = _get_cell(row, 'pre_question_text')

                    known_quiz_columns_set = {
                        'item_id', 'order_in_container', 'action', 'group_id', 'group_item_order', 'group_shared_components',
                        'question', 'pre_question_text', 'correct_answer_text', 'guidance',
                        'option_a', 'option_b', 'option_c', 'option_d',
                        'question_image_file', 'question_audio_file',
                        'ai_prompt', 'ai_explanation'
                    }
                    
                    custom_cols = [c for c in df.columns if c not in known_quiz_columns_set]
                    custom_dict = {}
                    for col in custom_cols:
                        val = _get_cell(row, col)
                        if val:
                            custom_dict[col] = val

                    new_item = LearningItem(
                        container_id=container_id,
                        item_type='QUIZ_MCQ',
                        content={
                            'question': _value_with_group_inner_new('question', 'question', question_text),
                            'options': {
                                'A': option_a,
                                'B': option_b,
                                'C': option_c,
                                'D': option_d,
                            },
                            'correct_answer': _value_with_group_inner_new('correct_answer', 'correct_answer', correct_answer),
                            'explanation': _value_with_group_inner_new('explanation', 'explanation', guidance_value),
                            'pre_question_text': _value_with_group_inner_new('pre_question_text', 'pre_question_text', pre_question_value),
                            'question_image_file': _value_with_group_inner_new('image', 'question_image_file', cls._process_relative_url(image_value, image_folder) if image_value else None),
                            'question_audio_file': _value_with_group_inner_new('audio', 'question_audio_file', cls._process_relative_url(audio_value, audio_folder) if audio_value else None),
                            'ai_prompt': _value_with_group_inner_new('prompt', 'ai_prompt', ai_prompt_value) if _value_with_group_inner_new('prompt', 'ai_prompt', ai_prompt_value) else None,
                            'group_item_order': group_item_order if group_item_order is not None else None,
                        },
                        custom_data=custom_dict if custom_dict else None,
                        ai_explanation=ai_explanation_value or None,
                        group_id=group_entry['group'].group_id if group_entry else None,
                        order_in_container=order_number,
                    )
                    
                    ordered_entries.append({
                        'type': 'new',
                        'item': new_item, 
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
                    'type': 'existing',
                    'item': item,
                    'order': item.order_in_container or 0,
                    'sequence': offset,
                })

            for delete_id in delete_ids:
                if delete_id in existing_map:
                    db.session.delete(existing_map[delete_id])

            ordered_entries.sort(
                key=lambda entry: (
                    entry['order'] if entry['order'] is not None else float('inf'),
                    entry['sequence'],
                )
            )

            next_order = 1
            for entry in ordered_entries:
                item = entry.get('item')
                if item:
                    item.order_in_container = next_order
                    if entry['type'] == 'new':
                        db.session.add(item)
                else:
                    current_app.logger.warning("Found entry without item object in ordered_entries")
                
                next_order += 1

            for group_entry in group_state.values():
                group_obj = group_entry['group']
                content_dict = dict(group_obj.content or {})
                if group_entry.get('external_id'):
                    content_dict['external_id'] = group_entry['external_id']
                content_dict['shared_components'] = sorted(group_entry['shared_components'])
                for token, field_name in GROUP_SHARED_COMPONENT_MAP.items():
                    if token in group_entry['shared_components']:
                        value = group_entry['shared_values'].get(field_name)
                        if value not in (None, ''):
                            content_dict[field_name] = value
                group_obj.content = content_dict
                flag_modified(group_obj, 'content')

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
            return f'Bộ câu hỏi quiz đã được xử lý: {summary_text}.'
        finally:
            if temp_filepath and os.path.exists(temp_filepath):
                os.remove(temp_filepath)
