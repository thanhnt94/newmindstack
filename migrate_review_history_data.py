"""
Script to migrate existing review_history JSON data to review_logs table.
Run this directly: python migrate_review_history_data.py
"""
import sqlite3
import json
from datetime import datetime

db_path = r'C:\Code\MindStack\database\mindstack_new.db'

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

print("=== MIGRATE REVIEW HISTORY DATA ===\n")

# 1. Migrate flashcard_progress.review_history
print("--- Migrating flashcard_progress.review_history ---")
cursor.execute("""
    SELECT progress_id, user_id, item_id, review_history 
    FROM flashcard_progress 
    WHERE review_history IS NOT NULL AND review_history != '[]' AND review_history != 'null'
""")
fc_rows = cursor.fetchall()
print(f"Found {len(fc_rows)} records with review_history")

fc_migrated = 0
fc_skipped = 0

for row in fc_rows:
    progress_id, user_id, item_id, review_history_json = row
    
    try:
        history = json.loads(review_history_json) if review_history_json else []
    except json.JSONDecodeError:
        print(f"  ERROR: Invalid JSON for progress_id={progress_id}")
        continue
    
    if not history:
        continue
    
    for entry in history:
        if not isinstance(entry, dict):
            continue
        
        timestamp_str = entry.get('timestamp')
        quality = entry.get('user_answer_quality')
        source = entry.get('source', 'flashcard')
        mastery = entry.get('mastery')
        memory_power = entry.get('memory_power')
        
        # Skip preview entries (no quality)
        if quality is None:
            continue
        
        # Parse timestamp
        timestamp = None
        if timestamp_str:
            try:
                # Try parsing ISO format
                timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
            except:
                try:
                    timestamp = datetime.strptime(timestamp_str, "%Y-%m-%dT%H:%M:%S.%f")
                except:
                    pass
        
        # Check if already exists (avoid duplicates)
        cursor.execute("""
            SELECT log_id FROM review_logs 
            WHERE user_id = ? AND item_id = ? AND timestamp = ? AND rating = ?
        """, (user_id, item_id, timestamp.isoformat() if timestamp else None, quality))
        
        if cursor.fetchone():
            fc_skipped += 1
            continue
        
        # Insert into review_logs
        cursor.execute("""
            INSERT INTO review_logs (user_id, item_id, timestamp, rating, review_type, mastery_snapshot, memory_power_snapshot)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (user_id, item_id, timestamp, quality, source or 'flashcard', mastery, memory_power))
        fc_migrated += 1

print(f"  Migrated: {fc_migrated} entries")
print(f"  Skipped (duplicates): {fc_skipped}")

# 2. Migrate quiz_progress.review_history
print("\n--- Migrating quiz_progress.review_history ---")
cursor.execute("""
    SELECT progress_id, user_id, item_id, review_history 
    FROM quiz_progress 
    WHERE review_history IS NOT NULL AND review_history != '[]' AND review_history != 'null'
""")
qz_rows = cursor.fetchall()
print(f"Found {len(qz_rows)} records with review_history")

qz_migrated = 0
qz_skipped = 0

for row in qz_rows:
    progress_id, user_id, item_id, review_history_json = row
    
    try:
        history = json.loads(review_history_json) if review_history_json else []
    except json.JSONDecodeError:
        print(f"  ERROR: Invalid JSON for progress_id={progress_id}")
        continue
    
    if not history:
        continue
    
    for entry in history:
        if not isinstance(entry, dict):
            continue
        
        timestamp_str = entry.get('timestamp')
        user_answer = entry.get('user_answer')
        is_correct = entry.get('is_correct')
        score_change = entry.get('score_change')
        
        # Parse timestamp
        timestamp = None
        if timestamp_str:
            try:
                timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
            except:
                try:
                    timestamp = datetime.strptime(timestamp_str, "%Y-%m-%dT%H:%M:%S.%f")
                except:
                    pass
        
        # Check if already exists
        cursor.execute("""
            SELECT log_id FROM review_logs 
            WHERE user_id = ? AND item_id = ? AND timestamp = ? AND review_type = 'quiz'
        """, (user_id, item_id, timestamp.isoformat() if timestamp else None))
        
        if cursor.fetchone():
            qz_skipped += 1
            continue
        
        # Insert into review_logs
        rating = 1 if is_correct else 0
        cursor.execute("""
            INSERT INTO review_logs (user_id, item_id, timestamp, rating, review_type, user_answer, is_correct, score_change)
            VALUES (?, ?, ?, ?, 'quiz', ?, ?, ?)
        """, (user_id, item_id, timestamp, rating, user_answer, is_correct, score_change))
        qz_migrated += 1

print(f"  Migrated: {qz_migrated} entries")
print(f"  Skipped (duplicates): {qz_skipped}")

# Commit
conn.commit()

# Verify
cursor.execute("SELECT COUNT(*) FROM review_logs")
total_logs = cursor.fetchone()[0]
print(f"\n=== SUMMARY ===")
print(f"Total entries in review_logs: {total_logs}")
print(f"Flashcard entries migrated: {fc_migrated}")
print(f"Quiz entries migrated: {qz_migrated}")

conn.close()
print("\nDone!")
