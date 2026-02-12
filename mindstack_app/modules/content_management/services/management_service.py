"""Management Service for orchestrating content operations."""
from __future__ import annotations
import os
import tempfile
from typing import Any, Dict, List, Optional
import pandas as pd
from flask import current_app
from .kernel_service import ContentKernelService
from mindstack_app.core.signals import content_changed
from mindstack_app.utils.excel import (
    read_excel_with_formulas, 
    extract_info_sheet_mapping,
    normalize_action,
    get_cell_value
)
from ..logics.validators import has_container_access

class ManagementService:
    """Orchestrates content creation, updates, and imports."""

    @staticmethod
    def build_content_dict(row_data: Any, columns: List[str], 
                           standard_fields: set[str], 
                           url_fields: set[str] = None,
                           image_folder: str = None,
                           audio_folder: str = None) -> Dict[str, Any]:
        """
        Generic builder for item content JSON.
        Supports both direct column names and 'content:' prefixed columns.
        """
        from mindstack_app.utils.excel import get_cell_value
        from mindstack_app.utils.media_paths import normalize_media_value_for_storage
        
        content = {}
        url_fields = url_fields or set()
        
        # 1. Handle Prefixed Columns (content:field_name) - High Priority
        for col in columns:
            if col.startswith('content:'):
                field_name = col.replace('content:', '')
                value = get_cell_value(row_data, col, columns)
                if value is not None:
                    if field_name in url_fields:
                        folder = image_folder if 'img' in field_name or 'cover' in field_name else audio_folder
                        value = normalize_media_value_for_storage(value, folder)
                    content[field_name] = value

        # 2. Handle Standard Fields (fallback for non-prefixed columns)
        for field in standard_fields:
            if field not in content:
                value = get_cell_value(row_data, field, columns)
                if value is not None:
                    if field in url_fields:
                        folder = image_folder if 'img' in field or 'cover' in field else audio_folder
                        value = normalize_media_value_for_storage(value, folder)
                    content[field] = value
                    
        return content

    @staticmethod
    def build_custom_data(row_data: Any, columns: List[str], 
                          known_fields: set[str]) -> Optional[Dict[str, Any]]:
        """
        Generic builder for custom_data JSON.
        Supports 'custom:' prefixed columns and unknown columns.
        """
        from mindstack_app.utils.excel import get_cell_value
        
        custom_data = {}
        
        # 1. Handle Prefixed Columns (custom:field_name)
        for col in columns:
            if col.startswith('custom:'):
                field_name = col.replace('custom:', '')
                value = get_cell_value(row_data, col, columns)
                if value is not None:
                    custom_data[field_name] = value

        # 2. Handle Unknown Columns (legacy/fallback)
        for col in columns:
            clean_col = col.replace('content:', '').replace('custom:', '')
            if (col not in known_fields and 
                clean_col not in known_fields and 
                not col.startswith(('content:', 'custom:')) and
                col not in {'item_id', 'action', 'order_in_container', 'item_type', 'group_id'}):
                
                value = get_cell_value(row_data, col, columns)
                if value is not None:
                    custom_data[col] = value
                    
        return custom_data if custom_data else None

    @staticmethod
    def notify_content_change(item_id: int, action: str, container_id: int):
        """Emit a signal that content has changed."""
        content_changed.send(
            'cms',
            content_type='item',
            content_id=item_id,
            action=action, # legacy/extra
            container_id=container_id, # useful context
            payload={'regenerate_audio': True, 'ai_process': True}
        )

    @classmethod
    def process_form_item(cls, container_id: int, item_type: str, 
                          content: Dict, item_id: Optional[int] = None) -> Any:
        """Create or update a single item from a form."""
        if not has_container_access(container_id, 'editor'):
            raise PermissionError("User does not have editor access to this container.")

        if item_id:
            item = ContentKernelService.update_item(item_id, content=content)
            cls.notify_content_change(item_id, 'updated', container_id)
        else:
            item = ContentKernelService.create_item(container_id, item_type, content)
            cls.notify_content_change(item.item_id, 'created', container_id)
            
        return item

    @classmethod
    def process_excel_import(cls, container_id: int, item_type: str, 
                             excel_file, column_mapper: callable) -> Dict[str, int]:
        """
        Generic Excel import logic.
        column_mapper: function(row_data, columns) -> (content_dict, custom_data_dict)
        """
        if not has_container_access(container_id, 'editor'):
            raise PermissionError("User does not have editor access to this container.")

        temp_filepath = None
        stats = {'created': 0, 'updated': 0, 'deleted': 0, 'skipped': 0}

        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx') as tmp:
                excel_file.save(tmp.name)
                temp_filepath = tmp.name

            df = read_excel_with_formulas(temp_filepath, sheet_name='Data')
            columns = list(df.columns)
            
            # 1. Process Info sheet if exists
            info_mapping, _ = extract_info_sheet_mapping(temp_filepath)
            if info_mapping:
                update_payload = {}
                settings_payload = {}
                
                standard_container_fields = {
                    'title', 'description', 'tags', 'is_public', 
                    'ai_prompt', 'media_image_folder', 'media_audio_folder', 'cover_image'
                }
                
                for k, v in info_mapping.items():
                    if k in standard_container_fields:
                        if k == 'is_public':
                            update_payload[k] = str(v).upper() == 'TRUE'
                        else:
                            update_payload[k] = v
                    elif k.startswith('setting:'):
                        setting_key = k.replace('setting:', '')
                        # Try to parse JSON for complex types
                        try:
                            settings_payload[setting_key] = json.loads(v)
                        except:
                            settings_payload[setting_key] = v
                
                if settings_payload:
                    update_payload['settings'] = settings_payload
                
                if update_payload:
                    ContentKernelService.update_container(container_id, **update_payload)

            # 2. Process Data rows
            for index, row in df.iterrows():
                raw_item_id = get_cell_value(row, 'item_id', columns)
                item_id = int(float(raw_item_id)) if raw_item_id else None
                
                action = normalize_action(get_cell_value(row, 'action', columns), bool(item_id))
                
                if action == 'skip':
                    stats['skipped'] += 1
                    continue
                
                if action == 'delete' and item_id:
                    ContentKernelService.delete_item(item_id)
                    cls.notify_content_change(item_id, 'deleted', container_id)
                    stats['deleted'] += 1
                    continue

                # Map columns to content structure
                content, custom_data = column_mapper(row, columns)
                
                if not content:
                    stats['skipped'] += 1
                    continue

                if item_id:
                    ContentKernelService.update_item(item_id, content=content, custom_data=custom_data)
                    cls.notify_content_change(item_id, 'updated', container_id)
                    stats['updated'] += 1
                else:
                    item = ContentKernelService.create_item(container_id, item_type, content, custom_data=custom_data)
                    cls.notify_content_change(item.item_id, 'created', container_id)
                    stats['created'] += 1

            return stats

        finally:
            if temp_filepath and os.path.exists(temp_filepath):
                try:
                    os.remove(temp_filepath)
                except:
                    pass

    @staticmethod
    def get_container_content_keys(container_id: int, limit: int = 20) -> List[str]:
        """
        Scans a sample of items in the container to find all available content keys.
        Returns a sorted list of unique keys.
        """
        from mindstack_app.models import LearningItem
        
        # Query a sample of items
        items = LearningItem.query.filter_by(container_id=container_id).limit(limit).all()
        
        keys = set()
        # Always include defaults
        keys.add('front')
        keys.add('back')
        
        for item in items:
            if item.content and isinstance(item.content, dict):
                keys.update(item.content.keys())
        
        # Filter out keys starting with underscores or system keys if needed
        return sorted([k for k in keys if not k.startswith('_')])


