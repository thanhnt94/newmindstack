
import pathlib

# Read paths
try:
    css_path = pathlib.Path('temp_css_path.txt').read_text(encoding='utf-16').strip().splitlines()[0]
except:
    css_path = pathlib.Path('temp_css_path.txt').read_text(encoding='utf-8', errors='ignore').strip().splitlines()[0]

try:
    js_paths = pathlib.Path('temp_js_paths.txt').read_text(encoding='utf-16').strip().splitlines()
except:
    js_paths = pathlib.Path('temp_js_paths.txt').read_text(encoding='utf-8', errors='ignore').strip().splitlines()

# Generate batch script
commands = []
commands.append(f'@echo off')
commands.append(f'git show 3a9889c6c8d792f2b93d5ad7e3c6da34c4f48076:{css_path} > session_single_legacy.css')

for i, js in enumerate(js_paths):
    target = f'legacy_js_{i}.js'
    commands.append(f'git show 3a9889c6c8d792f2b93d5ad7e3c6da34c4f48076:{js} > {target}')

pathlib.Path('restore_assets.bat').write_text('\n'.join(commands), encoding='utf-8')
print("restore_assets.bat created")
