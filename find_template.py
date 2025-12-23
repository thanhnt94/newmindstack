import subprocess

commit = "45bc15601ced8f649dd2620d0f539508a0217598"
base = "mindstack_app/modules/learning/vocabulary/flashcard"
possibilities = [
    f"{base}/templates/flashcard/session.html",
    f"{base}/templates/vocab_flashcard/session.html",
    f"{base}/templates/session.html",
    f"{base}/templates/flashcard/index.html",
    f"{base}/templates/vocab_flashcard/index.html",
    f"{base}/templates/index.html",
    "mindstack_app/modules/learning/vocabulary/flashcard/templates/vocab_flashcard/session.html",
    "mindstack_app/modules/learning/vocabulary/flashcard/templates/vocab_flashcard/index.html",
    "mindstack_app/modules/learning/vocabulary/flashcard/templates/flashcard/session.html", 
    "mindstack_app/modules/learning/vocabulary/templates/vocab_flashcard/session.html",
    "mindstack_app/modules/learning/vocabulary/templates/vocab_flashcard/index.html",
    "mindstack_app/modules/learning/vocabulary/templates/vocabulary/flashcard/session.html",
    "mindstack_app/modules/learning/vocabulary/templates/vocabulary/session.html",
    "mindstack_app/modules/learning/vocabulary/vocab_flashcard/templates/session.html"
]

found = False
for p in possibilities:
    print(f"Trying {p}...")
    try:
        # Use shell=True for windows command parsing if needed, but list args is safer
        # git show on windows might need shell=True or careful quoting? 
        # But subprocess.run with list should be fine.
        cmd = ["git", "show", f"{commit}:{p}"]
        result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='ignore')
        
        if result.returncode == 0:
            print(f"FOUND: {p}")
            with open("restored_template.html", "w", encoding="utf-8") as f:
                f.write(result.stdout)
            print("Saved to restored_template.html")
            found = True
            break
        else:
             print(f"Failed: {result.stderr.strip()[:100]}")
    except Exception as e:
        print(f"Error: {e}")

if not found:
    print("Not found in any guessed paths.")
