import json
import os

def process_kanji_banks():
    base_dir = r"c:\Code\MindStack\newmindstack\mindstack_app\modules\kanji\logics"
    files = ["kanji_bank_1.json", "kanji_bank_2.json"]
    
    vietnamese_data = {}
    
    for filename in files:
        path = os.path.join(base_dir, filename)
        if not os.path.exists(path):
            print(f"Skipping {filename}, not found.")
            continue
            
        with open(path, "r", encoding="utf-8") as f:
            try:
                data = json.load(f)
                for entry in data:
                    if len(entry) < 6:
                        continue
                    
                    char = entry[0]
                    hv = entry[1]
                    meanings = entry[4]
                    
                    # Clean up meanings: "[á] thứ hai" -> "thứ hai"
                    clean_meanings = []
                    for m in meanings:
                        if "]" in m:
                            m = m.split("]", 1)[1].strip()
                        clean_meanings.append(m)
                    
                    vietnamese_data[char] = {
                        "hv": hv,
                        "meanings": clean_meanings
                    }
            except Exception as e:
                print(f"Error processing {filename}: {e}")
                
    output_path = os.path.join(base_dir, "kanji_vietnamese.json")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(vietnamese_data, f, ensure_ascii=False, indent=2)
    
    print(f"Successfully created {output_path} with {len(vietnamese_data)} entries.")

if __name__ == "__main__":
    process_kanji_banks()
