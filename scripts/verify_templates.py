
import os
import sys
from flask import Flask

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from mindstack_app import create_app
from mindstack_app.services.template_service import TemplateService

def verify_templates():
    app = create_app()
    with app.app_context():
        print("Starting Template Verification...")
        
        all_settings = TemplateService.get_all_template_settings()
        errors = []
        
        DEFAULT_FILENAMES = {
            'user_profile': 'profile.html',
            'auth.login': 'login.html', 
            'course.dashboard': 'course_learning_dashboard.html',
            'course.detail': 'course_session.html', 
            'collab.dashboard': 'dashboard.html',
            'vocabulary.detail': 'detail.html',
            'vocabulary.dashboard': 'dashboard.html',
        }

        for template_type, settings in all_settings.items():
            active_version = settings['active']
            available_versions = settings['options']
            
            check_filename = DEFAULT_FILENAMES.get(template_type, 'index.html')
            
            # Check ALL versions
            versions_to_check = set(available_versions)
            versions_to_check.add(active_version)
            versions_to_check.add('v2') # Explicitly check v2 as user reported issues
            
            for version in versions_to_check:
                if not version: continue
                
                print(f"Checking {template_type} (Version: {version}, File: {check_filename})...")
                
                try:
                    # Flask templates are usually relative to the blueprint's template folder or app's template folder.
                    folder_path = TemplateService.TEMPLATE_MAPPING.get(template_type)
                    if not folder_path:
                         print(f"  [SKIP] No folder path mapped for {template_type}")
                         continue

                    module_name = folder_path.split('/')[0]
                    
                    found = False
                    for blueprint_name, blueprint in app.blueprints.items():
                        if module_name in blueprint_name and blueprint.template_folder:
                            
                            # blueprint.template_folder is relative to blueprint.root_path
                            abs_template_folder = os.path.join(blueprint.root_path, blueprint.template_folder)
                            
                            # Standard path: .../templates/<folder_path>/<version>/<filename>
                            full_path_standard = os.path.join(abs_template_folder, folder_path, version, check_filename)
                            
                            # Flattened path: .../templates/<version>/<filename>
                            full_path_flat = os.path.join(abs_template_folder, version, check_filename)

                            if os.path.exists(full_path_standard):
                                found = True
                                print(f"  [OK] Found at standard path: {full_path_standard}")
                                break
                            elif os.path.exists(full_path_flat):
                                 found = True
                                 print(f"  [OK] Found at flattened path: {full_path_flat}")
                                 break
                    
                    if not found:
                        msg = f"  [MISSING] Could not find '{check_filename}' for version '{version}' of '{template_type}'"
                        print(msg)
                        errors.append(msg)

                except Exception as e:
                    msg = f"  [ERROR] checking {template_type} version {version}: {e}"
                    print(msg)
                    errors.append(msg)

        print("-" * 30)
        if errors:
            print(f"Found {len(errors)} errors:")
            for err in errors:
                print(err)
            sys.exit(1)
        else:
            print("All active templates verified successfully!")
            sys.exit(0)

if __name__ == "__main__":
    verify_templates()
