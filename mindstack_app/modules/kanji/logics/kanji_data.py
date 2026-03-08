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

KANGXI_RADICALS = {
    "1 nét": ["一", "丨", "丶", "丿", "乙", "亅"],
    "2 nét": ["二", "亠", "人", "儿", "入", "八", "冂", "冖", "冫", "几", "凵", "刀", "力", "勹", "匕", "匚", "匸", "十", "卜", "卩", "厂", "厶", "又"],
    "3 nét": ["口", "囗", "土", "士", "夂", "夊", "夕", "大", "女", "子", "宀", "寸", "小", "尢", "尸", "屮", "山", "巛", "工", "己", "巾", "干", "幺", "广", "廴", "廾", "弋", "弓", "彐", "彡", "彳"],
    "4 nét": ["心", "戈", "戶", "手", "支", "攴", "文", "斗", "斤", "方", "无", "日", "曰", "月", "木", "欠", "止", "歹", "殳", "毋", "比", "毛", "氏", "气", "水", "火", "爪", "父", "爻", "爿", "片", "牙", "牛", "犬"],
    "5 nét": ["玄", "玉", "瓜", "瓦", "甘", "生", "用", "田", "疋", "疒", "癶", "白", "皮", "皿", "目", "矛", "矢", "石", "示", "禸", "禾", "穴", "立"],
    "6 nét": ["竹", "米", "糸", "缶", "网", "羊", "羽", "老", "而", "耒", "耳", "聿", "肉", "臣", "自", "至", "臼", "舌", "舛", "舟", "艮", "色", "艸", "虍", "虫", "血", "行", "衣", "襾"],
    "7 nét": ["見", "角", "言", "谷", "豆", "豕", "豸", "貝", "赤", "走", "足", "身", "車", "辛", "辰", "辵", "邑", "酉", "釆", "里"],
    "8 nét": ["金", "長", "門", "阜", "隶", "隹", "雨", "青", "非"],
    "9 nét": ["面", "革", "韋", "韭", "音", "頁", "風", "飛", "食", "首", "香"],
    "10 nét": ["馬", "骨", "高", "髟", "鬥", "鬯", "鬲", "鬼"],
    "11 nét": ["魚", "鳥", "鹵", "鹿", "麥", "麻"],
    "12 nét": ["黃", "黍", "黑", "黹"],
    "13 nét": ["黽", "鼎", "鼓", "鼠"],
    "14 nét": ["鼻", "齊"],
    "15 nét": ["齒"],
    "16 nét": ["龍", "龜"],
    "17 nét": ["龠"]
}

_DIRECTORY_CACHE = None

def get_kanji_directory_data() -> dict:
    """
    Returns all Kanji grouped by JLPT level, stroke count, and predefined radicals.
    Used for the Kanji Directory homepage.
    """
    global _DIRECTORY_CACHE
    if _DIRECTORY_CACHE:
        return _DIRECTORY_CACHE
        
    db = _get_kanji_db()
    
    directory = {
        "jlpt": {"N5": [], "N4": [], "N3": [], "N2": [], "N1": [], "Other": []},
        "strokes": {},
        "radicals": KANGXI_RADICALS
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
