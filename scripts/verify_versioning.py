import os
import sys

# Add project root to path
sys.path.insert(0, os.path.abspath('c:/Code/MindStack/newmindstack'))

from mindstack_app import create_app
from mindstack_app.services.template_service import TemplateService

def verify():
    app = create_app()
    with app.app_context():
        print("Verifying TemplateService...")
        
        # 1. Check Default Version
        version = TemplateService.get_active_global_version()
        print(f"Active Global Version: {version}")
        assert version in ['v1', 'v2'], f"Unexpected version: {version}"
        
        # 2. List Available Versions
        available = TemplateService.list_available_versions()
        print(f"Available Versions: {available}")
        assert 'v1' in available, "v1 should be available"
        
        # 3. Test render_template wrapper logic (mock)
        # We can't easily mock render_template call without full request, 
        # but we can verify importing it works
        from mindstack_app.core.templating import render_template
        print("Successfully imported mindstack_app.core.templating.render_template")
        
        print("VERIFICATION SUCCESSFUL")

if __name__ == "__main__":
    verify()
