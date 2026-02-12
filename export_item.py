
import sqlite3
import json

db_path = r"c:\Code\MindStack\database\mindstack_new.db"
conn = sqlite3.connect(db_path)
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

cursor.execute("SELECT * FROM learning_items WHERE container_id = 3 LIMIT 1;")
row = cursor.fetchone()

if row:
    result = dict(row)
    result['content'] = json.loads(row['content'])
    result['custom_data'] = json.loads(row['custom_data']) if row['custom_data'] else None
    
    with open('item_sample.json', 'w', encoding='utf-8') as f:
        json.dump(result, f, indent=2, ensure_ascii=False)
    print("Exported to item_sample.json")

conn.close()
