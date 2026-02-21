"""Utility helpers for working with media folders and stored paths."""

from __future__ import annotations

import os
from typing import Mapping, Optional

MEDIA_TYPES = ("image", "audio")


def normalize_media_folder(folder: Optional[str]) -> Optional[str]:
    """Return a sanitized folder path (relative to the uploads root)."""

    if not folder:
        return None

    normalized = str(folder).strip().replace("\\", "/")
    normalized = normalized.strip("/")

    # Remove legacy prefixes
    for prefix in ["uploads/", "static/"]:
        if normalized.startswith(prefix):
            normalized = normalized[len(prefix):]

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
    Normalize a path before storing it in the database.
    Returns the path relative to uploads/ directory.
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

    # Strip legacy prefixes
    for prefix in ["uploads/", "static/"]:
        while normalized.startswith(prefix):
            normalized = normalized[len(prefix):]

    # Prepend media_folder if it's just a filename
    if "/" not in normalized:
        folder_normalized = normalize_media_folder(media_folder)
        if folder_normalized:
            normalized = f"{folder_normalized}/{normalized}"
    
    return normalized


def build_relative_media_path(value, media_folder: Optional[str]) -> Optional[str]:
    """
    Build a relative path (from the uploads root) for the stored value.
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

    # Strip legacy prefixes
    for prefix in ["uploads/", "static/"]:
        while normalized.startswith(prefix):
            normalized = normalized[len(prefix):]

    # Prepend media_folder if it's just a filename
    if "/" not in normalized:
        folder_normalized = normalize_media_folder(media_folder)
        if folder_normalized:
            normalized = f"{folder_normalized}/{normalized}"
    
    if not normalized:
        return None

    return normalized


def resolve_media_in_content(content: dict, audio_folder: Optional[str] = None, image_folder: Optional[str] = None) -> dict:
    """
    In-place resolve relative media paths in a content dictionary.
    
    Args:
        content: The content dictionary to modify.
        audio_folder: The base folder for audio files.
        image_folder: The base folder for image files.
        
    Returns:
        dict: The modified content dictionary.
    """
    if not isinstance(content, dict):
        return content

    # 1. Resolve Audio Fields
    audio_fields = ['front_audio_url', 'back_audio_url', 'audio_url', 'question_audio_file', 'memrise_audio_url']
    for field in audio_fields:
        val = content.get(field)
        if val and isinstance(val, str) and not val.startswith(('http://', 'https://', '/')):
            rel_path = build_relative_media_path(val, audio_folder)
            if rel_path:
                content[field] = f"/media/{rel_path}"

    # 2. Resolve Image Fields
    image_fields = ['front_img', 'back_img', 'image_url', 'question_image_file', 'cover_image']
    for field in image_fields:
        val = content.get(field)
        if val and isinstance(val, str) and not val.startswith(('http://', 'https://', '/')):
            rel_path = build_relative_media_path(val, image_folder)
            if rel_path:
                content[field] = f"/media/{rel_path}"

    return content
