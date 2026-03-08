import urllib.request
import json
import gzip
import os

def download_kradfile():
    url = "http://ftp.monash.edu/pub/nihongo/kradfile.gz"
    output_path = r"c:\Code\MindStack\newmindstack\mindstack_app\modules\kanji\logics\kradfile.json"
    
    print(f"Downloading Kradfile from {url}...")
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req) as response:
            compressed_data = response.read()
            raw_data = gzip.decompress(compressed_data).decode('euc-jp')
            
        krad_dict = {}
        for line in raw_data.splitlines():
            if line.startswith('#') or not line.strip():
                continue
            # Format: KANJI : RAD1 RAD2 ...
            if ' : ' in line:
                kanji, radicals = line.split(' : ')
                krad_dict[kanji.strip()] = radicals.strip().split(' ')
                
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(krad_dict, f, ensure_ascii=False, indent=2)
        print(f"Successfully processed Kradfile: {len(krad_dict)} entries.")
    except Exception as e:
        print(f"Failed to process Kradfile: {e}")

def download_kanjialive():
    url = "https://raw.githubusercontent.com/kanjialive/kanji-data-media/master/language-data/kanji-data.json"
    output_path = r"c:\Code\MindStack\newmindstack\mindstack_app\modules\kanji\logics\kanjialive.json"
    
    print(f"Downloading KanjiAlive from {url}...")
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req) as response:
            data = json.loads(response.read().decode('utf-8'))
            
        # Refactor data to be keyed by kanji character
        ka_dict = {}
        for item in data:
            kanji = item.get("kanji", {}).get("character")
            meaning = item.get("kanji", {}).get("meaning", {}).get("english")
            mnemonic = item.get("radical", {}).get("hint")
            if kanji:
                ka_dict[kanji] = {
                    "meaning_en": meaning,
                    "mnemonic": mnemonic
                }
                
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(ka_dict, f, ensure_ascii=False, indent=2)
        print(f"Successfully processed KanjiAlive: {len(ka_dict)} entries.")
    except Exception as e:
        print(f"Failed to process KanjiAlive: {e}")

if __name__ == "__main__":
    download_kradfile()
    download_kanjialive()
