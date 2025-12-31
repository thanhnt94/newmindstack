import os
import py_compile

def check_syntax(root_dir):
    for dirpath, dirnames, filenames in os.walk(root_dir):
        if 'venv' in dirpath or '.git' in dirpath or '__pycache__' in dirpath:
            continue
        for filename in filenames:
            if filename.endswith('.py'):
                path = os.path.join(dirpath, filename)
                try:
                    py_compile.compile(path, doraise=True)
                except py_compile.PyCompileError as e:
                    print(f"Syntax Error in {path}:")
                    print(e)
                except Exception as e:
                    print(f"Error checking {path}: {e}")

if __name__ == "__main__":
    check_syntax("c:/Code/MindStack/newmindstack/mindstack_app")
