"""Simple test"""
import sys
sys.path.insert(0, 'c:/Code/MindStack/newmindstack')

try:
    from mindstack_app.modules.learning import learning_bp
    print("✓ Import OK")
    print(f"learning_bp name: {learning_bp.name}")
    print(f"learning_bp url_prefix: {learning_bp.url_prefix}")
    
    # Check registered blueprints
    if hasattr(learning_bp, 'blueprints'):
        print(f"\nRegistered sub-blueprints:")
        for name, bp in learning_bp.blueprints.items():
            print(f"  - {name}")
    
except Exception as e:
    print(f"✗ Error: {e}")
    import traceback
    traceback.print_exc()
