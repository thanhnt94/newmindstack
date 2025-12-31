import os
import shutil

ROOT_DIR = os.path.join(os.getcwd(), 'mindstack_app', 'modules')

def delete_legacy_folders():
    print(f"Scanning {ROOT_DIR} for 'templates' and 'static' folders...")
    count = 0
    for root, dirs, files in os.walk(ROOT_DIR):
        # Modify dirs in-place to prune traversal if we delete a folder
        # But here we want to delete specific names
        
        targets = ['templates', 'static']
        for target in targets:
            if target in dirs:
                full_path = os.path.join(root, target)
                try:
                    print(f"Deleting: {full_path}")
                    shutil.rmtree(full_path)
                    dirs.remove(target) # Stop walking into deleted dir
                    count += 1
                except Exception as e:
                    print(f"Error deleting {full_path}: {e}")

    print(f"Deleted {count} legacy folders.")

if __name__ == "__main__":
    delete_legacy_folders()
