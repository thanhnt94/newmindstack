import json
import os

def load_json(name):
    path = os.path.join(os.path.dirname(__file__), name)
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        return {}

def main():
    krad = load_json('kradfile.json')
    readings = load_json('kanji_readings.json')
    hanviet_raw = load_json('kanji_hanviet.json')
    vi_data = load_json('kanji_vietnamese.json')
    mnemonics = load_json('kanji_mnemonics.json')
    elements = load_json('kanji_elements.json') # Old elements

    hanviet = {}
    if isinstance(hanviet_raw, dict) and 'data' in hanviet_raw:
        for item in hanviet_raw['data']:
            char, hv = item[0], item[1]
            if char in hanviet:
                hanviet[char] += f", {hv}"
            else:
                hanviet[char] = hv

    # Get union of all kanjis
    all_chars = set()
    for d in (krad, readings, vi_data, mnemonics, elements):
        all_chars.update(d.keys())

    kanji_db = {}
    for char in all_chars:
        # Priority to Kradfile, fallback to elements
        comps = krad.get(char)
        if not comps: comps = elements.get(char, [])
        
        r = readings.get(char, {})
        vi = vi_data.get(char, {})
        m = mnemonics.get(char, {})
        
        hv = vi.get("hv") or hanviet.get(char, "")
        meanings = vi.get("meanings")
        if not meanings: meanings = r.get("meanings", [])

        kanji_db[char] = {
            "components": comps,
            "meanings": meanings,
            "readings_on": r.get("readings_on", []),
            "readings_kun": r.get("readings_kun", []),
            "hanviet": hv.upper() if hv else "",
            "strokes": r.get("strokes"),
            "jlpt": r.get("jlpt_new") or r.get("jlpt_old"),
            "mnemonic_hint": m.get("story", ""),
            "mnemonic_radicals": m.get("radicals", [])
        }

    out_path = os.path.join(os.path.dirname(__file__), 'kanji_db.json')
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(kanji_db, f, ensure_ascii=False, separators=(',', ':'))

    print(f"Merged {len(kanji_db)} kanjis into kanji_db.json")

    # Clean up the old files
    files_to_remove = [
        'kradfile.json', 'kanji_readings.json', 'kanji_hanviet.json',
        'kanji_vietnamese.json', 'kanji_mnemonics.json', 'kanji_elements.json'
    ]
    for filename in files_to_remove:
        path = os.path.join(os.path.dirname(__file__), filename)
        if os.path.exists(path):
            os.remove(path)
            print(f"Removed {filename}")

if __name__ == '__main__':
    main()
