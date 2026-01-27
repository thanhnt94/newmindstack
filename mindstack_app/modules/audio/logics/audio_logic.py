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
    
    # Physical Path
    physical_dir = app_root / rel_dir
    physical_path = physical_dir / filename
    
    # URL Calculation
    # We assume 'static' is at the start of relative path for URLs to work by default via Flask static serving
    # URL should be root-relative, e.g. /static/audio/cache/hash.mp3
    
    # Ensure URL always uses forward slashes
    url_path = f"/{rel_dir.as_posix()}/{filename}"
    
    return {
        'physical_path': str(physical_path.resolve() if physical_path.exists() else physical_path), # resolve only if exists validation needed? No, just str.
        'url': url_path
    }
