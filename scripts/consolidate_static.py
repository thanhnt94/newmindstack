import os
import shutil
import re

# Configuration: (Source Path, Namespace, Endpoint Name)
MIGRATION_MAP = [
    (
        r'mindstack_app/modules/learning/sub_modules/quiz/individual/static',
        'quiz',
        'learning.quiz_learning.static'
    ),
    (
        r'mindstack_app/modules/admin/api_key_management/static',
        'admin_api',
        'api_key_management.static' 
    ),
    (
        r'mindstack_app/modules/shared/static',
        'shared',
        'shared.static'
    ),
    (
        r'mindstack_app/modules/translator/static',
        'translator',
        'translator.static'
    )
]

# Root paths
PROJECT_ROOT = os.getcwd()
STATIC_ROOT = os.path.join(PROJECT_ROOT, 'mindstack_app', 'static')
TEMPLATES_ROOT = os.path.join(PROJECT_ROOT, 'mindstack_app', 'templates', 'default')

def migrate_static_files():
    for source_rel, namespace, endpoint in MIGRATION_MAP:
        source_abs = os.path.join(PROJECT_ROOT, source_rel)
        if not os.path.exists(source_abs):
            print(f"Skipping missing source: {source_abs}")
            continue

        target_dir = os.path.join(STATIC_ROOT, namespace)
        os.makedirs(target_dir, exist_ok=True)

        print(f"Migrating {namespace}...")
        # Copy files
        for root, dirs, files in os.walk(source_abs):
            for file in files:
                src_file = os.path.join(root, file)
                # Calculate relative path from source static root
                rel_path = os.path.relpath(src_file, source_abs)
                dest_file = os.path.join(target_dir, rel_path)
                
                os.makedirs(os.path.dirname(dest_file), exist_ok=True)
                shutil.copy2(src_file, dest_file)
                print(f"  Copied {rel_path}")

        # Update Templates
        update_templates(endpoint, namespace)

def update_templates(endpoint, namespace):
    print(f"Updating templates for endpoint: {endpoint} -> namespace: {namespace}")
    
    # Regex to find url_for('endpoint.static', filename='...')
    # Handles both single and double quotes
    # Capture group 1: filename value
    pattern = re.compile(rf"url_for\s*\(\s*['\"]{re.escape(endpoint)}['\"]\s*,\s*filename\s*=\s*['\"]([^'\"]+)['\"]\s*\)")

    for root, dirs, files in os.walk(TEMPLATES_ROOT):
        for file in files:
            if not file.endswith('.html'):
                continue
            
            file_path = os.path.join(root, file)
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            if endpoint in content:
                # Replacement function
                def replace_match(match):
                    original_filename = match.group(1)
                    new_filename = f"{namespace}/{original_filename}".replace('\\', '/')
                    return f"url_for('static', filename='{new_filename}')"

                new_content = pattern.sub(replace_match, content)

                if new_content != content:
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.write(new_content)
                    print(f"  Updated {file}")

if __name__ == "__main__":
    migrate_static_files()
