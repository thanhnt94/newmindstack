import os
import shutil
import pathlib

# Configuration
BASE_DIR = os.path.join(os.getcwd(), 'mindstack_app', 'templates', 'default')
BACKUP_DIR = os.path.join(os.getcwd(), 'mindstack_app', 'templates', 'default_backup')

# Define target structure keys
BASE = 'base'
PAGES = 'pages'
COMPONENTS = 'components'

# Mapping: (Existing Relative Path) -> (New Relative Path)
# If new path is None, it means we handle it specially or it's a directory move
MOVES = {
    # --- Category 1: Base ---
    'base.html': f'{BASE}/layout.html',
    '_base_desktop.html': f'{BASE}/layouts/desktop.html',
    '_base_mobile.html': f'{BASE}/layouts/mobile.html',
    'includes': f'{BASE}/includes', # Move entire directory
    
    # --- Category 2: Pages (Direct Directories) ---
    'admin': f'{PAGES}/admin',
    'auth': f'{PAGES}/auth',
    'landing': f'{PAGES}/landing',
    'user_profile': f'{PAGES}/user_profile',
    'course': f'{PAGES}/course',
    'setup': f'{PAGES}/setup', # Likely from flashcard setup if exists at root, otherwise see below
    
    # --- Category 2: Pages (Specific Files/Subdirs) ---
    # Dashboard
    'dashboard/default/index.html': f'{PAGES}/dashboard/index.html',
    
    # Flashcard Pages
    'flashcard/individual/setup': f'{PAGES}/flashcard/setup',
    'flashcard/individual/individual/cardsession/v2/index.html': f'{PAGES}/flashcard/session/index.html',
    # Note: v1 session might need similar handling if active, assuming v2 for now based on user context
    
    # Quiz Pages
    'quiz/individual/dashboard': f'{PAGES}/quiz/dashboard',
    'quiz/individual/session': f'{PAGES}/quiz/session',
    'quiz/battle': f'{PAGES}/quiz/battle',
    
    # --- Category 3: Components ---
    # Dashboard Components
    'dashboard/default/_desktop.html': f'{COMPONENTS}/dashboard/desktop_view.html',
    'dashboard/default/_mobile.html': f'{COMPONENTS}/dashboard/mobile_view.html',
    'dashboard/default/_base.html': f'{COMPONENTS}/dashboard/base.html', # Dashboard specific base
    
    # Flashcard Components
    'flashcard/individual/individual/_sets_list.html': f'{COMPONENTS}/flashcard/sets_list.html',
    'flashcard/individual/individual/_sets_list_desktop.html': f'{COMPONENTS}/flashcard/sets_list_desktop.html',
    'flashcard/individual/individual/_sets_list_mobile.html': f'{COMPONENTS}/flashcard/sets_list_mobile.html',
    'flashcard/individual/individual/_modes_list.html': f'{COMPONENTS}/flashcard/modes_list.html',
    'flashcard/individual/individual/_modes_list_desktop.html': f'{COMPONENTS}/flashcard/modes_list_desktop.html',
    'flashcard/individual/individual/_modes_list_mobile.html': f'{COMPONENTS}/flashcard/modes_list_mobile.html',
    
    # Shared Styles
    'content_management/_shared_styles.html': f'{COMPONENTS}/shared/styles.html',
}

def reorganize():
    # 1. Backup
    if os.path.exists(BASE_DIR):
        if os.path.exists(BACKUP_DIR):
            shutil.rmtree(BACKUP_DIR)
        shutil.copytree(BASE_DIR, BACKUP_DIR)
        print(f"Backed up to {BACKUP_DIR}")

    # 2. Create New Root Dirs
    for d in [BASE, PAGES, COMPONENTS]:
        os.makedirs(os.path.join(BASE_DIR, d), exist_ok=True)

    # 3. Execute Moves
    print("Moving files...")
    for src_rel, dst_rel in MOVES.items():
        src_path = os.path.join(BASE_DIR, src_rel)
        dst_path = os.path.join(BASE_DIR, dst_rel)
        
        if not os.path.exists(src_path):
            print(f"[SKIP] Source not found: {src_rel}")
            continue
            
        # Create dest dir if needed
        os.makedirs(os.path.dirname(dst_path), exist_ok=True)
        
        if os.path.isdir(src_path):
            # For directories, valid destination must not exist or be empty
            if os.path.exists(dst_path):
                # Merge? Or just warn? For now, let's try to copy tree content
                copy_tree(src_path, dst_path)
                shutil.rmtree(src_path)
                print(f"[DIR] Moved {src_rel} -> {dst_rel}")
            else:
                shutil.move(src_path, dst_path)
                print(f"[DIR] Moved {src_rel} -> {dst_rel}")
        else:
            shutil.move(src_path, dst_path)
            print(f"[FILE] Moved {src_rel} -> {dst_rel}")
            
    # 4. cleanup empty dirs (optional, simple pass)
    clean_empty_dirs(BASE_DIR)

def copy_tree(src, dst):
    for item in os.listdir(src):
        s = os.path.join(src, item)
        d = os.path.join(dst, item)
        if os.path.isdir(s):
            shutil.copytree(s, d, dirs_exist_ok=True)
        else:
            shutil.copy2(s, d)

def clean_empty_dirs(path):
    for root, dirs, files in os.walk(path, topdown=False):
        for name in dirs:
            try:
                os.rmdir(os.path.join(root, name))
            except:
                pass

if __name__ == "__main__":
    try:
        reorganize()
        print("\nSUCCESS: Organization complete.")
    except Exception as e:
        print(f"\nERROR: {e}")
        print("Restoring from backup...")
        if os.path.exists(BACKUP_DIR):
            shutil.rmtree(BASE_DIR)
            shutil.copytree(BACKUP_DIR, BASE_DIR)
            print("Restored.")
