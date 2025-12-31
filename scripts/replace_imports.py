
import os
import re

def bulk_replace_render_template(root_dir):
    """
    Recursively scans the codebase and replaces:
    from flask import ..., render_template, ...
    to
    from flask import ...
    from mindstack_app.core.templating import render_template
    
    Or simple:
    from flask import render_template
    to
    from mindstack_app.core.templating import render_template
    """
    
    for dirpath, dirnames, filenames in os.walk(root_dir):
        if 'venv' in dirpath or '.git' in dirpath or '__pycache__' in dirpath:
            continue
            
        for filename in filenames:
            if not filename.endswith('.py'):
                continue
                
            filepath = os.path.join(dirpath, filename)
            
            # Skip the wrapper file itself
            if 'core' in filepath and 'templating.py' in filepath:
                continue
                
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
                
            if 'render_template' not in content:
                continue
                
            new_content = content
            modified = False
            
            # Case 1: from flask import render_template (only)
            if re.search(r'^from flask import render_template\s*$', content, re.MULTILINE):
                new_content = re.sub(r'^from flask import render_template\s*$', 'from mindstack_app.core.templating import render_template', new_content, flags=re.MULTILINE)
                modified = True
                
            # Case 2: from flask import ..., render_template, ... (mixed)
            # This is harder to regex perfectly safely, but usually it's comma separated
            # Strategy: If render_template is in "from flask import ...", remove it from there and add new import
            elif re.search(r'from flask import .*render_template', content):
                # Check for "from flask import ( ... render_template ... )" multi-line style
                pass
                
            # SIMPLIFIED STRATEGY FOR ROBUSTNESS:
            # Just replace "from flask import" lines that contain render_template
            
            lines = content.splitlines()
            final_lines = []
            file_modified = False
            
            for line in lines:
                if line.strip().startswith('from flask import') and 'render_template' in line:
                    # Remove render_template from this line
                    parts = line.replace('from flask import', '').split(',')
                    cleaned_parts = [p.strip() for p in parts if p.strip() and p.strip() != 'render_template']
                    
                    if not cleaned_parts:
                        # It was ONLY render_template
                        final_lines.append('from mindstack_app.core.templating import render_template')
                    else:
                        # It had other imports
                        # Reconstruct the flask import line
                        new_flask_import = f"from flask import {', '.join(cleaned_parts)}"
                        final_lines.append(new_flask_import)
                        final_lines.append('from mindstack_app.core.templating import render_template')
                    
                    file_modified = True
                else:
                    final_lines.append(line)
            
            if file_modified:
                print(f"Modifying {filepath}")
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write('\n'.join(final_lines) + '\n')

if __name__ == '__main__':
    bulk_replace_render_template('c:/Code/MindStack/newmindstack/mindstack_app')
