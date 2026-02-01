# File: mindstack_app/modules/vocabulary/utils.py

def get_cover_url(path):
    """Helper to convert database path to accessible URL."""
    if not path:
        return None
    path = path.replace('\\', '/')
    if path.startswith('http') or path.startswith('/'):
        return path
    
    # Standardize: remove common legacy prefixes if they exist
    p = path
    if p.startswith('static/'): p = p[7:]
    if p.startswith('uploads/'): p = p[8:]
    
    return '/media/' + p.lstrip('/')

