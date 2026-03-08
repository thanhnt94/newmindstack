"""
Kanji decomposition and reading data loader.
Loads:
- KanjiVG element data (kanji_elements.json)
- Japanese readings (kanji_readings.json)
- Hán-Việt readings (kanji_hanviet.json)
- Vietnamese meanings and Hán-Việt (kanji_vietnamese.json)
"""
import os
import json

# Manual visual similarity groups
MANUAL_SIMILAR_GROUPS = [
    ["持", "待", "特"],
    ["問", "間", "聞"],
    ["右", "石", "若"],
    ["左", "在"],
    ["人", "入", "八"],
    ["大", "太", "犬"],
    ["日", "白", "目", "自"],
    ["口", "品"],
    ["土", "士"],
    ["未", "末"],
    ["買", "売"],
    ["鳥", "島"],
    ["書", "画"],
    ["使", "便"],
]

_KANJI_DB_CACHE = None

def _load_json(filename):
    path = os.path.join(os.path.dirname(__file__), filename)
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return {}

def _get_kanji_db():
    global _KANJI_DB_CACHE
    if _KANJI_DB_CACHE is None:
        _KANJI_DB_CACHE = _load_json('kanji_db.json')
    return _KANJI_DB_CACHE

def get_kanji_components(kanji: str) -> list:
    db = _get_kanji_db()
    data = db.get(kanji, {})
    return data.get("components", [])

def get_all_supported_kanji() -> list:
    return list(_get_kanji_db().keys())

def get_manual_similarity_groups() -> list:
    return MANUAL_SIMILAR_GROUPS

_DIRECTORY_CACHE = None

def get_kanji_directory_data() -> dict:
    """
    Returns all Kanji grouped by JLPT level and stroke count.
    Used for the Kanji Directory homepage.
    """
    global _DIRECTORY_CACHE
    if _DIRECTORY_CACHE:
        return _DIRECTORY_CACHE
        
    db = _get_kanji_db()
    
    directory = {
        "jlpt": {"N5": [], "N4": [], "N3": [], "N2": [], "N1": [], "Other": []},
        "strokes": {}
    }
    
    for kanji, data in db.items():
        # Group by JLPT
        jlpt = data.get("jlpt")
        if jlpt in [1, 2, 3, 4, 5]:
            directory["jlpt"][f"N{jlpt}"].append(kanji)
        else:
            directory["jlpt"]["Other"].append(kanji)
            
        # Group by Strokes
        strokes = data.get("strokes")
        if strokes:
            s_key = f"{strokes} nét"
            if s_key not in directory["strokes"]:
                directory["strokes"][s_key] = []
            directory["strokes"][s_key].append(kanji)
            
    # Sort strokes keys numerically
    sorted_strokes = {k: v for k, v in sorted(directory["strokes"].items(), key=lambda x: int(x[0].split()[0]))}
    directory["strokes"] = sorted_strokes
    
    _DIRECTORY_CACHE = directory
    return directory

def get_kanji_details(kanji: str) -> dict:
    """
    Returns unified details for a Kanji from the consolidated kanji_db.json.
    """
    db = _get_kanji_db()
    data = db.get(kanji, {})
    
    return {
        "meanings": data.get("meanings", []),
        "readings_on": data.get("readings_on", []),
        "readings_kun": data.get("readings_kun", []),
        "hanviet": data.get("hanviet", ""),
        "strokes": data.get("strokes"),
        "jlpt": data.get("jlpt"),
        "mnemonic_hint": data.get("mnemonic_hint", ""),
        "mnemonic_radicals": data.get("mnemonic_radicals", []),
        "components": data.get("components", []),
        "hanzipy_level1_immediate": data.get("hanzipy_level1_immediate", []),
        "hanzipy_level2_radicals": data.get("hanzipy_level2_radicals", []),
        "hanzipy_level3_strokes": data.get("hanzipy_level3_strokes", [])
    }
