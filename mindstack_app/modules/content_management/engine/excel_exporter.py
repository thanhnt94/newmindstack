"""Engine for exporting LearningContainer data to various formats."""
from __future__ import annotations
import io
import json
import pandas as pd
from collections import OrderedDict
from sqlalchemy import inspect
from datetime import datetime
from mindstack_app.models import LearningContainer, LearningItem, LearningGroup

class ExcelExporter:
    """Stateful or Stateless engine to generate complex Excel files."""

    @staticmethod
    def export_container(container: LearningContainer) -> tuple[io.BytesIO, str]:
        """
        Generates a comprehensive Excel file from a container.
        Returns: (BytesIO_buffer, suggested_filename)
        """
        # 1. Prepare Info Sheet Data (Absolute)
        info_dict = OrderedDict()
        inst = inspect(LearningContainer)
        for col in inst.columns:
            val = getattr(container, col.key)
            if col.name in {'ai_capabilities', 'settings'}:
                continue
            info_dict[col.key] = val.isoformat() if isinstance(val, datetime) else val

        # Flatten AI Capabilities
        if container.ai_capabilities:
            caps = container.ai_capabilities
            if isinstance(caps, list):
                for cap in caps: info_dict[f'capability:{cap}'] = 'TRUE'
            elif isinstance(caps, dict):
                for k, v in caps.items(): info_dict[f'capability:{k}'] = 'TRUE' if v else 'FALSE'

        # Flatten Settings
        if container.settings and isinstance(container.settings, dict):
            for k, v in container.settings.items():
                key = f'setting:{k}'
                info_dict[key] = v if not isinstance(v, (dict, list)) else json.dumps(v, ensure_ascii=False)

        info_rows = [['Key', 'Value']]
        for k, v in info_dict.items():
            info_rows.append([k, v])
        df_info = pd.DataFrame(info_rows[1:], columns=info_rows[0])

        # 2. Prepare Data Sheet Data
        items = LearningItem.query.filter_by(container_id=container.container_id).order_by(
            LearningItem.order_in_container, LearningItem.item_id
        ).all()
        
        data_rows = []
        for item in items:
            row = OrderedDict([
                ('item_id', item.item_id),
                ('action', 'keep'),
                ('item_type', item.item_type),
                ('group_id', item.group_id or ''),
                ('order_in_container', item.order_in_container),
            ])
            if item.content:
                for k, v in item.content.items():
                    row[f'content:{k}'] = v if not isinstance(v, (dict, list)) else json.dumps(v, ensure_ascii=False)
            row['ai_explanation'] = item.ai_explanation or ''
            if item.custom_data:
                for k, v in item.custom_data.items():
                    row[f'custom:{k}'] = v if not isinstance(v, (dict, list)) else json.dumps(v, ensure_ascii=False)
            data_rows.append(row)
        df_data = pd.DataFrame(data_rows)

        # 3. Prepare Groups Sheet
        group_rows = []
        groups = LearningGroup.query.filter_by(container_id=container.container_id).all()
        for g in groups:
            grow = OrderedDict([('group_id', g.group_id), ('group_type', g.group_type)])
            if g.content:
                for k, v in g.content.items():
                    grow[f'content:{k}'] = v if not isinstance(v, (dict, list)) else json.dumps(v, ensure_ascii=False)
            group_rows.append(grow)
        df_groups = pd.DataFrame(group_rows) if group_rows else None

        # 4. Write to Excel
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df_info.to_excel(writer, sheet_name='Info', index=False)
            df_data.to_excel(writer, sheet_name='Data', index=False)
            if df_groups is not None:
                df_groups.to_excel(writer, sheet_name='Groups', index=False)
        
        output.seek(0)
        
        safe_title = "".join([c if c.isalnum() else "_" for c in container.title])
        filename = f"MindStack_EXPORT_{container.container_type}_{safe_title}_{container.container_id}.xlsx"
        
        return output, filename
