import os
import sqlite3

repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
db_path = os.path.join(repo_root, 'database', 'watchtogether.sqlite')

username = input("Nhập username WatchTogether của bạn để cấp quyền Admin: ")

try:
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("UPDATE wt_users SET is_admin = 1 WHERE username = ?", (username,))
    if cur.rowcount > 0:
        print(f"Thành công! Tài khoản '{username}' đã trở thành Admin.")
    else:
        print(f"Thất bại: Không tìm thấy tài khoản '{username}' trong CSDL WatchTogether.")
    conn.commit()
    conn.close()
except Exception as e:
    print(f"Có lỗi xảy ra: {e}")
