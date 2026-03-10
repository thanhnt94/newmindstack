
import sqlite3
import os
import sys

def recover_db(source_path, target_path):
    print(f"Bắt đầu khôi phục từ {source_path} sang {target_path}...")
    
    if os.path.exists(target_path):
        os.remove(target_path)
        
    src_conn = sqlite3.connect(source_path)
    dst_conn = sqlite3.connect(target_path)
    
    src_cursor = src_conn.cursor()
    
    # Lấy danh sách Schema
    try:
        # Lấy tất cả các bảng
        src_cursor.execute("SELECT name, sql FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%';")
        tables = src_cursor.fetchall()
        
        for table_name, create_sql in tables:
            print(f"Đang xử lý bảng: {table_name}")
            dst_conn.execute(create_sql)
            
            # Copy data row-by-row to skip malformed rows
            src_cursor.execute(f"SELECT * FROM {table_name}")
            
            row_count = 0
            fail_count = 0
            
            while True:
                try:
                    row = src_cursor.fetchone()
                    if row is None:
                        break
                    
                    placeholders = ','.join(['?'] * len(row))
                    dst_conn.execute(f"INSERT INTO {table_name} VALUES ({placeholders})", row)
                    row_count += 1
                except sqlite3.DatabaseError as e:
                    print(f"Lỗi hàng trong bảng {table_name}: {e}")
                    fail_count += 1
                except Exception as e:
                    print(f"Lỗi không xác định: {e}")
                    fail_count += 1
            
            dst_conn.commit()
            print(f"Kết thúc bảng {table_name}: Thành công {row_count}, Lỗi {fail_count}")

        # Lấy các index
        src_cursor.execute("SELECT name, sql FROM sqlite_master WHERE type='index' AND sql IS NOT NULL;")
        indices = src_cursor.fetchall()
        for idx_name, idx_sql in indices:
            print(f"Đang tạo lại index: {idx_name}")
            try:
                dst_conn.execute(idx_sql)
            except Exception as e:
                print(f"Lỗi tạo index {idx_name}: {e}")
        
        dst_conn.commit()
        print("Quá trình khôi phục hoàn tất.")
        
    except Exception as e:
        print(f"Lỗi nghiêm trọng: {e}")
    finally:
        src_conn.close()
        dst_conn.close()

if __name__ == "__main__":
    source = "c:/Code/MindStack/database/mindstack_new.db"
    target = "c:/Code/MindStack/database/mindstack_new_recovered.db"
    
    # Backup file gốc trước khi làm gì
    import shutil
    backup_path = source + ".corrupted.bak"
    if not os.path.exists(backup_path):
        shutil.copy2(source, backup_path)
        print(f"Đã tạo bản sao lưu file lỗi tại {backup_path}")
        
    recover_db(source, target)
