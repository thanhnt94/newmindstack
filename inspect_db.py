
import json
import sqlite3
import os

db_path = r'c:\Code\MindStack\database\mindstack_new.db'
if not os.path.exists(db_path):
    print(f"DB not found at {db_path}")
    exit(1)

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Get some sample items for container_id = 1 (based on previous logs)
cursor.execute("SELECT item_id, content, custom_data FROM learning_items LIMIT 5")
rows = cursor.fetchall()

data = []
for row in rows:
    data.append({
        'id': row[0],
        'content': json.loads(row[1]) if row[1] else None,
        'custom_data': json.loads(row[2]) if row[2] else None
    })

print(json.dumps(data, indent=2, ensure_ascii=False))
conn.close()
