import os
import subprocess

# Define configuration
commit_hash = "3a9889c6c8d792f2b93d5ad7e3c6da34c4f48076"
base_dest = os.path.join(os.getcwd(), "mindstack_app", "static", "flashcard", "js")
base_src_path = "mindstack_app/modules/learning/flashcard/individual/templates/individual/cardsession/v2/js"

files_to_restore = ["session_engine.js", "render_engine.js", "events.js", "notes_feedback.js"]

def restore_files():
    print(f"Starting binary restoration to: {base_dest}")
    os.makedirs(base_dest, exist_ok=True)
    
    for filename in files_to_restore:
        src_path = f"{base_src_path}/{filename}"
        dest_path = os.path.join(base_dest, filename)
        
        print(f"Restoring {filename}...")
        
        # Execute git show, capture as binary
        cmd = ["git", "show", f"{commit_hash}:{src_path}"]
        try:
            # Capture as bytes!
            result = subprocess.run(cmd, capture_output=True, check=False)
            
            if result.returncode == 0 and result.stdout:
                # Write binary content to file
                with open(dest_path, "wb") as f:
                    f.write(result.stdout)
                
                size = os.path.getsize(dest_path)
                print(f"  [OK] Wrote {size} bytes to {dest_path}")
            else:
                print(f"  [ERROR] Git command failed.")
                print(f"  Stderr: {result.stderr.decode('utf-8', errors='ignore')}")
        except Exception as e:
            print(f"  [EXCEPTION] {e}")

if __name__ == "__main__":
    restore_files()
