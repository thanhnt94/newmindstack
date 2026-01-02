import os

root_dir = r"c:\Code\MindStack\newmindstack\mindstack_app"
search_str = "stats.dashboard"
print(f"Searching for '{search_str}' in {root_dir}...")

count = 0
with open('found_files.txt', 'w', encoding='utf-8') as outfile:
    for dirpath, dirnames, filenames in os.walk(root_dir):
        for filename in filenames:
            if filename.endswith(('.html', '.py', '.js', '.css')):
                filepath = os.path.join(dirpath, filename)
                try:
                    with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read()
                        if search_str in content:
                            outfile.write(f"{filepath}\n")
                            count += 1
                except Exception as e:
                    outfile.write(f"Error reading {filepath}: {e}\n")

print(f"Done. Found {count} files. Specific paths written to found_files.txt")
