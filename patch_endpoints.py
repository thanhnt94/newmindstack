import os

target_dir = "mindstack_app/modules/learning/flashcard/templates/flashcard/individual/session/custom"
old_endpoint = "learning.vocabulary.vocab_flashcard."
new_endpoint = "learning.flashcard_learning."

for filename in os.listdir(target_dir):
    filepath = os.path.join(target_dir, filename)
    if not filename.endswith(".html"): 
        continue
        
    print(f"Patching {filename}...")
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()
        
    new_content = content.replace(old_endpoint, new_endpoint)
    
    if content != new_content:
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(new_content)
        print(f"UPDATED {filename}")
    else:
        print(f"No changes in {filename}")

print("Done patching endpoints.")
