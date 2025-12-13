from mindstack_app.db_instance import db
from mindstack_app.models import SystemSetting
from mindstack_app import create_app

app = create_app()

with app.app_context():
    # Check if setting exists
    setting = SystemSetting.query.filter_by(key='telegram_bot_username').first()
    if not setting:
        print("Creating telegram_bot_username setting...")
        new_setting = SystemSetting(key='telegram_bot_username', value='MindStackBot', description='Username của Telegram Bot (không có @)')
        db.session.add(new_setting)
        db.session.commit()
        print("Done. Default value is 'MindStackBot'. Please update it in Admin Panel if your bot name is different.")
    else:
        print(f"Setting exists. Current value: {setting.value}")
