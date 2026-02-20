import os
import ast
import sys

# Add mindstack_app to path so we can resolve if needed
app_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
modules_dir = os.path.join(app_dir, 'mindstack_app', 'modules')

def get_module_name_from_path(filepath):
    # Extracts the module name from the filepath
    # e.g., mindstack_app/modules/auth/services/auth_service.py -> auth
    rel_path = os.path.relpath(filepath, modules_dir)
    parts = rel_path.split(os.sep)
    if len(parts) > 0:
        return parts[0]
    return None

def check_file(filepath):
    source_module = get_module_name_from_path(filepath)
    if not source_module:
        return []

    with open(filepath, 'r', encoding='utf-8') as f:
        try:
            content = f.read()
            tree = ast.parse(content, filename=filepath)
        except Exception as e:
            print(f"Error parsing {filepath}: {e}")
            return []

    violations = []
    
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                name = alias.name
                if name.startswith('mindstack_app.modules.'):
                    parts = name.split('.')
                    if len(parts) >= 4:
                        target_module = parts[2]
                        if target_module != source_module and parts[3] != 'interface':
                            if parts[3] != 'tests':
                                violations.append((node.lineno, name))
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                module = node.module
                level = node.level if node.level else 0
                
                full_module_name = ""
                if level > 0:
                    rel_path = os.path.relpath(os.path.dirname(filepath), modules_dir)
                    path_parts = rel_path.split(os.sep)
                    parent_parts = ['mindstack_app', 'modules'] + path_parts
                    
                    base_parts = parent_parts[:len(parent_parts) - level + 1]
                    full_module_name = '.'.join(base_parts)
                    if module:
                        full_module_name += '.' + module
                else:
                    full_module_name = module

                if full_module_name.startswith('mindstack_app.modules.'):
                    parts = full_module_name.split('.')
                    if len(parts) >= 3:
                        target_module = parts[2]
                        
                        if target_module != source_module:
                            is_violation = False
                            
                            if len(parts) == 3:
                                # from mindstack_app.modules.gamification import services
                                for alias in node.names:
                                    if alias.name != 'interface' and not alias.name.endswith('Interface'): 
                                        is_violation = True
                            elif len(parts) > 3:
                                # from mindstack_app.modules.vocabulary.flashcard.interface import ...
                                # Check if any part after the module name is 'interface'
                                if 'interface' not in parts[3:]:
                                    is_violation = True
                                    
                            if is_violation:
                                names_str = ", ".join(alias.name for alias in node.names)
                                import_str = f"from {full_module_name} import {names_str}"
                                violations.append((node.lineno, import_str))
                                
    return violations

def main():
    if not os.path.exists(modules_dir):
        print(f"Modules directory not found: {modules_dir}")
        return

    output = []
    total_violations = 0
    for root, _, files in os.walk(modules_dir):
        for file in files:
            if file.endswith('.py'):
                filepath = os.path.join(root, file)
                violations = check_file(filepath)
                if violations:
                    output.append(f"\n[{get_module_name_from_path(filepath)}] File: {os.path.relpath(filepath, app_dir)}")
                    for line, info in violations:
                        output.append(f"  Line {line}: {info}")
                    total_violations += len(violations)
                    
    output.append(f"\nTotal cross-module import violations found: {total_violations}")
    
    with open('check_results.txt', 'w', encoding='utf-8') as f:
        f.write('\n'.join(output))

if __name__ == '__main__':
    main()
