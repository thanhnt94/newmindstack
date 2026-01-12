from mindstack_app import create_app, db
from mindstack_app.models import AppSettings

app = create_app()

with app.app_context():
    print("Checking current template version setting...")
    setting = AppSettings.query.get('global_template_version')
    if setting:
        print(f"Current setting: {setting.value}")
        setting.value = 'v4'
        print("Updated to: v4")
    else:
        print("Setting not found. Creating new setting...")
        setting = AppSettings(key='global_template_version', value='v4', category='template', data_type='string', description='Global Interface Version')
        db.session.add(setting)
        print("Created new setting: v4")
    
    db.session.commit()
    print("Database updated successfully.")
