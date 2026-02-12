
import sqlite3
import json

db_path = r"c:\Code\MindStack\database\mindstack_new.db"
conn = sqlite3.connect(db_path)
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

cursor.execute("SELECT container_id, title, settings FROM learning_containers WHERE container_id = 3;")
row = cursor.fetchone()

if row:
    data = {
        "container_id": row['container_id'],
        "title": row['title'],
        "settings": json.loads(row['settings']) if row['settings'] else None
    }
    with open('container_3_settings.json', 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print("Exported to container_3_settings.json")

conn.close()
