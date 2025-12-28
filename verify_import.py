
import sys
import os

# Add the project root to sys.path
sys.path.insert(0, os.getcwd())

try:
    print("Attempting to import mindstack_app.modules.admin.routes...")
    from mindstack_app.modules.admin import routes
    print("Import successful!")
except ImportError as e:
    print(f"Import failed: {e}")
except Exception as e:
    print(f"An error occurred: {e}")
