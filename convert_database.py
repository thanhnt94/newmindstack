import sqlite3
import json
from datetime import datetime, timezone

def convert_database(old_db_path, new_db_path):
    """
    Chuyển đổi dữ liệu từ database của mindstack (cũ) sang newmindstack (mới).
    Phiên bản cuối cùng: Sửa lỗi cấu trúc bảng quiz_progress và các lỗi liên quan.
    """
    try:
        old_conn = sqlite3.connect(old_db_path)
        old_cursor = old_conn.cursor()

        new_conn = sqlite3.connect(new_db_path)
        new_cursor = new_conn.cursor()

        print("Đã kết nối thành công đến 2 database.")

        # --- TẠO CÁC BẢNG (ĐÃ SỬA LẠI CẤU TRÚC QUIZ_PROGRESS) ---
        
        # Bảng users
        new_cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT(80) UNIQUE NOT NULL,
                email TEXT(120) UNIQUE NOT NULL,
                password_hash TEXT(256) NOT NULL,
                user_role TEXT(50) NOT NULL DEFAULT 'user',
                total_score INTEGER DEFAULT 0,
                last_seen DATETIME,
                current_flashcard_container_id INTEGER,
                current_quiz_container_id INTEGER,
                current_course_container_id INTEGER,
                current_flashcard_mode TEXT(50),
                current_quiz_mode TEXT(50),
                current_quiz_batch_size INTEGER,
                flashcard_button_count INTEGER DEFAULT 3
            )
        ''')

        # Bảng learning_containers
        new_cursor.execute('''
            CREATE TABLE IF NOT EXISTS learning_containers (
                container_id INTEGER PRIMARY KEY AUTOINCREMENT,
                creator_user_id INTEGER NOT NULL,
                container_type TEXT(50) NOT NULL,
                title TEXT(255) NOT NULL,
                description TEXT,
                tags TEXT(255),
                is_public BOOLEAN NOT NULL DEFAULT 0,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME,
                ai_settings TEXT,
                FOREIGN KEY (creator_user_id) REFERENCES users (user_id)
            )
        ''')

        # Bảng learning_items
        new_cursor.execute('''
            CREATE TABLE IF NOT EXISTS learning_items (
                item_id INTEGER PRIMARY KEY AUTOINCREMENT,
                container_id INTEGER NOT NULL,
                group_id INTEGER,
                item_type TEXT(50) NOT NULL,
                content TEXT NOT NULL,
                order_in_container INTEGER DEFAULT 0,
                ai_explanation TEXT,
                FOREIGN KEY (container_id) REFERENCES learning_containers (container_id)
            )
        ''')

        # Bảng flashcard_progress
        new_cursor.execute('''
            CREATE TABLE IF NOT EXISTS flashcard_progress (
                progress_id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                item_id INTEGER NOT NULL,
                due_time DATETIME,
                easiness_factor REAL DEFAULT 2.5,
                repetitions INTEGER DEFAULT 0,
                interval INTEGER DEFAULT 0,
                last_reviewed DATETIME,
                status TEXT(50) DEFAULT 'new',
                times_correct INTEGER DEFAULT 0,
                times_incorrect INTEGER DEFAULT 0,
                times_vague INTEGER DEFAULT 0,
                correct_streak INTEGER DEFAULT 0,
                incorrect_streak INTEGER DEFAULT 0,
                vague_streak INTEGER DEFAULT 0,
                first_seen_timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                review_history TEXT,
                FOREIGN KEY (user_id) REFERENCES users (user_id),
                FOREIGN KEY (item_id) REFERENCES learning_items (item_id)
            )
        ''')
        
        # Bảng user_container_states
        new_cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_container_states (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                container_id INTEGER NOT NULL,
                is_archived BOOLEAN NOT NULL DEFAULT 0,
                is_favorite BOOLEAN NOT NULL DEFAULT 0,
                last_accessed DATETIME,
                UNIQUE(user_id, container_id)
            )
        ''')
        
        # Bảng quiz_progress (ĐÃ SỬA LẠI HOÀN TOÀN CẤU TRÚC CHO ĐÚNG)
        new_cursor.execute('''
            CREATE TABLE IF NOT EXISTS quiz_progress (
                progress_id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                item_id INTEGER NOT NULL,
                times_correct INTEGER DEFAULT 0,
                times_incorrect INTEGER DEFAULT 0,
                correct_streak INTEGER DEFAULT 0,
                incorrect_streak INTEGER DEFAULT 0,
                last_reviewed DATETIME,
                status TEXT(50) DEFAULT 'new',
                first_seen_timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                review_history TEXT,
                UNIQUE(user_id, item_id)
            )
        ''')

        print("Đã tạo các bảng cần thiết trong database mới (đã sửa lỗi cấu trúc Quiz).")
        new_conn.commit()

        # --- CHUYỂN ĐỔI DỮ LIỆU ---
        
        # 1. Chuyển đổi Users và tạo bản đồ ID
        print("\nBắt đầu chuyển đổi bảng Users...")
        user_id_map = {}
        old_cursor.execute("SELECT user_id, username, user_role, score, password FROM Users")
        users = old_cursor.fetchall()
        for user in users:
            old_user_id, username, user_role, score, password = user
            email = f"{username}@example.com" if '@' not in username else username
            new_cursor.execute(
                "INSERT INTO users (username, email, user_role, total_score, password_hash, last_seen) VALUES (?, ?, ?, ?, ?, ?)",
                (username, email, user_role, score, password, datetime.now(timezone.utc).isoformat())
            )
            new_user_id = new_cursor.lastrowid
            user_id_map[old_user_id] = new_user_id
        print(f"-> Đã chuyển đổi {len(users)} người dùng.")
        new_conn.commit()

        # 2. Chuyển đổi VocabularySets (Flashcard)
        print("\nBắt đầu chuyển đổi VocabularySets (Flashcard)...")
        flashcard_set_id_map = {}
        old_cursor.execute("SELECT set_id, creator_user_id, title, description, tags, is_public, creation_date FROM VocabularySets")
        flashcard_sets = old_cursor.fetchall()
        for old_set in flashcard_sets:
            old_creator_id = old_set[1]
            new_creator_id = user_id_map.get(old_creator_id)
            if new_creator_id is None: continue
            new_cursor.execute(
                "INSERT INTO learning_containers (creator_user_id, container_type, title, description, tags, is_public, created_at) VALUES (?, 'FLASHCARD_SET', ?, ?, ?, ?, ?)",
                (new_creator_id, old_set[2], old_set[3], old_set[4], old_set[5], old_set[6])
            )
            new_set_id = new_cursor.lastrowid
            flashcard_set_id_map[old_set[0]] = new_set_id
        print(f"-> Đã chuyển đổi {len(flashcard_sets)} bộ flashcard.")
        new_conn.commit()
        
        # 3. Chuyển đổi QuestionSets (Quiz)
        print("\nBắt đầu chuyển đổi QuestionSets (Quiz)...")
        quiz_set_id_map = {}
        old_cursor.execute("SELECT set_id, creator_user_id, title, description, is_public, creation_date FROM QuestionSets")
        quiz_sets = old_cursor.fetchall()
        for old_set in quiz_sets:
            old_creator_id = old_set[1]
            new_creator_id = user_id_map.get(old_creator_id)
            if new_creator_id is None: continue
            new_cursor.execute(
                "INSERT INTO learning_containers (creator_user_id, container_type, title, description, is_public, created_at) VALUES (?, 'QUIZ_SET', ?, ?, ?, ?)",
                (new_creator_id, old_set[2], old_set[3], old_set[4], old_set[5])
            )
            new_set_id = new_cursor.lastrowid
            quiz_set_id_map[old_set[0]] = new_set_id
        print(f"-> Đã chuyển đổi {len(quiz_sets)} bộ quiz.")
        new_conn.commit()
        
        # 4. Chuyển đổi Flashcards
        print("\nBắt đầu chuyển đổi Flashcards...")
        flashcard_id_map = {}
        old_cursor.execute("SELECT flashcard_id, set_id, front, back FROM Flashcards")
        flashcards = old_cursor.fetchall()
        for old_card in flashcards:
            old_set_id = old_card[1]
            if old_set_id in flashcard_set_id_map:
                new_container_id = flashcard_set_id_map[old_set_id]
                content = {'front': old_card[2], 'back': old_card[3]}
                new_cursor.execute("INSERT INTO learning_items (container_id, item_type, content) VALUES (?, 'FLASHCARD', ?)", (new_container_id, json.dumps(content)))
                new_item_id = new_cursor.lastrowid
                flashcard_id_map[old_card[0]] = new_item_id
        print(f"-> Đã chuyển đổi {len(flashcards)} flashcards.")
        new_conn.commit()

        # 5. Chuyển đổi QuizQuestions
        print("\nBắt đầu chuyển đổi QuizQuestions...")
        quiz_question_id_map = {}
        old_cursor.execute("SELECT question_id, set_id, question, option_a, option_b, option_c, option_d, correct_answer, guidance FROM QuizQuestions")
        questions = old_cursor.fetchall()
        for old_q in questions:
            old_set_id = old_q[1]
            if old_set_id in quiz_set_id_map:
                new_container_id = quiz_set_id_map[old_set_id]
                content = {
                    'question': old_q[2],
                    'options': {'A': old_q[3], 'B': old_q[4], 'C': old_q[5], 'D': old_q[6]},
                    'correct_answer': old_q[7],
                    'explanation': old_q[8]
                }
                new_cursor.execute("INSERT INTO learning_items (container_id, item_type, content) VALUES (?, 'QUIZ_MCQ', ?)", (new_container_id, json.dumps(content)))
                new_item_id = new_cursor.lastrowid
                quiz_question_id_map[old_q[0]] = new_item_id
        print(f"-> Đã chuyển đổi {len(questions)} câu hỏi quiz.")
        new_conn.commit()

        # 6. Chuyển đổi UserFlashcardProgress và UserQuizProgress
        print("\nBắt đầu chuyển đổi tiến độ học tập...")
        processed_user_container_pairs = set()

        # Xử lý Flashcard
        old_cursor.execute("SELECT user_id, flashcard_id, due_time, review_count, learned_date FROM UserFlashcardProgress")
        flashcard_progress_data = old_cursor.fetchall()
        for old_progress in flashcard_progress_data:
            old_user_id, old_card_id, due_time_ts, review_count, learned_date = old_progress
            new_user_id = user_id_map.get(old_user_id)
            new_item_id = flashcard_id_map.get(old_card_id)
            
            if new_user_id and new_item_id:
                due_time_iso = datetime.fromtimestamp(due_time_ts, tz=timezone.utc).isoformat() if due_time_ts else None
                new_cursor.execute(
                    "INSERT INTO flashcard_progress (user_id, item_id, due_time, repetitions, status) VALUES (?, ?, ?, ?, ?)",
                    (new_user_id, new_item_id, due_time_iso, review_count, 'reviewing' if learned_date else 'new')
                )
                
                new_cursor.execute("SELECT container_id FROM learning_items WHERE item_id = ?", (new_item_id,))
                result = new_cursor.fetchone()
                if result and (new_user_id, result[0]) not in processed_user_container_pairs:
                    container_id = result[0]
                    new_cursor.execute("INSERT OR IGNORE INTO user_container_states (user_id, container_id, last_accessed) VALUES (?, ?, ?)",
                                       (new_user_id, container_id, datetime.now(timezone.utc).isoformat()))
                    processed_user_container_pairs.add((new_user_id, container_id))
        print(f"-> Đã chuyển đổi {len(flashcard_progress_data)} bản ghi tiến độ flashcard.")

        # Xử lý Quiz
        old_cursor.execute("SELECT user_id, question_id, is_correct, answered_at FROM UserQuizProgress")
        quiz_progress_data = old_cursor.fetchall()
        for old_progress in quiz_progress_data:
            old_user_id, old_question_id, is_correct, answered_at = old_progress
            new_user_id = user_id_map.get(old_user_id)
            new_item_id = quiz_question_id_map.get(old_question_id)
            
            if new_user_id and new_item_id:
                # Dữ liệu cũ không có nhiều thông tin, ta sẽ điền mặc định
                times_correct = 1 if is_correct else 0
                times_incorrect = 0 if is_correct else 1
                new_cursor.execute(
                    "INSERT INTO quiz_progress (user_id, item_id, times_correct, times_incorrect, last_reviewed, status) VALUES (?, ?, ?, ?, ?, ?)",
                    (new_user_id, new_item_id, times_correct, times_incorrect, answered_at, 'answered')
                )
                
                new_cursor.execute("SELECT container_id FROM learning_items WHERE item_id = ?", (new_item_id,))
                result = new_cursor.fetchone()
                if result and (new_user_id, result[0]) not in processed_user_container_pairs:
                    container_id = result[0]
                    new_cursor.execute("INSERT OR IGNORE INTO user_container_states (user_id, container_id, last_accessed) VALUES (?, ?, ?)",
                                       (new_user_id, container_id, datetime.now(timezone.utc).isoformat()))
                    processed_user_container_pairs.add((new_user_id, container_id))
        print(f"-> Đã chuyển đổi {len(quiz_progress_data)} bản ghi tiến độ quiz.")
        new_conn.commit()

        print("\n🎉 Mọi thứ đã xong! Quá trình chuyển đổi database đã hoàn tất thành công!")

    except sqlite3.Error as e:
        print(f"Lỗi SQLite: {e}")
    finally:
        if 'old_conn' in locals(): old_conn.close()
        if 'new_conn' in locals(): new_conn.close()
        print("Đã đóng kết nối database.")

if __name__ == '__main__':
    old_db_file = input("Nhập đường dẫn đến file database cũ của mindstack (ví dụ: mindstack.db): ")
    new_db_file = input("Nhập tên cho file database mới sẽ được tạo (ví dụ: newmindstack.db): ")
    
    convert_database(old_db_file, new_db_file)