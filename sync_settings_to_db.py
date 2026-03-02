import sqlite3
import os
import json

db_path = r"c:\Code\MindStack\database\mindstack_new.db"

new_defaults = {
    'SCORE_FSRS_AGAIN': 1,
    'SCORE_FSRS_HARD': 2,
    'SCORE_FSRS_GOOD': 4,
    'SCORE_FSRS_EASY': 7,
    'QUIZ_CORRECT_BONUS': 5,
    'QUIZ_FIRST_TIME_BONUS': 3,
    'VOCAB_MCQ_CORRECT_BONUS': 3,
    'VOCAB_TYPING_CORRECT_BONUS': 5,
    'VOCAB_MATCHING_CORRECT_BONUS': 1,
    'VOCAB_LISTENING_CORRECT_BONUS': 4,
    'VOCAB_SPEED_CORRECT_BONUS': 2
}

if not os.path.exists(db_path):
    print(f"Database not found at {db_path}")
    exit(1)

try:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    print("Updating app_settings with new defaults...")
    for key, val in new_defaults.items():
        # Using JSON format as expected by the model's value field
        cursor.execute("UPDATE app_settings SET value = ? WHERE key = ?", (val, key))
        if cursor.rowcount == 0:
            # If not exists, insert (optional but good for completeness)
            cursor.execute("INSERT INTO app_settings (key, value, category, data_type) VALUES (?, ?, 'scoring', 'int')", (key, val))
    
    conn.commit()
    print("Database updated successfully.")
    conn.close()
except Exception as e:
    print(f"Error: {e}")
    exit(1)
