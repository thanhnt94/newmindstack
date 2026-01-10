"""Batch update V4 templates to use dynamic template_version instead of hardcoded 'v4'."""
import os
import re

V4_PAGES = r"c:\Code\MindStack\newmindstack\mindstack_app\templates\v4\pages"

def make_includes_dynamic(content):
    """Replace hardcoded v4/ includes with dynamic _v ~ syntax."""
    
    # First, add the version variable definition at the top if not present
    version_def = "{% set _v = template_version|default('v4') %}"
    
    # Check if already has version definition
    if "_v = template_version" not in content:
        # Add BEFORE extends line (Jinja requires variable defined before use)
        extends_match = re.search(r'(\{%\s*extends\s+)', content)
        if extends_match:
            insert_pos = extends_match.start()
            content = content[:insert_pos] + version_def + "\n" + content[insert_pos:]
        else:
            # Add after any header comment
            if content.strip().startswith('{#'):
                close_comment = content.find('#}')
                if close_comment > 0:
                    insert_pos = close_comment + 2
                    content = content[:insert_pos] + "\n" + version_def + content[insert_pos:]
            else:
                content = version_def + "\n" + content
    
    # Replace hardcoded v4/ paths with dynamic ones
    # Pattern: 'v4/path' or "v4/path" -> _v ~ '/path'
    # Only for include/import/from statements
    patterns = [
        (r"include\s+['\"]v4/", "include _v ~ '/"),
        (r"import\s+['\"]v4/", "import _v ~ '/"),
        (r"from\s+['\"]v4/", "from _v ~ '/"),
        (r"extends\s+['\"]v4/", "extends _v ~ '/"),
    ]
    
    for pattern, replacement in patterns:
        # Handle both single and double quotes
        content = re.sub(pattern, replacement, content)
        # Close the string properly - find the closing quote after our replacement
        # This is tricky, let's do a simpler approach
    
    # Simpler approach: direct string replacement
    content = content.replace("include 'v4/", "include _v ~ '/")
    content = content.replace('include "v4/', 'include _v ~ "/')
    content = content.replace("import 'v4/", "import _v ~ '/")
    content = content.replace('import "v4/', 'import _v ~ "/')
    content = content.replace("from 'v4/", "from _v ~ '/")
    content = content.replace('from "v4/', 'from _v ~ "/')
    content = content.replace("extends 'v4/", "extends _v ~ '/")
    content = content.replace('extends "v4/', 'extends _v ~ "/')
    
    return content

def process_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Skip if no v4/ references
    if 'v4/' not in content:
        return False
    
    new_content = make_includes_dynamic(content)
    
    if new_content != content:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(new_content)
        return True
    return False

def main():
    count = 0
    for root, dirs, files in os.walk(V4_PAGES):
        for fname in files:
            if fname.endswith('.html'):
                fpath = os.path.join(root, fname)
                if process_file(fpath):
                    count += 1
                    print(f"Updated: {fpath}")
    print(f"\nTotal files updated: {count}")

if __name__ == "__main__":
    main()
