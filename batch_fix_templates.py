import os

def fix_templates():
    templates_root = os.path.join('mindstack_app', 'templates', 'aora')
    if not os.path.exists(templates_root):
        print(f"Directory not found: {templates_root}")
        return

    target = "|default('v4')"
    replacement = ""
    count = 0

    for root, dirs, files in os.walk(templates_root):
        for file in files:
            if file.endswith('.html'):
                path = os.path.join(root, file)
                with open(path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                if target in content:
                    new_content = content.replace(target, replacement)
                    with open(path, 'w', encoding='utf-8') as f:
                        f.write(new_content)
                    print(f"Fixed: {path}")
                    count += 1
    
    print(f"Successfully processed {count} files.")

if __name__ == "__main__":
    fix_templates()
