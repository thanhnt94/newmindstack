
import sqlite3
import json

db_path = r"c:\Code\MindStack\database\mindstack_new.db"
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

cursor.execute("SELECT container_id, title, settings FROM learning_containers WHERE title LIKE '%Mimi Kara%';")
rows = cursor.fetchall()

for row in rows:
    print(f"ID: {row[0]}")
    print(f"Title: {row[1]}")
    settings = row[2]
    if settings:
        try:
            settings_dict = json.loads(settings)
            print(f"Settings: {json.dumps(settings_dict, indent=2, ensure_ascii=False)}")
        except Exception as e:
            print(f"Raw Settings: {settings}")
            print(f"Error parsing: {e}")
    else:
        print("Settings: None")
    print("-" * 20)

# Also check UserContainerState
cursor.execute("SELECT user_id, container_id, settings FROM user_container_states WHERE container_id = ? LIMIT 5;", (rows[0][0] if rows else -1,))
ucs_rows = cursor.fetchall()

print("\nUser Container States:")
for row in ucs_rows:
    print(f"User: {row[0]}, Container: {row[1]}")
    ucs_settings = row[2]
    if ucs_settings:
        try:
            ucs_dict = json.loads(ucs_settings)
            print(f"UCS Settings: {json.dumps(ucs_dict, indent=2, ensure_ascii=False)}")
        except Exception as e:
            print(f"Raw UCS Settings: {ucs_settings}")
            print(f"Error parsing: {ucs_settings}")
    print("-" * 20)

conn.close()
