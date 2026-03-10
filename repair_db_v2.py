
import sqlite3
import os

def recover_via_dump(source_path, target_path):
    print(f"Đang thử khôi phục qua iterdump từ {source_path}...")
    
    if os.path.exists(target_path):
        os.remove(target_path)
    
    try:
        source_conn = sqlite3.connect(source_path)
        target_conn = sqlite3.connect(target_path)
        
        # iterdump generates SQL text. We pipe it to the target database.
        # We wrap it in a try-except to catch potential issues during dumping.
        count = 0
        for line in source_conn.iterdump():
            try:
                target_conn.execute(line)
                count += 1
                if count % 1000 == 0:
                    print(f"Đã xử lý {count} dòng SQL...")
            except sqlite3.Error as e:
                # If a line fails, we skip it but log it
                print(f"Bỏ qua dòng lỗi SQL: {e}")
                print(f"Dòng lỗi: {line[:100]}...")
        
        target_conn.commit()
        print(f"Hoàn tất! Đã thực thi {count} dòng SQL.")
        
    except Exception as e:
        print(f"Lỗi khôi phục: {e}")
    finally:
        source_conn.close()
        target_conn.close()

if __name__ == "__main__":
    # Use the backup of the corrupted database as source
    source = "c:/Code/MindStack/database/mindstack_new.db.last_corrupted"
    target = "c:/Code/MindStack/database/mindstack_new_v2_recovered.db"
    
    recover_via_dump(source, target)
