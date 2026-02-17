import os
import shutil

def get_project_root():
    """Lấy thư mục hiện tại nơi script đang chạy."""
    return os.getcwd()

def format_size(size_bytes):
    """Chuyển đổi dung lượng byte sang KB, MB, GB cho dễ đọc."""
    if size_bytes == 0:
        return "0 B"
    size_name = ("B", "KB", "MB", "GB", "TB")
    i = int(os.path.abspath(os.path.join(str(size_bytes).replace('-', ''), '..')).count(os.sep) / 1024) if size_bytes > 1024 else 0
    # Logic đơn giản hoá:
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.2f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.2f} PB"

def remove_pycache(root_dir):
    """1. Xoá các thư mục __pycache__ và file .pyc"""
    print(f"\n--- ĐANG QUÉT VÀ XOÁ PYCACHE TẠI: {root_dir} ---")
    deleted_dirs = 0
    deleted_files = 0
    
    for dirpath, dirnames, filenames in os.walk(root_dir):
        # Xoá thư mục __pycache__
        if "__pycache__" in dirnames:
            cache_path = os.path.join(dirpath, "__pycache__")
            try:
                shutil.rmtree(cache_path)
                print(f"[Đã xoá thư mục]: {cache_path}")
                deleted_dirs += 1
            except Exception as e:
                print(f"[Lỗi xoá thư mục] {cache_path}: {e}")
            dirnames.remove("__pycache__") # Không duyệt vào trong thư mục đã xoá

        # Xoá file .pyc lẻ (nếu có)
        for file in filenames:
            if file.endswith(".pyc") or file.endswith(".pyo"):
                file_path = os.path.join(dirpath, file)
                try:
                    os.remove(file_path)
                    print(f"[Đã xoá file]: {file_path}")
                    deleted_files += 1
                except Exception as e:
                    print(f"[Lỗi xoá file] {file_path}: {e}")

    print(f"-> Hoàn tất: Đã xoá {deleted_dirs} thư mục __pycache__ và {deleted_files} file rác.")

def project_statistics(root_dir):
    """2. Đếm số lượng file và tính tổng dung lượng"""
    print(f"\n--- THỐNG KÊ DỰ ÁN ---")
    total_files = 0
    total_size = 0
    file_extensions = {}

    for dirpath, dirnames, filenames in os.walk(root_dir):
        # Bỏ qua thư mục ẩn như .git, .idea, .vscode nếu muốn (ở đây tôi giữ lại để tính full dự án)
        if '.git' in dirnames: dirnames.remove('.git') 

        for f in filenames:
            fp = os.path.join(dirpath, f)
            total_files += 1
            try:
                size = os.path.getsize(fp)
                total_size += size
                
                # Thống kê đuôi file (tuỳ chọn thêm cho trực quan)
                ext = os.path.splitext(f)[1].lower()
                file_extensions[ext] = file_extensions.get(ext, 0) + 1
            except OSError:
                continue

    print(f"Tổng số lượng file: {total_files}")
    print(f"Tổng dung lượng dự án: {format_size(total_size)}")
    # print(f"Chi tiết loại file: {file_extensions}") # Bỏ comment nếu muốn xem chi tiết

def count_lines_in_file(file_path):
    """Hàm hỗ trợ đếm dòng, bỏ qua file nhị phân/ảnh"""
    try:
        # Cố gắng đọc file với encoding utf-8
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            return sum(1 for _ in f)
    except Exception:
        return 0

def top_largest_files_by_lines(root_dir):
    """3. Liệt kê file có số dòng lớn nhất"""
    print(f"\n--- TÌM CÁC FILE CÓ NHIỀU DÒNG NHẤT ---")
    try:
        top_n = int(input("Bạn muốn xem Top bao nhiêu file lớn nhất? (nhập số, ví dụ 5): "))
    except ValueError:
        print("Vui lòng nhập một con số hợp lệ.")
        return

    file_line_counts = []
    
    # Các đuôi file code cần kiểm tra (tránh kiểm tra file ảnh, exe, dll...)
    valid_extensions = {'.py', '.js', '.html', '.css', '.java', '.c', '.cpp', '.h', '.txt', '.md', '.json', '.xml', '.sql'}

    print("Đang phân tích...")
    for dirpath, dirnames, filenames in os.walk(root_dir):
        if '.git' in dirnames: dirnames.remove('.git') # Bỏ qua .git
        if 'venv' in dirnames: dirnames.remove('venv') # Bỏ qua môi trường ảo nếu có
        if '.idea' in dirnames: dirnames.remove('.idea')

        for f in filenames:
            ext = os.path.splitext(f)[1].lower()
            if ext in valid_extensions:
                full_path = os.path.join(dirpath, f)
                lines = count_lines_in_file(full_path)
                # Lưu đường dẫn tương đối cho gọn
                rel_path = os.path.relpath(full_path, root_dir)
                file_line_counts.append((rel_path, lines))

    # Sắp xếp giảm dần theo số dòng
    file_line_counts.sort(key=lambda x: x[1], reverse=True)

    print(f"\nTop {top_n} file có số dòng nhiều nhất:")
    print("-" * 50)
    print(f"{'Số dòng':<10} | {'Tên File'}")
    print("-" * 50)
    
    for i, (fname, lines) in enumerate(file_line_counts[:top_n]):
        print(f"{lines:<10} | {fname}")
    print("-" * 50)

def main():
    root_dir = get_project_root()
    print(f"Script đang chạy tại: {root_dir}")
    print("Chọn chức năng:")
    print("1. Xoá file pycache")
    print("2. Thống kê file và dung lượng")
    print("3. Tìm file code dài nhất")
    print("4. Chạy tất cả")
    
    choice = input("Nhập lựa chọn (1-4): ")

    if choice == '1':
        remove_pycache(root_dir)
    elif choice == '2':
        project_statistics(root_dir)
    elif choice == '3':
        top_largest_files_by_lines(root_dir)
    elif choice == '4':
        remove_pycache(root_dir)
        project_statistics(root_dir)
        top_largest_files_by_lines(root_dir)
    else:
        print("Lựa chọn không hợp lệ.")

if __name__ == "__main__":
    main()