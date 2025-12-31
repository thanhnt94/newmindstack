
try:
    with open("all_files_legacy.txt", "r", encoding="utf-16") as f:
        lines = f.readlines()
except:
    with open("all_files_legacy.txt", "r", encoding="utf-8") as f:
        lines = f.readlines()

found = []
for line in lines:
    if "session_engine.js" in line:
        found.append(line.strip())

with open("found_js_paths.txt", "w", encoding="utf-8") as f:
    for path in found:
        f.write(path + "\n")
