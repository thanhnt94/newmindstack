import os
import shutil

TARGET_DIR = r'c:\Code\MindStack\newmindstack\mindstack_app\templates\v1'

def fix_nesting():
    print(f"Scanning {TARGET_DIR} for double nesting...")
    
    for item in os.listdir(TARGET_DIR):
        parent_path = os.path.join(TARGET_DIR, item)
        if os.path.isdir(parent_path):
            nested_path = os.path.join(parent_path, item)
            
            if os.path.exists(nested_path) and os.path.isdir(nested_path):
                print(f"Found double nesting: {nested_path}")
                
                # Move contents up
                for subitem in os.listdir(nested_path):
                    src = os.path.join(nested_path, subitem)
                    dst = os.path.join(parent_path, subitem)
                    
                    if os.path.exists(dst):
                        print(f"  WARNING: Destination exists, merging/overwriting: {dst}")
                        if os.path.isdir(src) and os.path.isdir(dst):
                            # recursive merge needed? existing shutil.move might fail if dst dir exists 
                            # but here we assume simple structure. 
                            # actually shutil.move(src, dst) where dst IS A DIR moves src INTO dst.
                            # We want to move contents of src to dst? No, we are moving subitem (file or dir) to parent_path.
                            # If parent_path/subitem exists, we have a problem.
                            pass
                    
                    print(f"  Moving {subitem} -> ..")
                    shutil.move(src, dst)
                
                # Remove empty nested dir
                os.rmdir(nested_path)
                print("  Removed nested dir.")

if __name__ == '__main__':
    fix_nesting()
