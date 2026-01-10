"""
Fix import placement issues caused by the batch update script.
The previous script incorrectly inserted imports inside multi-line `from flask import (` statements.
"""
import os
import re

MODULES_DIR = r"c:\Code\MindStack\newmindstack\mindstack_app\modules"

IMPORT_LINE = "from mindstack_app.utils.template_helpers import render_dynamic_template"

def fix_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Check if file has the import
    if IMPORT_LINE not in content:
        return False
    
    original = content
    
    # Pattern: import inserted inside `from flask import (` block
    # Fix by finding misplaced imports and moving them
    
    # Check for pattern: from flask import (\nIMPORT_LINE
    bad_pattern = re.compile(
        r"(from flask import \(\s*)\n" + re.escape(IMPORT_LINE) + r"\n",
        re.MULTILINE
    )
    
    if bad_pattern.search(content):
        # Remove the misplaced import
        content = re.sub(
            re.escape(IMPORT_LINE) + r"\n\s*",
            "",
            content,
            count=1
        )
        
        # Find a good place to add it back - after the flask import block
        flask_import_end = re.search(r"from flask import \([^)]+\)\n", content)
        if flask_import_end:
            insert_pos = flask_import_end.end()
            content = content[:insert_pos] + IMPORT_LINE + "\n" + content[insert_pos:]
    
    # Also check for import inside any multi-line import block
    # Pattern: something like "    Blueprint," preceded by our import
    bad_pattern2 = re.compile(
        r"(\n" + re.escape(IMPORT_LINE) + r"\n)(\s+\w+,)",
        re.MULTILINE
    )
    
    if bad_pattern2.search(content):
        # Remove the misplaced import and its newline
        content = re.sub(
            r"\n" + re.escape(IMPORT_LINE) + r"(?=\n\s+\w+,)",
            "",
            content
        )
        
        # Find end of imports and add there
        # Look for first empty line after imports or first function/class
        last_import = 0
        for m in re.finditer(r"^(from|import)\s+", content, re.MULTILINE):
            last_import = max(last_import, m.end())
        
        # Find the end of that import line
        end_of_import = content.find('\n', last_import)
        if end_of_import > 0:
            # Check if import is already there
            if IMPORT_LINE not in content:
                content = content[:end_of_import+1] + IMPORT_LINE + "\n" + content[end_of_import+1:]
    
    if content != original:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        return True
    
    return False

def main():
    fixed = 0
    for root, dirs, files in os.walk(MODULES_DIR):
        if '__pycache__' in root:
            continue
        for fname in files:
            if fname.endswith('.py'):
                fpath = os.path.join(root, fname)
                if fix_file(fpath):
                    fixed += 1
                    print(f"Fixed: {fpath}")
    
    print(f"\nTotal files fixed: {fixed}")

if __name__ == "__main__":
    main()
