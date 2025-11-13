"""Tests for helper utilities that parse Excel info sheets."""
from __future__ import annotations

import pandas as pd

from mindstack_app.modules.shared.utils.excel import (
    extract_info_sheet_mapping,
    format_info_warnings,
)


def test_extract_info_sheet_mapping_returns_partial_data(tmp_path):
    file_path = tmp_path / "info.xlsx"
    info_df = pd.DataFrame(
        {
            "Key": ["title", "description", "ai_prompt"],
            "Value": ["Sample Title", None, "  "],
        }
    )
    with pd.ExcelWriter(file_path, engine="openpyxl") as writer:
        info_df.to_excel(writer, sheet_name="Info", index=False)

    mapping, warnings = extract_info_sheet_mapping(str(file_path))

    assert mapping["title"] == "Sample Title"
    assert mapping["description"] == ""
    assert mapping["ai_prompt"] == ""
    assert warnings == []


def test_extract_info_sheet_mapping_missing_sheet(tmp_path):
    file_path = tmp_path / "no_info.xlsx"
    with pd.ExcelWriter(file_path, engine="openpyxl") as writer:
        pd.DataFrame({"dummy": [1]}).to_excel(writer, sheet_name="Data", index=False)

    mapping, warnings = extract_info_sheet_mapping(str(file_path))

    assert mapping == {}
    assert warnings
    assert "Không tìm thấy sheet 'Info'" in warnings[0]


def test_extract_info_sheet_mapping_missing_value_column(tmp_path):
    file_path = tmp_path / "missing_value.xlsx"
    info_df = pd.DataFrame(
        {
            "Key": ["title", "tags"],
            "Another": ["My Title", "tag1, tag2"],
        }
    )
    with pd.ExcelWriter(file_path, engine="openpyxl") as writer:
        info_df.to_excel(writer, sheet_name="Info", index=False)

    mapping, warnings = extract_info_sheet_mapping(str(file_path))

    assert mapping == {"title": "My Title", "tags": "tag1, tag2"}
    assert warnings
    assert "thiếu cột 'Value'" in warnings[0]


def test_format_info_warnings_human_readable():
    assert format_info_warnings([]) == ""
    assert format_info_warnings(["Một cảnh báo"]) == "Một cảnh báo"
    formatted = format_info_warnings(["Cảnh báo A", "Cảnh báo B"])
    assert formatted.startswith("1. Cảnh báo A")
    assert "2. Cảnh báo B" in formatted
