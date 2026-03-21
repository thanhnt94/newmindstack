import os

repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
db_path = os.path.join(repo_root, 'database', 'watchtogether.sqlite')

print(f"Patching DB at: {db_path}")

from watchtogether.database import init_db, engine
from watchtogether.models import WTUser, WTRoom, WTSetting
import sqlite3

# Thêm cột is_admin nếu chưa có
try:
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("ALTER TABLE wt_users ADD COLUMN is_admin BOOLEAN DEFAULT 0;")
    conn.commit()
    conn.close()
    print("Column is_admin added successfully.")
except sqlite3.OperationalError as e:
    print(f"Error adding is_admin (maybe it exists): {e}")

# init_db() sẽ lệnh cho SQLAlchemy tạo bảng wt_settings vì metadata đã cập nhật
print("Running Base.metadata.create_all() ...")
init_db()
print("Done.")
