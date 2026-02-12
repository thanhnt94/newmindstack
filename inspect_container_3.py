
import sqlite3
import json

db_path = r"c:\Code\MindStack\database\mindstack_new.db"
conn = sqlite3.connect(db_path)
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

cursor.execute("SELECT container_id, title, settings FROM learning_containers WHERE container_id = 3;")
row = cursor.fetchone()

if row:
    print(f"--- Container {row['container_id']} ---")
    print(f"Title: {row['title']}")
    if row['settings']:
        try:
            settings = json.loads(row['settings'])
            print("Full Settings:")
            print(json.dumps(settings, indent=2, ensure_ascii=False))
        except:
            print(f"Raw Settings: {row['settings']}")
    else:
        print("Settings: None")

conn.close()
