import os
import shutil

BASE_DIR = os.path.join(os.getcwd(), 'mindstack_app', 'templates', 'default')
PAGES_DIR = os.path.join(BASE_DIR, 'pages')

# Folders to explicitly ignore (already correct)
IGNORE = {'base', 'pages', 'components', 'includes'} # includes should be gone but just in case

def cleanup():
    print(f"Scanning {BASE_DIR}...")
    
    # Get all items in BASE_DIR
    items = os.listdir(BASE_DIR)
    
    for item in items:
        src_path = os.path.join(BASE_DIR, item)
        
        if item in IGNORE:
            continue
            
        if os.path.isdir(src_path):
            dst_path = os.path.join(PAGES_DIR, item)
            
            print(f"Moving {item} -> pages/{item}")
            
            if os.path.exists(dst_path):
                # Merge logic
                print(f"  Destination pages/{item} exists. Merging...")
                copy_tree(src_path, dst_path)
                shutil.rmtree(src_path)
            else:
                shutil.move(src_path, dst_path)

def copy_tree(src, dst):
    for item in os.listdir(src):
        s = os.path.join(src, item)
        d = os.path.join(dst, item)
        if os.path.isdir(s):
            shutil.copytree(s, d, dirs_exist_ok=True)
        else:
            if os.path.exists(d):
                 print(f"  [WARN] Overwriting {d}")
            shutil.copy2(s, d)

if __name__ == "__main__":
    cleanup()
