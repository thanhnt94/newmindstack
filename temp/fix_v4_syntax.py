"""Fix malformed extends and properly implement dynamic versioning in V4 templates."""
import os
import re

V4_PAGES = r"c:\Code\MindStack\newmindstack\mindstack_app\templates\v4\pages"

VERSION_DEF = "{% set _v = template_version|default('v4') %}"

def fix_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    original = content
    
    # Fix malformed extends patterns like: {% extends _v ~ '/base.html" %}
    # Should be: {% extends _v ~ '/base.html' %}
    content = re.sub(
        r"\{%\s*extends\s+_v\s*~\s*'/([^'\"]+)\"\s*%\}",
        r"{% extends _v ~ '/\1' %}",
        content
    )
    
    # Also fix double quote version
    content = re.sub(
        r'\{%\s*extends\s+_v\s*~\s*"/([^"\']+)\'\s*%\}',
        r"{% extends _v ~ '/\1' %}",
        content
    )
    
    # Ensure _v is defined BEFORE extends statement
    if "_v = template_version" in content:
        # Check if _v definition comes AFTER extends
        extends_pos = content.find('{% extends')
        v_def_pos = content.find("{% set _v = template_version")
        
        if extends_pos != -1 and v_def_pos != -1 and v_def_pos > extends_pos:
            # Move _v definition before extends
            # Remove the misplaced definition
            content = content.replace(VERSION_DEF + "\n", "")
            content = content.replace("\n" + VERSION_DEF, "")
            content = content.replace(VERSION_DEF, "")
            
            # Add before extends
            extends_match = re.search(r'\{%\s*extends\s+', content)
            if extends_match:
                pos = extends_match.start()
                content = content[:pos] + VERSION_DEF + "\n" + content[pos:]
    
    if content != original:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        return True
    return False

def main():
    count = 0
    for root, dirs, files in os.walk(V4_PAGES):
        for fname in files:
            if fname.endswith('.html'):
                fpath = os.path.join(root, fname)
                if fix_file(fpath):
                    count += 1
                    print(f"Fixed: {fpath}")
    print(f"\nTotal files fixed: {count}")

if __name__ == "__main__":
    main()
