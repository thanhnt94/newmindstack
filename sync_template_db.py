from mindstack_app import create_app
from mindstack_app.models import AppSettings, db

def sync_db():
    app = create_app()
    with app.app_context():
        key = "global_template_version"
        setting = AppSettings.query.get(key)
        if setting:
            print(f"Updating {key} from {setting.value} to aora")
            setting.value = 'aora'
        else:
            print(f"Creating {key} with value aora")
            setting = AppSettings(
                key=key, 
                value='aora', 
                category='template', 
                data_type='string', 
                description='Global Interface Version'
            )
            db.session.add(setting)
        
        db.session.commit()
    print("Database sync complete.")

if __name__ == "__main__":
    sync_db()
