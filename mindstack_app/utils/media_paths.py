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
    """
    Normalize a user-provided path before storing it in the database.
    Changed: Always returns the full path relative to uploads/ directory.
    Does NOT strip the media_folder prefix anymore to ensure path integrity.
    Does NOT use basename, preserving subdirectories.
    """

    if value is None:
        return None

    normalized = str(value).strip()

    if normalized == "":
        return ""

    if normalized.startswith(("http://", "https://")):
        return normalized

    normalized = normalized.replace("\\", "/")
    normalized = normalized.lstrip("/")

    # Strip 'uploads/' prefix if present
    uploads_prefix = "uploads/"
    while normalized.startswith(uploads_prefix):
        normalized = normalized[len(uploads_prefix):]

    # [CHANGE] If the value has no slashes, it's likely a legacy filename
    # or a shortcut (user just typed 'cover.jpg').
    # Prepend the media_folder to make it a full relative path.
    if "/" not in normalized:
        folder_normalized = normalize_media_folder(media_folder)
        if folder_normalized:
            normalized = f"{folder_normalized}/{normalized}"
    
    return normalized


def build_relative_media_path(value, media_folder: Optional[str]) -> Optional[str]:
    """
    Build a relative path (from the static/uploads root) for the stored value.
    Handles legacy data (filename only) by prepending media_folder.
    Handles new data (full path) by returning as-is.
    """

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

    # Heuristic: If the value has no slashes, it's likely a legacy filename
    # that implies it resides in the default media_folder.
    if "/" not in normalized:
        folder_normalized = normalize_media_folder(media_folder)
        if folder_normalized:
            # Prepend default folder
            normalized = f"{folder_normalized}/{normalized}"
    
    # If it has slashes, we assume it's already a full relative path (e.g. 'folder/img.jpg')
    # and return it as is.

    if not normalized:
        return None

    return normalized

