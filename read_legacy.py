
import pathlib

files = ['temp_css_path.txt', 'temp_js_paths.txt']

def read_file(path):
    try:
        return pathlib.Path(path).read_text(encoding='utf-16')
    except:
        return pathlib.Path(path).read_text(encoding='utf-8', errors='ignore')

for f in files:
    content = read_file(f)
    for line in content.splitlines():
        if 'session_single.css' in line or 'mobile' in line or 'session' in line:
            print(line.strip())
