import os
import shutil

ROOT_DIR = r'c:\Code\MindStack\newmindstack\mindstack_app'
TARGET_DIR = os.path.join(ROOT_DIR, 'templates', 'v1')

# Detailed mapping from Implementation Plan
# Key: Module path relative to 'mindstack_app' (e.g. 'modules/auth')
# Value: Target subdirectory in 'templates/v1/' (e.g. 'auth')
# If value is None, it means we keep the existing internal structure but move to root of target (risky if not namespaced)
# But based on plan, we have specific targets.

MAPPINGS = {
    'modules/auth': 'auth',
    'modules/dashboard': 'dashboard',
    'modules/landing': 'landing',
    'modules/shared': '.',  # Root of templates/v1
    'modules/user_profile': 'user_profile', # Was default -> user_profile/default
    'modules/admin/api_key_management': 'admin/api_keys',
    'modules/admin/user_management': 'admin/users',
    'modules/content_management': 'content_management',
    'modules/content_management/courses': 'content_management/courses',
    'modules/content_management/flashcards': 'content_management/flashcards',
    'modules/content_management/quizzes': 'content_management/quizzes',
    'modules/learning': 'learning',
    'modules/learning/sub_modules/flashcard': 'flashcard',
    'modules/learning/sub_modules/flashcard/individual': 'individual',
    'modules/learning/sub_modules/flashcard/dashboard': 'flashcard/dashboard_internal', # Avoid collision with flashcard/dashboard? Check audit.
    # Audit says: modules\learning\sub_modules\flashcard\dashboard\templates -> dashboard\index.html
    # This conflicts with modules\dashboard\templates -> dashboard\index.html if we point both to 'dashboard'.
    # So flashcard dashboard needs a distinct namespace. 
    # Let's map it to 'flashcard/dashboard' and ensure the main dashboard is valid.
    # Wait, main dashboard has 'dashboard/default/index.html'.  
    # Flashcard dashboard has 'dashboard/index.html'. 
    # If we map flashcard dashboard to 'flashcard', it becomes 'flashcard/dashboard/index.html'.
    
    'modules/notes': 'notes',
    'modules/notification': 'notification',
    'modules/feedback': 'feedback',
    'modules/goals': 'goals',
    'modules/gamification': 'gamification',
    'modules/ai_services': 'ai_services',
    'modules/learning/sub_modules/course': 'course',
    'modules/learning/sub_modules/collab': 'collab',
    'modules/learning/sub_modules/practice': 'practice',
    'modules/learning/sub_modules/quiz': 'quiz',
    'modules/learning/sub_modules/stats': 'stats',
    'modules/learning/sub_modules/vocabulary': 'vocabulary',
    'modules/learning/sub_modules/vocabulary/listening': 'vocabulary/listening',
    'modules/learning/sub_modules/vocabulary/matching': 'vocabulary/matching',
    'modules/learning/sub_modules/vocabulary/mcq': 'vocabulary/mcq',
    'modules/learning/sub_modules/vocabulary/memrise': 'vocabulary/memrise',
    'modules/learning/sub_modules/vocabulary/speed': 'vocabulary/speed',
    'modules/learning/sub_modules/vocabulary/typing': 'vocabulary/typing',
    'modules/learning/sub_modules/flashcard/individual': 'flashcard/individual', 
    # Overriding previous 'individual' mapping to be more specific 'flashcard/individual' 
    # because 'individual' is too generic.
}

def migrate():
    print(f"Migrating templates to {TARGET_DIR}...")
    if not os.path.exists(TARGET_DIR):
        os.makedirs(TARGET_DIR)

    counts = {'moved': 0, 'skipped': 0}

    for module_rel_path, target_sub_path in MAPPINGS.items():
        module_full_path = os.path.join(ROOT_DIR, module_rel_path.replace('/', os.sep))
        templates_dir = os.path.join(module_full_path, 'templates')

        if not os.path.exists(templates_dir):
            print(f"Skipping {module_rel_path}: No templates dir found.")
            continue

        print(f"Processing {module_rel_path} -> {target_sub_path}")
        
        # Calculate full target directory
        full_target_dir = os.path.normpath(os.path.join(TARGET_DIR, target_sub_path))
        
        for root, dirs, files in os.walk(templates_dir):
            for file in files:
                source_file = os.path.join(root, file)
                rel_in_templates = os.path.relpath(source_file, templates_dir)
                
                # Logic for handling collisions/prefixes?
                # The MAPPINGS key handles the prefixing.
                # e.g. if file is 'default/index.html' and target is 'admin/users',
                # dest becomes 'admin/users/default/index.html'.
                
                # Wait, if target is 'admin/users' and file is 'default/add_edit_user.html'
                # It becomes 'admin/users/default/add_edit_user.html'.
                # Is that what we want? The plan said:
                # admin.user_management | default/... | Namespace | admin/users/ | YES
                # implies we want 'admin/users/default/...' ??
                
                # Check plan again:
                # admin.user_management | default/... | Namespace | admin/users/
                # If we want 'admin/users/add_edit_user.html', we need to strip 'default'??
                # The plan implies namespacing.
                # If the existing path is 'default/...', and we map to 'admin/users', we get 'admin/users/default/...'.
                # This is safe. If we want to flatten 'default', that's an extra step.
                # Let's keep it simple: Map module template root to Target Path.
                
                dest_file = os.path.join(full_target_dir, rel_in_templates)
                
                dest_dir = os.path.dirname(dest_file)
                if not os.path.exists(dest_dir):
                    os.makedirs(dest_dir)
                
                # print(f"  Move: {rel_in_templates} -> {os.path.relpath(dest_file, TARGET_DIR)}")
                shutil.move(source_file, dest_file)
                counts['moved'] += 1
        
        # Clean up empty templates dir
        try:
            os.rmdir(templates_dir) # Only works if empty
            print(f"  Removed empty dir: {templates_dir}")
        except OSError:
            print(f"  Dir not empty or error: {templates_dir}")

    print(f"Migration complete. Moved {counts['moved']} files.")

if __name__ == '__main__':
    migrate()
