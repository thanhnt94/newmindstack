# seed_course_data.py
# Phiên bản: 1.0
# Mục đích: Thêm dữ liệu mẫu cho một khoá học để kiểm tra chức năng.
# Hướng dẫn chạy: python seed_course_data.py từ thư mục gốc của dự án.

from mindstack_app import create_app, db
from mindstack_app.models import User, LearningContainer, LearningItem

def seed_data():
    """
    Mô tả: Hàm chính để thêm dữ liệu khoá học mẫu vào database.
    """
    app = create_app()
    with app.app_context():
        print("Bắt đầu thêm dữ liệu khóa học mẫu...")

        # 1. Tìm người dùng 'admin' để làm người tạo khóa học
        admin_user = User.query.filter_by(username='admin').first()
        if not admin_user:
            print("Lỗi: Không tìm thấy người dùng 'admin'. Vui lòng tạo tài khoản admin trước.")
            return

        # 2. Kiểm tra xem khóa học đã tồn tại chưa để tránh tạo trùng lặp
        course_title = "Khóa học Python cơ bản 2"
        existing_course = LearningContainer.query.filter_by(title=course_title, container_type='COURSE').first()
        if existing_course:
            print(f"Khóa học '{course_title}' đã tồn tại. Bỏ qua.")
            return

        # 3. Tạo một LearningContainer cho khóa học
        new_course = LearningContainer(
            creator_user_id=admin_user.user_id,
            container_type='COURSE',
            title=course_title,
            description='Khóa học này cung cấp kiến thức nền tảng về lập trình Python cho người mới bắt đầu, từ biến, kiểu dữ liệu đến các cấu trúc điều khiển.',
            tags='python, lap trinh, co ban',
            is_public=True
        )
        db.session.add(new_course)
        db.session.flush()  # Gửi lên DB để lấy được new_course.container_id

        print(f"Đã tạo khóa học: '{new_course.title}' (ID: {new_course.container_id})")

        # 4. Tạo các LearningItem (bài học) cho khóa học
        lessons_data = [
            {
                'title': 'Bài 1: Giới thiệu về Python',
                'bbcode_content': '[b]Python là gì?[/b]\n\nPython là một ngôn ngữ lập trình bậc cao, thông dịch, hướng đối tượng và đa năng. Nó nổi tiếng vì có cú pháp rất đơn giản và dễ đọc.\n\n[img]https://upload.wikimedia.org/wikipedia/commons/thumb/c/c3/Python-logo-notext.svg/800px-Python-logo-notext.svg.png[/img]\n\n[b]Tại sao nên học Python?[/b]\n[list]\n[*]Dễ học, dễ đọc.\n[*]Cộng đồng hỗ trợ lớn.\n[*]Ứng dụng trong nhiều lĩnh vực: phát triển web, khoa học dữ liệu, AI, machine learning...\n[/list]'
            },
            {
                'title': 'Bài 2: Biến và Kiểu dữ liệu',
                'bbcode_content': 'Trong Python, bạn không cần phải khai báo kiểu dữ liệu cho biến một cách tường minh. Kiểu dữ liệu sẽ được tự động xác định khi bạn gán giá trị.\n\n[b]Ví dụ về biến:[/b]\n[code]x = 5          # x là kiểu Integer\ny = "Xin chào" # y là kiểu String\nz = 3.14       # z là kiểu Float[/code]\n\nCác kiểu dữ liệu cơ bản bao gồm: số nguyên (int), số thực (float), chuỗi (str), và boolean (bool).'
            },
            {
                'title': 'Bài 3: Cấu trúc điều khiển',
                'bbcode_content': 'Cấu trúc điều khiển cho phép bạn kiểm soát luồng thực thi của chương trình.\n\n[b]Câu lệnh điều kiện (if-elif-else):[/b]\n[code]diem = 85\nif diem >= 90:\n    print("Xuất sắc")\nelif diem >= 80:\n    print("Giỏi")\nelse:\n    print("Khá")[/code]\n\n[b]Vòng lặp (for, while):[/b]\nSử dụng vòng lặp [b]for[/b] để lặp qua một chuỗi (ví dụ: list, tuple) và [b]while[/b] để lặp khi một điều kiện còn đúng.'
            }
        ]

        for index, lesson_data in enumerate(lessons_data):
            new_lesson = LearningItem(
                container_id=new_course.container_id,
                item_type='LESSON',
                content={
                    'title': lesson_data['title'],
                    'bbcode_content': lesson_data['bbcode_content']
                },
                order_in_container=index + 1
            )
            db.session.add(new_lesson)
            print(f"  - Đã thêm bài học: '{lesson_data['title']}'")

        # 5. Lưu tất cả thay đổi vào database
        db.session.commit()
        print("\nThêm dữ liệu mẫu thành công!")

if __name__ == '__main__':
    seed_data()
