import os

IGNORE_DIRS = {'.git', '__pycache__', 'venv', 'node_modules', '.idea', '.vscode', '.pytest_cache', 'tests', 'migrations'}
IGNORE_FILES = {'.DS_Store'}

def generate_tree(dir_path, prefix=""):
    tree_str = ""
    try:
        entries = sorted(os.listdir(dir_path))
    except PermissionError:
        return ""
        
    entries = [e for e in entries if e not in IGNORE_DIRS and e not in IGNORE_FILES]
    
    for i, entry in enumerate(entries):
        path = os.path.join(dir_path, entry)
        is_last = (i == len(entries) - 1)
        connector = "└── " if is_last else "├── "
        
        if os.path.isdir(path):
            tree_str += f"{prefix}{connector}{entry}/\n"
            extension = "    " if is_last else "│   "
            tree_str += generate_tree(path, prefix + extension)
        else:
             # Only include certain file types to keep it clean, or just all files
             if entry.endswith('.py') or entry.endswith('.md') or entry.endswith('.html') or entry.endswith('.txt') or entry.endswith('.json'):
                 tree_str += f"{prefix}{connector}{entry}\n"
    return tree_str

def main():
    app_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    mindstack_app_dir = os.path.join(app_dir, 'mindstack_app')
    docs_dir = os.path.join(app_dir, 'docs')
    output_file = os.path.join(docs_dir, 'project_structure.md')
    
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("# Cấu trúc Dự án MindStack\n\n")
        f.write("Tài liệu này mô tả cấu trúc thư mục tự động được sinh ra của dự án MindStack.\n\n")
        
        f.write("## 1. Cấu trúc Tổng quan (`newmindstack/`)\n\n")
        f.write("```text\n")
        f.write("newmindstack/\n")
        f.write(generate_tree(app_dir))
        f.write("```\n\n")

    print(f"✅ Generated project structure documentation at {output_file}")

if __name__ == '__main__':
    main()
