import hashlib
import os
from pathlib import Path
from flask import current_app

def generate_hash_name(text: str, engine: str, voice: str) -> str:
    """
    Generate a deterministic MD5 hash filename for the audio request.
    Format: md5(text|engine|voice).mp3
    """
    # Normalize inputs
    text_norm = text.strip()
    voice_norm = voice if voice else "default"
    
    raw_key = f"{text_norm}|{engine}|{voice_norm}"
    hash_obj = hashlib.md5(raw_key.encode('utf-8'))
    return f"{hash_obj.hexdigest()}.mp3"

def get_storage_path(target_dir: str, filename: str) -> dict:
    """
    Resolve physical path and relative URL for the audio file.
    
    Args:
        target_dir: Relative path from app root (e.g. 'static/audio/cache')
        filename: Name of the file (e.g. 'hash.mp3')
        
    Returns:
        dict: {'physical_path': Path, 'url': str}
    """
    # Assume target_dir is relative to mindstack_app root package
    # current_app.root_path points to mindstack_app/
    
    app_root = Path(current_app.root_path)
    
    # Handle both forward and backslashes by using Path
    rel_dir = Path(target_dir) 
    
    # Physical Path Resolution
    # Check if we are targeting the uploads directory
    parts = rel_dir.parts
    if parts and parts[0] == 'uploads':
        # Route to UPLOAD_FOLDER configured in app
        # Remove 'uploads' from the start to get relative path inside UPLOAD_FOLDER
        upload_root = Path(current_app.config['UPLOAD_FOLDER'])
        if len(parts) > 1:
            physical_dir = upload_root / Path(*parts[1:])
        else:
            physical_dir = upload_root
    else:
        # Default behavior: relative to mindstack_app package
        physical_dir = app_root / rel_dir
        
    physical_path = physical_dir / filename
    
    # URL Calculation
    # Fix: If targeting uploads, use /media/ prefix for serving
    if parts and parts[0] == 'uploads':
        # Replace 'uploads' with 'media' for the URL
        url_path = f"/media/{Path(*parts[1:]).as_posix()}/{filename}"
    else:
        # Default behavior: root-relative
        url_path = f"/{rel_dir.as_posix()}/{filename}"
    
    return {
        'physical_path': str(physical_path.resolve() if physical_path.exists() else physical_path), # resolve only if exists validation needed? No, just str.
        'url': url_path
    }
