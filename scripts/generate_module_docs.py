import os
import ast

def get_module_name(path, modules_dir):
    try:
        rel = os.path.relpath(path, modules_dir)
        return rel.split(os.sep)[0]
    except ValueError:
        return None

def extract_interfaces(filepath):
    """Find functions/classes defined in interface.py"""
    exports = []
    if not os.path.exists(filepath):
        return exports
    with open(filepath, 'r', encoding='utf-8') as f:
        try:
            tree = ast.parse(f.read(), filename=filepath)
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef) or isinstance(node, ast.AsyncFunctionDef):
                    if not node.name.startswith('_'):
                        exports.append(f"Function: `{node.name}`")
                elif isinstance(node, ast.ClassDef):
                    if not node.name.startswith('_'):
                        methods = [n.name for n in node.body if isinstance(n, ast.FunctionDef) and not n.name.startswith('_')]
                        exports.append(f"Class: `{node.name}` (Methods: {', '.join(methods)})")
        except:
            pass
    return exports

def extract_signals(filepath):
    """Find signals defined in signals.py"""
    signals = []
    if not os.path.exists(filepath):
        return signals
    with open(filepath, 'r', encoding='utf-8') as f:
        try:
            tree = ast.parse(f.read(), filename=filepath)
            for node in ast.walk(tree):
                if isinstance(node, ast.Assign):
                    for target in node.targets:
                        if isinstance(target, ast.Name):
                            signals.append(f"`{target.id}`")
        except:
            pass
    return signals

def scan_module_ast(module_path, module_name, modules_dir):
    dependencies = set()
    listened_events = []
    emitted_signals = []
    models = []
    
    for root, _, files in os.walk(module_path):
        for file in files:
            if not file.endswith('.py'):
                continue
            filepath = os.path.join(root, file)
            with open(filepath, 'r', encoding='utf-8') as f:
                try:
                    tree = ast.parse(f.read(), filename=filepath)
                except:
                    continue
                
                # Check imports for dependencies
                for node in ast.walk(tree):
                    if isinstance(node, ast.Import):
                        for alias in node.names:
                            if alias.name.startswith('mindstack_app.modules.'):
                                parts = alias.name.split('.')
                                if len(parts) >= 3 and parts[2] != module_name:
                                    dependencies.add(parts[2])
                    elif isinstance(node, ast.ImportFrom):
                        module = node.module or ''
                        level = node.level if node.level else 0
                        full_module = ""
                        if level > 0:
                            rel_path = os.path.relpath(root, modules_dir)
                            path_parts = rel_path.split(os.sep)
                            parent_parts = ['mindstack_app', 'modules'] + path_parts
                            base_parts = parent_parts[:len(parent_parts) - level + 1]
                            full_module = '.'.join(base_parts)
                            if module: full_module += '.' + module
                        else:
                            full_module = module

                        if full_module.startswith('mindstack_app.modules.'):
                            parts = full_module.split('.')
                            if len(parts) >= 3 and parts[2] != module_name:
                                dependencies.add(parts[2])

                    # Check for signal emissions .send(
                    if isinstance(node, ast.Call):
                        if isinstance(node.func, ast.Attribute) and node.func.attr == 'send':
                            if isinstance(node.func.value, ast.Name):
                                emitted_signals.append(f"`{node.func.value.id}.send(...)` in `{file}`")

                    # Check for event listeners @signal.connect
                    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        for dec in node.decorator_list:
                            if isinstance(dec, ast.Call) and isinstance(dec.func, ast.Attribute):
                                if dec.func.attr == 'connect':
                                    if isinstance(dec.func.value, ast.Name):
                                        listened_events.append(f"Listens to `{dec.func.value.id}` -> via `{node.name}` in `{file}`")
                                        
                # Check models
                if file == 'models.py':
                    for node in ast.walk(tree):
                        if isinstance(node, ast.ClassDef):
                            models.append(f"`{node.name}`")
                            
    return list(dependencies), list(set(listened_events)), list(set(emitted_signals)), list(set(models))


def main():
    app_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    modules_dir = os.path.join(app_dir, 'mindstack_app', 'modules')
    docs_dir = os.path.join(app_dir, 'docs', 'module_dependencies')
    
    if not os.path.exists(docs_dir):
        os.makedirs(docs_dir)

    modules = [d for d in os.listdir(modules_dir) if os.path.isdir(os.path.join(modules_dir, d)) and not d.startswith('__')]
    
    for module_name in modules:
        module_path = os.path.join(modules_dir, module_name)
        
        interfaces = extract_interfaces(os.path.join(module_path, 'interface.py'))
        signals_def = extract_signals(os.path.join(module_path, 'signals.py'))
        deps, listens, emits, models = scan_module_ast(module_path, module_name, modules_dir)
        
        md_path = os.path.join(docs_dir, f"{module_name}.md")
        with open(md_path, 'w', encoding='utf-8') as f:
            f.write(f"# 📦 Module: `{module_name}`\n\n")
            f.write(f"This document outlines the dependencies and relationships of the `{module_name}` module based on Hexagonal Architecture.\n\n")
            
            f.write("## 🔗 Dependencies (Consumes)\n")
            if deps:
                for d in sorted(deps):
                    f.write(f"- `{d}`\n")
            else:
                f.write("- None (Independent Module)\n")
            f.write("\n")
            
            f.write("## 🚪 Public Interface (Exports)\n")
            f.write("*These are the endpoints exposed via `interface.py` for other modules to use.*\n")
            if interfaces:
                for i in sorted(interfaces):
                    f.write(f"- {i}\n")
            else:
                f.write("- No public interface defined.\n")
            f.write("\n")
            
            f.write("## 📡 Signals (Defines/Emits)\n")
            if signals_def:
                f.write("**Defined Signals:**\n")
                for s in sorted(signals_def):
                    f.write(f"- {s}\n")
            if emits:
                f.write("\n**Emitted Events:**\n")
                for e in sorted(emits):
                    f.write(f"- {e}\n")
            if not signals_def and not emits:
                f.write("- None.\n")
            f.write("\n")
            
            f.write("## 🎧 Event Listeners\n")
            if listens:
                for l in sorted(listens):
                    f.write(f"- {l}\n")
            else:
                f.write("- None.\n")
            f.write("\n")
            
            f.write("## 💾 Database Models\n")
            if models:
                for m in sorted(models):
                    f.write(f"- {m}\n")
            else:
                f.write("- No dedicated models found.\n")
            
    print(f"✅ Generated connection docs for {len(modules)} modules in {docs_dir}")

if __name__ == '__main__':
    main()
