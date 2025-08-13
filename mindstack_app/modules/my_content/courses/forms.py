# File: Mindstack/web/mindstack_app/modules/my_content/courses/forms.py
# Version: 1.0
# Mục đích: Định nghĩa các form để quản lý Khóa học và Bài học.

from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, BooleanField, SubmitField, URLField, FileField
from wtforms.validators import DataRequired, Length, Optional
from flask_wtf.file import FileAllowed

class CourseForm(FlaskForm):
    """
    Form để tạo hoặc sửa một Khóa học (LearningContainer).
    """
    title = StringField('Tiêu đề khoá học', validators=[DataRequired(message="Vui lòng nhập tiêu đề khoá học."), Length(max=255)])
    description = TextAreaField('Mô tả', validators=[Optional()])
    tags = StringField('Thẻ (cách nhau bởi dấu phẩy)', validators=[Optional(), Length(max=255)])
    is_public = BooleanField('Công khai (người khác có thể tìm thấy và học)')
    
    # AI Prompt Tùy chỉnh cho khoá học
    ai_prompt = TextAreaField('AI Prompt Tùy chỉnh (cho khoá học)', 
                              description='Nhập prompt tùy chỉnh để AI tạo nội dung. Nếu để trống, hệ thống sẽ sử dụng prompt mặc định.',
                              validators=[Optional()])
    
    # Có thể thêm upload file Excel cho Course sau nếu cần
    # excel_file = FileField('Tải từ file Excel (.xlsx)', validators=[
    #     FileAllowed(['xlsx'], 'Chỉ cho phép file Excel (.xlsx)!'),
    #     Optional()
    # ], description='Nếu bạn tải file lên, các thông tin bạn điền ở trên sẽ bị bỏ qua.')
    
    submit = SubmitField('Lưu khoá học')

class LessonForm(FlaskForm):
    """
    Form để tạo hoặc sửa một Bài học (LearningItem).
    """
    title = StringField('Tiêu đề bài học', validators=[DataRequired(message="Tiêu đề bài học không được để trống.")])
    # Nội dung bài học sẽ được lưu dưới dạng BBCode
    bbcode_content = TextAreaField('Nội dung bài học (BBCode)', validators=[DataRequired(message="Nội dung bài học không được để trống.")])
    
    # Các trường tùy chọn cho audio và hình ảnh (nếu bài học có media riêng)
    lesson_audio_url = URLField('URL file âm thanh bài học', validators=[Optional()])
    lesson_image_url = URLField('URL hình ảnh bài học', validators=[Optional()])
    
    # Nội dung giải thích do AI (chỉ để hiển thị)
    ai_explanation = TextAreaField('Giải thích AI', render_kw={'readonly': True}, validators=[Optional()])

    submit = SubmitField('Lưu bài học')
