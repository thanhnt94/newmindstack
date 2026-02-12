
import sqlite3
import json

db_path = r"c:\Code\MindStack\database\mindstack_new.db"
conn = sqlite3.connect(db_path)
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

cursor.execute("SELECT container_id, title, settings FROM learning_containers WHERE title LIKE '%N2%';")
rows = cursor.fetchall()

if rows:
    for row in rows:
        print(f"--- Container {row['container_id']} ---")
        print(f"Title: {row['title']}")
        if row['settings']:
            try:
                settings = json.loads(row['settings'])
                print("MCQ Settings:")
                print(json.dumps(settings.get('mcq', {}), indent=2, ensure_ascii=False))
            except:
                print(f"Raw Settings: {row['settings']}")
        else:
            print("Settings: None")

cursor.execute("SELECT user_id, container_id, settings FROM user_container_states WHERE container_id = 1 AND user_id = 2;")
row = cursor.fetchone()
if row:
    print(f"\n--- User Container State (User 2, Container 1) ---")
    try:
        settings = json.loads(row['settings'])
        print("MCQ Settings in UCS:")
        print(json.dumps(settings.get('mcq', {}), indent=2, ensure_ascii=False))
    except:
        print(f"Raw UCS settings: {row['settings']}")

conn.close()
