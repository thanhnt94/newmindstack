import os
import subprocess

# Define configuration
commit_hash = "3a9889c6c8d792f2b93d5ad7e3c6da34c4f48076"
base_dest = os.path.join(os.getcwd(), "mindstack_app", "static", "flashcard")

# Only targeting the missing ones
files_to_restore = {
    "js": ["notes_feedback.js", "render_engine.js", "session_engine.js", "events.js"]
}

def load_legacy_paths():
    paths = []
    try:
        with open("all_files_legacy.txt", "r", encoding="utf-16") as f:
            paths = [line.strip() for line in f]
    except:
         with open("all_files_legacy.txt", "r", encoding="utf-8") as f:
            paths = [line.strip() for line in f]
    return paths

def restore_files():
    all_paths = load_legacy_paths()
    print(f"Loaded {len(all_paths)} paths from dump file.")
    
    print(f"Starting restoration to: {base_dest}")
    
    for sub_dir, filenames in files_to_restore.items():
        dest_dir = os.path.join(base_dest, sub_dir)
        os.makedirs(dest_dir, exist_ok=True)
        
        for filename in filenames:
            # SIMPLE MATCH: just check if filename is part of the path
            # But ensure it ends with the filename to avoid partial matches
            src_path = next((p for p in all_paths if p.endswith(f"/{filename}")), None)
            
            if not src_path:
                print(f"  [WARN] Strictly ending with /{filename} failed. Trying substring...")
                src_path = next((p for p in all_paths if filename in p), None)
            
            if not src_path:
                print(f"  [ERROR] Could not find ANY path for {filename} in dump file.")
                continue

            # Construct local destination path
            dest_path = os.path.join(dest_dir, filename)
            
            print(f"Processing {filename} from {src_path}...")
            
            # Execute git show
            cmd = ["git", "show", f"{commit_hash}:{src_path}"]
            try:
                result = subprocess.run(cmd, capture_output=True, text=True, check=False)
                
                if result.returncode == 0 and result.stdout:
                    # Write content to file
                    with open(dest_path, "w", encoding="utf-8") as f:
                        f.write(result.stdout)
                    
                    # Verify file size
                    size = os.path.getsize(dest_path)
                    print(f"  [OK] Wrote {size} bytes to {dest_path}")
                else:
                    print(f"  [ERROR] Git command failed or empty output.")
                    print(f"  Stderr: {result.stderr}")
            except Exception as e:
                print(f"  [EXCEPTION] {e}")

if __name__ == "__main__":
    restore_files()
