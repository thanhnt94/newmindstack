import subprocess
import os

commit = "45bc15601ced8f649dd2620d0f539508a0217598"
base_git_path = "mindstack_app/modules/learning/vocabulary/flashcard/templates/vocab_flashcard/individual/session"
target_dir = "mindstack_app/modules/learning/flashcard/templates/flashcard/individual/session/custom"

files = [
    "index.html",
    "_desktop.html",
    "_mobile.html",
    "_card_desktop.html",
    "_card_mobile.html",
    "_stats_desktop.html",
    "_stats_mobile.html"
]

for filename in files:
    git_path = f"{base_git_path}/{filename}"
    print(f"Restoring {filename}...")
    
    cmd = ["git", "show", f"{commit}:{git_path}"]
    result = subprocess.run(cmd, capture_output=True) # Binary output
    
    if result.returncode != 0:
        print(f"FAILED to get {filename}: {result.stderr.decode('utf-8', errors='ignore')}")
        continue
        
    content = result.stdout.decode('utf-8', errors='replace') # Decode as utf-8 (assuming source was utf-8)
    
    # Replace include paths
    # Old path style might vary slightly, but generally 'vocab_flashcard/individual/session/...'
    
    new_content = content.replace("vocab_flashcard/individual/session/", "flashcard/individual/session/custom/")
    
    target_path = os.path.join(target_dir, filename)
    with open(target_path, "w", encoding="utf-8") as f:
        f.write(new_content)
    print(f"Saved to {target_path}")

print("Done.")
