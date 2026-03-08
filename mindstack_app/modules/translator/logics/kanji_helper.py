from typing import List
import re

def extract_kanji(text: str) -> List[str]:
    """
    Extracts unique Kanji characters from a string.
    Kanji range in Unicode: \u4e00-\u9faf
    """
    if not text:
        return []
    
    # Simple regex for Kanji characters
    kanji_pattern = re.compile(r'[\u4e00-\u9faf]')
    kanji_found = kanji_pattern.findall(text)
    
    # Return unique kanji while preserving order
    unique_kanji = []
    seen = set()
    for k in kanji_found:
        if k not in seen:
            unique_kanji.append(k)
            seen.add(k)
            
    return unique_kanji
