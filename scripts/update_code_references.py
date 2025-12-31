import os
import re

ROOT_DIR = r'c:\Code\MindStack\newmindstack\mindstack_app\modules'

# Config for path replacements in render_template calls
# Key: Relative path to module directory from ROOT_DIR
# Value: List of tuples (regex_pattern, replacement_string)
# Note: For regex, group 1 should usually be preserved if matching content.

PATH_UPDATES = {
    'user_profile': [
        (r"(['\"])(default/)", r"\1user_profile/default/"),
    ],
    'admin/api_key_management': [
        (r"(['\"])(default/)", r"\1admin/api_keys/"),
        (r"(['\"])(add_edit_api_key\.html)", r"\1admin/api_keys/\2"), # Fallback if flat
    ],
    'admin/user_management': [
        (r"(['\"])(default/)", r"\1admin/users/"),
    ],
    'content_management': [
        # Flat files in content_management root
        (r"render_template\((['\"])([^/]+\.html)", r"render_template(\1content_management/\2"),
    ],
    'content_management/courses': [
         # Flat files
        (r"render_template\((['\"])([^/]+\.html)", r"render_template(\1content_management/courses/\2"),
    ],
     'content_management/flashcards': [
         # sets/.., items/..
        (r"(['\"])(sets/)", r"\1content_management/flashcards/sets/"),
        (r"(['\"])(items/)", r"\1content_management/flashcards/items/"),
        (r"(['\"])(excel/)", r"\1content_management/flashcards/excel/"),
        (r"(['\"])(shared/)", r"\1content_management/flashcards/shared/"),
    ],
     'content_management/quizzes': [
         # sets/.., items/..
        (r"(['\"])(sets/)", r"\1content_management/quizzes/sets/"),
        (r"(['\"])(items/)", r"\1content_management/quizzes/items/"),
        (r"(['\"])(excel/)", r"\1content_management/quizzes/excel/"),
        (r"(['\"])(shared/)", r"\1content_management/quizzes/shared/"),
    ],
    'learning/sub_modules/course': [
        (r"(['\"])(default/)", r"\1course/"),
    ]
}

def update_references():
    print("Updating code references...")
    
    for root, dirs, files in os.walk(ROOT_DIR):
        rel_path = os.path.relpath(root, ROOT_DIR).replace(os.sep, '/')
        
        # 1. Update Blueprints (Remove template_folder)
        for file in files:
            if file == '__init__.py' or file.endswith('.py'):
                file_path = os.path.join(root, file)
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Regex to remove template_folder argument
                # Matches: template_folder=... (with optional comma and whitespace)
                # Be careful not to break syntax.
                # Pattern: template_folder=['"][^'"]+['"],?
                
                new_content = re.sub(r',\s*template_folder=[\'"][^\'"]+[\'"]', '', content)
                new_content = re.sub(r'template_folder=[\'"][^\'"]+[\'"],?\s*', '', new_content)

                if content != new_content:
                    print(f"Updated Blueprint in: {file_path}")
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.write(new_content)

        # 2. Update render_template paths based on config
        # Check if this exact directory needs updates
        update_rules = PATH_UPDATES.get(rel_path)
        if update_rules:
            print(f"Applying string replacements for: {rel_path}")
            for file in files:
                if file.endswith('.py'):
                    file_path = os.path.join(root, file)
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    original_content = content
                    for pattern, replacement in update_rules:
                        content = re.sub(pattern, replacement, content)
                    
                    if content != original_content:
                        print(f"  Modified: {file}")
                        with open(file_path, 'w', encoding='utf-8') as f:
                            f.write(content)

if __name__ == '__main__':
    update_references()
