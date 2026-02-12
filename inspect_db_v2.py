
import json
import sqlite3
import os

db_path = r'c:\Code\MindStack\database\mindstack_new.db'
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

container_id = 1
cursor.execute("SELECT item_id, item_type, content, custom_data FROM learning_items WHERE container_id = ? LIMIT 20", (container_id,))
rows = cursor.fetchall()

print(f"Items found for container {container_id}: {len(rows)}")
for row in rows:
    item_id, item_type, content_json, custom_data_json = row
    content = json.loads(content_json) if content_json else {}
    custom_data = json.loads(custom_data_json) if custom_data_json else {}
    print(f"Item {item_id} ({item_type}):")
    print(f"  Content keys: {list(content.keys())}")
    print(f"  Custom Data keys: {list(custom_data.keys())}")

conn.close()
