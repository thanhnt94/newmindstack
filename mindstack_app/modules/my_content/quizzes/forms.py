# File: Mindstack/web/mindstack_app/modules/my_content/quizzes/forms.py
# Version: 1.1 - Đã thêm trường upload Excel vào QuizSetForm.
# Mục đích: Định nghĩa các form để quản lý bộ Quiz và câu hỏi Quiz.

from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, BooleanField, SubmitField, URLField, FileField, SelectField
from wtforms.validators import DataRequired, Length, Optional, ValidationError
from flask_wtf.file import FileAllowed # Để xác thực loại file

class QuizSetForm(FlaskForm):
    """
    Form để tạo hoặc sửa một bộ Quiz (LearningContainer).
    """
    title = StringField('Tiêu đề bộ Quiz', validators=[DataRequired(message="Vui lòng nhập tiêu đề bộ Quiz."), Length(max=255)])
    description = TextAreaField('Mô tả', validators=[Optional()])
    tags = StringField('Thẻ (cách nhau bởi dấu phẩy)', validators=[Optional(), Length(max=255)])
    is_public = BooleanField('Công khai (người khác có thể tìm thấy và làm)')
    
    # AI Prompt Tùy chỉnh cho bộ Quiz
    ai_prompt = TextAreaField('AI Prompt Tùy chỉnh (cho bộ Quiz)', 
                              description='Nhập prompt tùy chỉnh để AI tạo câu hỏi. Nếu để trống, hệ thống sẽ sử dụng prompt mặc định.',
                              validators=[Optional()])
    
    # TRƯỜNG MỚI (ĐÃ BỎ COMMENT): Upload file Excel
    excel_file = FileField('Tải từ file Excel (.xlsx)', validators=[
        FileAllowed(['xlsx'], 'Chỉ cho phép file Excel (.xlsx)!'),
        Optional()
    ], description='Nếu bạn tải file lên, các thông tin bạn điền ở trên (ngoại trừ Tiêu đề, Mô tả, Tags, Trạng thái) sẽ bị bỏ qua.')
    
    submit = SubmitField('Lưu bộ Quiz')

class QuizItemForm(FlaskForm):
    """
    Form để tạo hoặc sửa một câu hỏi Quiz (LearningItem).
    """
    question = TextAreaField('Câu hỏi', validators=[DataRequired(message="Câu hỏi không được để trống.")])
    pre_question_text = TextAreaField('Văn bản trước câu hỏi', validators=[Optional()])
    
    option_a = StringField('Lựa chọn A', validators=[DataRequired(message="Lựa chọn A không được để trống.")])
    option_b = StringField('Lựa chọn B', validators=[DataRequired(message="Lựa chọn B không được để trống.")])
    option_c = StringField('Lựa chọn C', validators=[Optional()])
    option_d = StringField('Lựa chọn D', validators=[Optional()])
    
    correct_answer_text = SelectField('Đáp án đúng', choices=[
        ('A', 'A'), ('B', 'B'), ('C', 'C'), ('D', 'D')
    ], validators=[DataRequired(message="Vui lòng chọn đáp án đúng.")])
    
    guidance = TextAreaField('Giải thích/Gợi ý', validators=[Optional()])
    
    question_image_file = URLField('URL hình ảnh câu hỏi', validators=[Optional()])
    question_audio_file = URLField('URL file âm thanh câu hỏi', validators=[Optional()])
    
    passage_text = TextAreaField('Đoạn văn liên quan', validators=[Optional()])
    passage_order = StringField('Thứ tự đoạn văn (ví dụ: 1, 2)', validators=[Optional()]) # Có thể là IntegerField nếu chỉ là số
    
    # Nội dung giải thích do AI (chỉ để hiển thị)
    ai_explanation = TextAreaField('Giải thích AI', render_kw={'readonly': True}, validators=[Optional()])

    submit = SubmitField('Lưu câu hỏi')

    def validate(self, extra_validators=None):
        initial_validation = super().validate(extra_validators)
        if not initial_validation:
            return False

        # Đảm bảo đáp án đúng không trỏ đến lựa chọn trống
        correct_opt = self.correct_answer_text.data
        if correct_opt == 'C' and not self.option_c.data:
            self.correct_answer_text.errors.append('Đáp án đúng C không thể được chọn nếu Lựa chọn C trống.')
            return False
        if correct_opt == 'D' and not self.option_d.data:
            self.correct_answer_text.errors.append('Đáp án đúng D không thể được chọn nếu Lựa chọn D trống.')
            return False
        
        return True
