"""
Batch update all routes to use render_dynamic_template instead of hardcoded v3/v4 paths.
"""
import os
import re

MODULES_DIR = r"c:\Code\MindStack\newmindstack\mindstack_app\modules"

# Pattern to match render_template('v3/... or render_template('v4/...
PATTERN = re.compile(
    r"render_template\(\s*['\"]v[34]/([^'\"]+)['\"]",
    re.MULTILINE
)

# Import statement to add
IMPORT_STATEMENT = "from mindstack_app.utils.template_helpers import render_dynamic_template"

def process_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Check if file has any v3/ or v4/ render_template calls
    matches = PATTERN.findall(content)
    if not matches:
        return False, 0
    
    original = content
    
    # Replace render_template('v3/path' with render_dynamic_template('path'
    # and render_template('v4/path' with render_dynamic_template('path'
    content = re.sub(
        r"render_template\(\s*['\"]v[34]/([^'\"]+)['\"]",
        r"render_dynamic_template('\1'",
        content
    )
    
    # Add import if not present
    if IMPORT_STATEMENT not in content and "render_dynamic_template" in content:
        # Find the import section (after from flask import ...)
        flask_import = re.search(r"from flask import[^\n]+\n", content)
        if flask_import:
            insert_pos = flask_import.end()
            content = content[:insert_pos] + IMPORT_STATEMENT + "\n" + content[insert_pos:]
        else:
            # Add at top after any docstrings
            lines = content.split('\n')
            insert_idx = 0
            for i, line in enumerate(lines):
                if line.strip() and not line.strip().startswith('#') and not line.strip().startswith('"""') and not line.strip().startswith("'''"):
                    if 'import' in line or 'from' in line:
                        insert_idx = i + 1
                        break
            lines.insert(insert_idx, IMPORT_STATEMENT)
            content = '\n'.join(lines)
    
    if content != original:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        return True, len(matches)
    
    return False, 0

def main():
    total_files = 0
    total_replacements = 0
    updated_files = []
    
    for root, dirs, files in os.walk(MODULES_DIR):
        # Skip __pycache__
        if '__pycache__' in root:
            continue
        
        for fname in files:
            if fname.endswith('.py'):
                fpath = os.path.join(root, fname)
                updated, count = process_file(fpath)
                if updated:
                    total_files += 1
                    total_replacements += count
                    rel_path = fpath.replace(MODULES_DIR, '').lstrip('\\/')
                    updated_files.append(f"  - {rel_path}: {count} replacements")
                    print(f"Updated: {rel_path} ({count} replacements)")
    
    print(f"\n{'='*50}")
    print(f"Total files updated: {total_files}")
    print(f"Total replacements: {total_replacements}")
    print(f"{'='*50}")
    
    if updated_files:
        print("\nUpdated files:")
        for f in updated_files:
            print(f)

if __name__ == "__main__":
    main()
