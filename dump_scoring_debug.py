import sqlite3
import os
import json

db_path = r"c:\Code\MindStack\database\mindstack_new.db"

if not os.path.exists(db_path):
    print(f"Database not found at {db_path}")
    exit(1)

try:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    print("--- APP SETTINGS (scoring) ---")
    cursor.execute("SELECT key, value FROM app_settings WHERE category='scoring'")
    for row in cursor.fetchall():
        print(f"{row[0]}: {row[1]}")
    
    print("\n--- RECENT SCORE LOGS ---")
    cursor.execute("SELECT log_id, user_id, reason, score_change, meta FROM score_logs ORDER BY log_id DESC LIMIT 5")
    for row in cursor.fetchall():
        print(f"ID: {row[0]}, User: {row[1]}, Reason: {row[2]}, Change: {row[3]}, Meta: {row[4]}")
        
    conn.close()
except Exception as e:
    print(f"Error: {e}")
    exit(1)
