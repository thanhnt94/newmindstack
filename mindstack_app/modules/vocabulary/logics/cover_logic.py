# File: mindstack_app/modules/vocabulary/logics/cover_logic.py

def get_cover_url(path):
    """
    Stateless logic to convert database path to accessible URL.
    Does NOT import DB or Flask.
    """
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
