import json
import os

def build_mnemonics():
    full_data_path = r"c:\Code\MindStack\newmindstack\mindstack_app\modules\kanji\logics\kanji_data_full.json"
    output_path = r"c:\Code\MindStack\newmindstack\mindstack_app\modules\kanji\logics\kanji_mnemonics.json"
    
    with open(full_data_path, "r", encoding="utf-8") as f:
        data = json.load(f)
        
    mnemonics = {}
    for kanji, info in data.items():
        wk_meanings = info.get("wk_meanings", [])
        wk_radicals = info.get("wk_radicals", [])
        if wk_meanings or wk_radicals:
            mnemonics[kanji] = {
                "meanings": wk_meanings,
                "radicals": wk_radicals,
                "story": f"Gợi ý WaniKani: Chữ này được cấu tạo từ các bộ {', '.join(wk_radicals)} để tạo thành nghĩa '{', '.join(wk_meanings)}'." if wk_radicals else ""
            }
            
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(mnemonics, f, ensure_ascii=False, indent=2)
    print(f"Created mnemonics for {len(mnemonics)} kanji.")

if __name__ == "__main__":
    build_mnemonics()
