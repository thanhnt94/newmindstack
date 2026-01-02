"""Helper utilities for working with Excel files in content management flows."""
from __future__ import annotations

from typing import List, Tuple

import pandas as pd


def extract_info_sheet_mapping(file_path: str) -> Tuple[dict[str, str], List[str]]:
    """Return mapping data from the ``Info`` sheet and any warnings encountered.

    The function tries to be forgiving with partially filled sheets. It accepts
    missing values, trims whitespace around keys/values and records any
    recoverable issues as human readable warnings so that callers can present
    actionable feedback to end users.
    """
    warnings: List[str] = []
    try:
        df_info = pd.read_excel(file_path, sheet_name="Info")
    except ValueError:
        warnings.append(
            "Không tìm thấy sheet 'Info'. Hãy giữ nguyên sheet này khi tải file từ hệ thống."
        )
        return {}, warnings
    except Exception as exc:  # pragma: no cover - defensive branch
        warnings.append(f"Không thể đọc sheet 'Info': {exc}")
        return {}, warnings

    if df_info.empty:
        warnings.append("Sheet 'Info' đang trống. Điền dữ liệu vào hai cột 'Key' và 'Value'.")
        return {}, warnings

    normalized_columns = {
        str(column).strip().lower(): column
        for column in df_info.columns
        if isinstance(column, str)
    }
    key_column_name = normalized_columns.get("key")
    value_column_name = normalized_columns.get("value")

    if not key_column_name:
        warnings.append("Sheet 'Info' thiếu cột 'Key'. Đảm bảo cột đầu tiên có tiêu đề 'Key'.")
        return {}, warnings

    if not value_column_name:
        remaining_columns = [column for column in df_info.columns if column != key_column_name]
        if remaining_columns:
            value_column_name = remaining_columns[0]
            warnings.append(
                "Sheet 'Info' thiếu cột 'Value'. Đang dùng tạm cột "
                f"'{value_column_name}' và cần đổi tên thành 'Value' để tránh lỗi."
            )
        else:
            warnings.append("Sheet 'Info' thiếu cột 'Value'. Hãy thêm cột thứ hai với tiêu đề 'Value'.")
            return {}, warnings

    info_mapping: dict[str, str] = {}
    for _, row in df_info.iterrows():
        raw_key = row.get(key_column_name)
        if pd.isna(raw_key):
            continue
        key = str(raw_key).strip()
        if not key:
            continue

        raw_value = row.get(value_column_name)
        if pd.isna(raw_value):
            info_mapping[key] = ""
        else:
            info_mapping[key] = str(raw_value).strip()

    if not info_mapping:
        warnings.append(
            "Sheet 'Info' không có dòng hợp lệ. Kiểm tra lại cột 'Key' và 'Value'."
        )

    return info_mapping, warnings


def format_info_warnings(warnings: List[str]) -> str:
    """Turn a list of warning strings into a short, human friendly sentence."""
    if not warnings:
        return ""
    if len(warnings) == 1:
        return warnings[0]
    return " ".join(f"{index + 1}. {message}" for index, message in enumerate(warnings))
