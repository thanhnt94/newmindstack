# File: newmindstack/mindstack_app/modules/content_management/forms.py
# Phiên bản: 3.3
# ĐÃ SỬA: Thêm trường 'ai_prompt' vào FlashcardItemForm và QuizItemForm.

from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, BooleanField, SubmitField, URLField, FileField, SelectField
from wtforms.validators import DataRequired, Length, Optional, ValidationError, Email
from flask_wtf.file import FileAllowed

# ==============================================================================
# Form MỚI cho QUẢN LÝ QUYỀN (CONTRIBUTORS)
# ==============================================================================

class ContributorForm(FlaskForm):
    """
    Form để thêm một người đóng góp mới bằng email.
    """
    email = StringField('Email của người dùng', 
                        validators=[DataRequired(message="Vui lòng nhập email."), 
                                    Email(message="Địa chỉ email không hợp lệ.")])
    permission_level = SelectField('Cấp độ quyền', 
                                   choices=[('editor', 'Editor (Chỉnh sửa)')], # Hiện tại chỉ có 1 cấp độ
                                   validators=[DataRequired()])
    submit = SubmitField('Thêm quyền')

# ==============================================================================
# Forms cho KHÓA HỌC (COURSES)
# ==============================================================================

class CourseForm(FlaskForm):
    """
    Form để tạo hoặc sửa một Khóa học (LearningContainer).
    """
    title = StringField('Tiêu đề khoá học', validators=[DataRequired(message="Vui lòng nhập tiêu đề khoá học."), Length(max=255)])
    description = TextAreaField('Mô tả', validators=[Optional()])
    tags = StringField('Thẻ (cách nhau bởi dấu phẩy)', validators=[Optional(), Length(max=255)])
    is_public = BooleanField('Công khai (người khác có thể tìm thấy và học)')
    ai_prompt = TextAreaField('AI Prompt Tùy chỉnh (cho khoá học)', 
                              description='Nhập prompt tùy chỉnh để AI tạo nội dung. Nếu để trống, hệ thống sẽ sử dụng prompt mặc định.',
                              validators=[Optional()])
    submit = SubmitField('Lưu khoá học')

class LessonForm(FlaskForm):
    """
    Form để tạo hoặc sửa một Bài học (LearningItem).
    """
    title = StringField('Tiêu đề bài học', validators=[DataRequired(message="Tiêu đề bài học không được để trống.")])
    bbcode_content = TextAreaField('Nội dung bài học (BBCode)', validators=[DataRequired(message="Nội dung bài học không được để trống.")])
    lesson_audio_url = URLField('URL file âm thanh bài học', validators=[Optional()])
    lesson_image_url = URLField('URL hình ảnh bài học', validators=[Optional()])
    ai_explanation = TextAreaField('Giải thích AI', render_kw={'readonly': True}, validators=[Optional()])
    submit = SubmitField('Lưu bài học')

# ==============================================================================
# Forms cho THẺ GHI NHỚ (FLASHCARDS)
# ==============================================================================

class FlashcardSetForm(FlaskForm):
    """
    Form để tạo hoặc sửa một bộ Flashcard (LearningContainer).
    """
    title = StringField('Tiêu đề bộ thẻ', validators=[DataRequired(message="Vui lòng nhập tiêu đề bộ thẻ."), Length(max=255)])
    description = TextAreaField('Mô tả', validators=[Optional()])
    tags = StringField('Thẻ (cách nhau bởi dấu phẩy)', validators=[Optional(), Length(max=255)])
    is_public = BooleanField('Công khai (người khác có thể tìm thấy và học)')
    ai_prompt = TextAreaField('AI Prompt Tùy chỉnh (cho bộ thẻ)', 
                              description='Nhập prompt tùy chỉnh để AI tạo thẻ. Nếu để trống, hệ thống sẽ sử dụng prompt mặc định.',
                              validators=[Optional()])
    excel_file = FileField('Tải từ file Excel (.xlsx)', validators=[
        FileAllowed(['xlsx'], 'Chỉ cho phép file Excel (.xlsx)!'),
        Optional()
    ], description='Nếu bạn tải file lên, các thông tin bạn điền ở trên (ngoại trừ Tiêu đề, Mô tả, Tags, Trạng thái) sẽ bị bỏ qua.')
    submit = SubmitField('Lưu bộ thẻ')

