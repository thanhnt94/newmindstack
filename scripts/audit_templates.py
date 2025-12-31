import os

ROOT_DIR = r'c:\Code\MindStack\newmindstack\mindstack_app'

def audit_templates():
    print("Auditing templates...")
    modules_dir = os.path.join(ROOT_DIR, 'modules')
    
    template_dirs = []
    lines = []
    
    
    for root, dirs, files in os.walk(modules_dir):
        if 'templates' in dirs:
            template_path = os.path.join(root, 'templates')
            template_dirs.append(template_path)
            
            # Check contents
            lines.append(f"\nFound: {template_path}")
            # Calculate module name from path
            rel_path = os.path.relpath(root, modules_dir)
            module_name = rel_path.replace(os.sep, '.')
            lines.append(f"  Module: {module_name}")
            
            for t_root, t_dirs, t_files in os.walk(template_path):
                for f in t_files:
                    t_rel = os.path.relpath(os.path.join(t_root, f), template_path)
                    lines.append(f"    - {t_rel}")

    with open('audit_result.txt', 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))
    print("Audit saved to audit_result.txt")

if __name__ == '__main__':
    audit_templates()
