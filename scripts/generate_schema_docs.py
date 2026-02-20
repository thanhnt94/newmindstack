import os
import ast

def parse_model(filepath):
    models = []
    if not os.path.exists(filepath):
        return models
    
    with open(filepath, 'r', encoding='utf-8') as f:
        try:
            tree = ast.parse(f.read(), filename=filepath)
        except:
            return models
            
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                # Simple heuristic checks to see if this is an SQLAlchemy Model
                is_model = any(isinstance(base, ast.Attribute) and base.attr == 'Model' for base in node.bases)
                is_model = is_model or any(isinstance(base, ast.Name) and base.id == 'Model' for base in node.bases)
                
                # If there are db.Column assignments, we can usually assume it's a model
                cols = []
                for body_node in node.body:
                    if isinstance(body_node, ast.Assign) and len(body_node.targets) == 1:
                        target = body_node.targets[0]
                        if isinstance(target, ast.Name):
                            # Try to extract the column type if it's a db.Column call
                            col_info = ""
                            if isinstance(body_node.value, ast.Call):
                                if getattr(body_node.value.func, 'attr', '') == 'Column' or getattr(body_node.value.func, 'id', '') == 'Column':
                                    if body_node.value.args:
                                        arg = body_node.value.args[0]
                                        if isinstance(arg, ast.Attribute):
                                            col_info = arg.attr
                                        elif isinstance(arg, ast.Name):
                                            col_info = arg.id
                            
                            if col_info:
                                cols.append(f"- **`{target.id}`**: ({col_info})")
                            else:
                                # We can't safely extract type, just list the attribute
                                if 'Column' in ast.dump(body_node.value):
                                    cols.append(f"- **`{target.id}`**")
                
                if is_model or cols:
                    models.append({
                        'name': node.name,
                        'columns': cols
                    })
    return models

def main():
    app_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    modules_dir = os.path.join(app_dir, 'mindstack_app', 'modules')
    docs_dir = os.path.join(app_dir, 'docs')
    output_file = os.path.join(docs_dir, 'database_schema.md')
    
    schema_map = {}
    
    if os.path.exists(modules_dir):
        for module_name in os.listdir(modules_dir):
            if module_name.startswith('__'):
                continue
                
            models_file = os.path.join(modules_dir, module_name, 'models.py')
            module_models = parse_model(models_file)
            
            if module_models:
                schema_map[module_name] = module_models
                
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("# Tài liệu Cấu trúc Cơ sở dữ liệu MindStack (Auto-generated)\n\n")
        f.write("Tài liệu này liệt kê các Database Models và Columns, được trích xuất tự động qua AST từ tất cả `models.py`.\n\n")
        
        for module_name in sorted(schema_map.keys()):
            f.write(f"## Module: `{module_name}`\n\n")
            for model in schema_map[module_name]:
                f.write(f"### Model: `{model['name']}`\n")
                if model['columns']:
                    for col in model['columns']:
                        f.write(f"{col}\n")
                else:
                    f.write("- No parseable SQLAlchemy Columns found or standard attributes only.\n")
                f.write("\n")
                
        f.write("---\n*Note: Bảng này được sinh tự động. Có thể không đầy đủ kiểu dữ liệu phức tạp hoặc Relationship (FK).*")

    print(f"✅ Generated database schema documentation at {output_file}")

if __name__ == '__main__':
    main()