class FlashcardItemForm(FlaskForm):
    """
    Form để tạo hoặc sửa một thẻ Flashcard (LearningItem).
    """
    front = TextAreaField('Mặt trước (câu hỏi/từ)', validators=[DataRequired(message="Mặt trước không được để trống.")])
    back = TextAreaField('Mặt sau (câu trả lời/định nghĩa)', validators=[DataRequired(message="Mặt sau không được để trống.")])
    front_audio_content = TextAreaField('Văn bản tạo âm thanh mặt trước (TTS)', validators=[Optional()])
    front_audio_url = URLField('URL file âm thanh mặt trước', validators=[Optional()])
    back_audio_content = TextAreaField('Văn bản tạo âm thanh mặt sau (TTS)', validators=[Optional()])
    back_audio_url = URLField('URL file âm thanh mặt sau', validators=[Optional()])
    front_img = URLField('URL hình ảnh mặt trước', validators=[Optional()])
    back_img = URLField('URL hình ảnh mặt sau', validators=[Optional()])
    ai_explanation = TextAreaField('Giải thích AI', render_kw={'readonly': True}, validators=[Optional()])
    ai_prompt = TextAreaField('AI Prompt tùy chỉnh (cho thẻ này)', 
                              description='Nhập prompt tùy chỉnh để ghi đè prompt của bộ thẻ hoặc mặc định hệ thống. Nếu để trống, hệ thống sẽ tự động sử dụng prompt cấp trên.',
                              validators=[Optional()])
    submit = SubmitField('Lưu thẻ')

# ==============================================================================
# Forms cho BỘ CÂU HỎI (QUIZZES)
# ==============================================================================

class QuizSetForm(FlaskForm):
    """
    Form để tạo hoặc sửa một bộ Quiz (LearningContainer).
    """
    title = StringField('Tiêu đề bộ Quiz', validators=[DataRequired(message="Vui lòng nhập tiêu đề bộ Quiz."), Length(max=255)])
    description = TextAreaField('Mô tả', validators=[Optional()])
    tags = StringField('Thẻ (cách nhau bởi dấu phẩy)', validators=[Optional(), Length(max=255)])
    is_public = BooleanField('Công khai (người khác có thể tìm thấy và làm)')
    ai_prompt = TextAreaField('AI Prompt Tùy chỉnh (cho bộ Quiz)', 
                              description='Nhập prompt tùy chỉnh để AI tạo câu hỏi. Nếu để trống, hệ thống sẽ sử dụng prompt mặc định.',
                              validators=[Optional()])
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
    passage_order = StringField('Thứ tự đoạn văn (ví dụ: 1, 2)', validators=[Optional()])
    ai_explanation = TextAreaField('Giải thích AI', render_kw={'readonly': True}, validators=[Optional()])
    ai_prompt = TextAreaField('AI Prompt tùy chỉnh (cho câu hỏi này)', 
                              description='Nhập prompt tùy chỉnh để ghi đè prompt của bộ quiz hoặc mặc định hệ thống. Nếu để trống, hệ thống sẽ tự động sử dụng prompt cấp trên.',
                              validators=[Optional()])
    submit = SubmitField('Lưu câu hỏi')

    def validate(self, extra_validators=None):
        initial_validation = super().validate(extra_validators)
        if not initial_validation:
            return False
        correct_opt = self.correct_answer_text.data
        if correct_opt == 'C' and not self.option_c.data:
            self.correct_answer_text.errors.append('Đáp án đúng C không thể được chọn nếu Lựa chọn C trống.')
            return False
        if correct_opt == 'D' and not self.option_d.data:
            self.correct_answer_text.errors.append('Đáp án đúng D không thể được chọn nếu Lựa chọn D trống.')
            return False
        return True