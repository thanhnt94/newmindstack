from mindstack_app import create_app
from mindstack_app.models import AppSettings, db
from sqlalchemy import text
import json

def deep_inspect():
    app = create_app()
    with app.app_context():
        # 1. Query via SQLAlchemy model
        key = "global_template_version"
        setting = AppSettings.query.get(key)
        if setting:
            print(f"ORM: key='{setting.key}', value='{setting.value}', type={type(setting.value)}, repr={repr(setting.value)}")
        else:
            print("ORM: key not found")
            
        # 2. Query via raw SQL to check for duplicates or case sensitivity
        # Note: AppSettings has no 'id' column, 'key' is PK.
        result = db.session.execute(text("SELECT key, value FROM app_settings WHERE key LIKE :key"), {"key": f"%{key}%"})
        rows = result.fetchall()
        print(f"RAW SQL: Found {len(rows)} matching rows")
        for row in rows:
            val_raw = row[1]
            print(f"  Key: '{row[0]}', Value: '{val_raw}', type={type(val_raw)}, repr={repr(val_raw)}")

if __name__ == "__main__":
    deep_inspect()
