"""Utility helpers for working with media folders and stored paths."""

from __future__ import annotations

import os
from typing import Mapping, Optional

MEDIA_TYPES = ("image", "audio")


def normalize_media_folder(folder: Optional[str]) -> Optional[str]:
    """Return a sanitized folder path (relative to the uploads static root)."""

    if not folder:
        return None

    normalized = str(folder).strip().replace("\\", "/")
    normalized = normalized.strip("/")

    uploads_prefix = "uploads/"
    while normalized.startswith(uploads_prefix):
        normalized = normalized[len(uploads_prefix):]

    return normalized or None


def get_media_folders(settings: Optional[Mapping[str, object]]) -> dict[str, str]:
    """Extract configured media folders from a settings mapping."""

    result: dict[str, str] = {}

    if not isinstance(settings, Mapping):
        return result

    media_settings = settings.get("media_folders")

    if isinstance(media_settings, Mapping):
        for media_type in MEDIA_TYPES:
            folder_value = media_settings.get(media_type)
            normalized = normalize_media_folder(folder_value)
            if normalized:
                result[media_type] = normalized
    else:
        for media_type in MEDIA_TYPES:
            fallback_key = f"{media_type}_base_folder"
            folder_value = settings.get(fallback_key)
            normalized = normalize_media_folder(folder_value)
            if normalized:
                result[media_type] = normalized

    return result


def normalize_media_value_for_storage(value, media_folder: Optional[str]) -> Optional[str]:
    """Normalize a user-provided path before storing it in the database."""

    if value is None:
        return None

    normalized = str(value).strip()

    if normalized == "":
        return ""

    if normalized.startswith(("http://", "https://")):
        return normalized

    normalized = normalized.replace("\\", "/")
    normalized = normalized.lstrip("/")

    uploads_prefix = "uploads/"
    while normalized.startswith(uploads_prefix):
        normalized = normalized[len(uploads_prefix):]

    folder_normalized = normalize_media_folder(media_folder)
    if folder_normalized:
        folder_prefix = f"{folder_normalized}/"
        if normalized.startswith(folder_prefix):
            normalized = normalized[len(folder_prefix):]
        normalized = os.path.basename(normalized)

    return normalized


def build_relative_media_path(value, media_folder: Optional[str]) -> Optional[str]:
    """Build a relative path (from the static/uploads root) for the stored value."""

    if value is None:
        return None

    normalized = str(value).strip()

    if not normalized:
        return None

    normalized = normalized.replace("\\", "/")

    if normalized.startswith(("http://", "https://")):
        return normalized

    normalized = normalized.lstrip("/")

    uploads_prefix = "uploads/"
    while normalized.startswith(uploads_prefix):
        normalized = normalized[len(uploads_prefix):]

    folder_normalized = normalize_media_folder(media_folder)
    if folder_normalized:
        folder_prefix = f"{folder_normalized}/"
        if normalized.startswith(folder_prefix):
            normalized = normalized[len(folder_prefix):]
        normalized = normalized.lstrip("/")
        normalized = f"{folder_prefix}{normalized}" if normalized else folder_normalized

    if not normalized:
        return None

    return normalized

