# mindstack_app/modules/content_management/forms.py
# Phiên bản: 4.6
# MỤC ĐÍCH: Bổ sung trường order_in_container vào LessonForm để hỗ trợ sắp xếp bài học.
# ĐÃ SỬA: Thêm IntegerField cho order_in_container vào LessonForm.

from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, BooleanField, SubmitField, FileField, SelectField, IntegerField
from wtforms.validators import DataRequired, Length, Optional, ValidationError, NumberRange
from flask_wtf.file import FileAllowed
import re

# ==============================================================================
# Form MỚI cho QUẢN LÝ QUYỀN (CONTRIBUTORS)
# ==============================================================================

class ContributorForm(FlaskForm):
    """
    Form để thêm một người đóng góp mới bằng tên người dùng.
    """
    username = StringField('Tên người dùng',
                           validators=[DataRequired(message="Vui lòng nhập tên người dùng."),
                                       Length(max=150, message="Tên người dùng tối đa 150 ký tự.")],
                           render_kw={'autocomplete': 'off'})
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
    """Form để tạo hoặc sửa một Bài học (LearningItem)."""

    title = StringField('Tiêu đề bài học', validators=[DataRequired(message="Tiêu đề bài học không được để trống.")])
    content_html = TextAreaField(
        'Nội dung bài học',
        validators=[DataRequired(message="Nội dung bài học không được để trống.")],
        description="Sử dụng trình soạn thảo WYSIWYG để định dạng nội dung, chèn hình ảnh, audio, bảng biểu...",
    )
    estimated_time = IntegerField('Thời gian hoàn thành dự tính (phút)', 
                                validators=[Optional(), 
                                            NumberRange(min=0, message="Thời gian phải là một số dương.")])
    ai_explanation = TextAreaField('Giải thích AI', render_kw={'readonly': True}, validators=[Optional()])
    order_in_container = IntegerField('Thứ tự hiển thị', validators=[
        Optional(),
        NumberRange(min=1, message="Thứ tự phải là một số nguyên dương.")
    ], description="Nhập một số để thay đổi vị trí của bài học. Nếu để trống, bài học sẽ được thêm vào cuối.")
    submit = SubmitField('Lưu bài học')
    
    def validate_url_fields(self):
        """
        Mô tả: Validator tùy chỉnh để chấp nhận cả URL đầy đủ và đường dẫn tương đối cho các trường media.
        """
        def is_valid_url_or_path(value):
            if value.startswith(('http://', 'https://')):
                url_pattern = re.compile(
                    r'^(?:http)s?://' 
                    r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+(?:[A-Z]{2,6}\.?|[A-Z0-9-]{2,}\.?)|'
                    r'localhost|'
                    r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'
                    r'(?::\d+)?'
                    r'(?:/?|[/?]\S+)$', re.IGNORECASE)
                return re.match(url_pattern, value) is not None
            return True

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
    supports_pronunciation = BooleanField('Hỗ trợ luyện phát âm')
    supports_writing = BooleanField('Hỗ trợ luyện viết')
    supports_quiz = BooleanField('Hỗ trợ luyện trắc nghiệm')
    supports_essay = BooleanField('Hỗ trợ tự luận')
    supports_listening = BooleanField('Hỗ trợ luyện nghe')
    supports_speaking = BooleanField('Hỗ trợ luyện nói')
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
    front_audio_url = StringField('URL file âm thanh mặt trước', validators=[Optional()])
    back_audio_content = TextAreaField('Văn bản tạo âm thanh mặt sau (TTS)', validators=[Optional()])
    back_audio_url = StringField('URL file âm thanh mặt sau', validators=[Optional()])
    front_img = StringField('URL hình ảnh mặt trước', validators=[Optional()])
    back_img = StringField('URL hình ảnh mặt sau', validators=[Optional()])
    ai_explanation = TextAreaField('Giải thích AI', render_kw={'readonly': True}, validators=[Optional()])
    ai_prompt = TextAreaField('AI Prompt tùy chỉnh (cho thẻ này)',
                              description='Nhập prompt tùy chỉnh để ghi đè prompt của bộ thẻ hoặc mặc định hệ thống. Nếu để trống, hệ thống sẽ tự động sử dụng prompt cấp trên.',
                              validators=[Optional()])
    supports_pronunciation = BooleanField('Hỗ trợ luyện phát âm')
    supports_writing = BooleanField('Hỗ trợ luyện viết')
    supports_quiz = BooleanField('Hỗ trợ luyện trắc nghiệm')
    supports_essay = BooleanField('Hỗ trợ tự luận')
    supports_listening = BooleanField('Hỗ trợ luyện nghe')
    supports_speaking = BooleanField('Hỗ trợ luyện nói')
    order_in_container = IntegerField('Thứ tự hiển thị', validators=[
        Optional(),
        NumberRange(min=1, message="Thứ tự phải là một số nguyên dương.")
    ], description="Nhập một số để thay đổi vị trí của thẻ. Nếu để trống, thẻ sẽ được thêm vào cuối.")
    submit = SubmitField('Lưu thẻ')

    def validate_front_img(self, field):
        """
        Mô tả: Validator tùy chỉnh để chấp nhận cả URL đầy đủ và đường dẫn tương đối.
        """
        if field.data and not self._is_valid_url_or_path(field.data):
            raise ValidationError('Đường dẫn hình ảnh không hợp lệ. Vui lòng nhập URL đầy đủ hoặc đường dẫn tương đối.')

    def validate_back_img(self, field):
        """
        Mô tả: Validator tùy chỉnh để chấp nhận cả URL đầy đủ và đường dẫn tương đối.
        """
        if field.data and not self._is_valid_url_or_path(field.data):
            raise ValidationError('Đường dẫn hình ảnh không hợp lệ. Vui lòng nhập URL đầy đủ hoặc đường dẫn tương đối.')

    def validate_front_audio_url(self, field):
        """
        Mô tả: Validator tùy chỉnh để chấp nhận cả URL đầy đủ và đường dẫn tương đối cho file âm thanh mặt trước.
        """
        if field.data and not self._is_valid_url_or_path(field.data):
            raise ValidationError('Đường dẫn file âm thanh mặt trước không hợp lệ. Vui lòng nhập URL đầy đủ hoặc đường dẫn tương đối.')

    def validate_back_audio_url(self, field):
        """
        Mô tả: Validator tùy chỉnh để chấp nhận cả URL đầy đủ và đường dẫn tương đối cho file âm thanh mặt sau.
        """
        if field.data and not self._is_valid_url_or_path(field.data):
            raise ValidationError('Đường dẫn file âm thanh mặt sau không hợp lệ. Vui lòng nhập URL đầy đủ hoặc đường dẫn tương đối.')

    def _is_valid_url_or_path(self, value):
        """
        Mô tả: Hàm kiểm tra nội bộ để xác định xem một chuỗi có phải là URL hợp lệ hay đường dẫn tương đối.
        """
        if value.startswith(('http://', 'https://')):
            url_pattern = re.compile(
                r'^(?:http)s?://' 
                r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+(?:[A-Z]{2,6}\.?|[A-Z0-9-]{2,}\.?)|'
                r'localhost|'
                r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'
                r'(?::\d+)?'
                r'(?:/?|[/?]\S+)$', re.IGNORECASE)
            return re.match(url_pattern, value) is not None
        
        return True

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
    option_a = StringField('Lựa chọn A', validators=[DataRequired(message="Vui lòng nhập lựa chọn A.")])
    option_b = StringField('Lựa chọn B', validators=[DataRequired(message="Vui lòng nhập lựa chọn B.")])
    option_c = StringField('Lựa chọn C', validators=[Optional()])
    option_d = StringField('Lựa chọn D', validators=[Optional()])
    correct_answer_text = SelectField('Đáp án đúng', choices=[
        ('A', 'A'), ('B', 'B'), ('C', 'C'), ('D', 'D')
    ], validators=[DataRequired(message="Vui lòng chọn đáp án đúng.")])
    guidance = TextAreaField('Giải thích/Gợi ý', validators=[Optional()])
    question_image_file = StringField('URL hình ảnh câu hỏi', validators=[Optional()])
    question_audio_file = StringField('URL file âm thanh câu hỏi', validators=[Optional()])
    passage_text = TextAreaField('Đoạn văn liên quan', validators=[Optional()])
    passage_order = StringField('Thứ tự đoạn văn (ví dụ: 1, 2)', validators=[Optional()])
    ai_explanation = TextAreaField('Giải thích AI', render_kw={'readonly': True}, validators=[Optional()])
    ai_prompt = TextAreaField('AI Prompt tùy chỉnh (cho câu hỏi này)', 
                              description='Nhập prompt tùy chỉnh để ghi đè prompt của bộ quiz hoặc mặc định hệ thống. Nếu để trống, hệ thống sẽ tự động sử dụng prompt cấp trên.',
                              validators=[Optional()])
    order_in_container = IntegerField('Thứ tự hiển thị', validators=[
        Optional(),
        NumberRange(min=1, message="Thứ tự phải là một số nguyên dương.")
    ], description="Nhập một số để thay đổi vị trí của câu hỏi. Nếu để trống, câu hỏi sẽ được thêm vào cuối.")
    submit = SubmitField('Lưu câu hỏi')
    
    def validate_question_image_file(self, field):
        """
        Mô tả: Validator tùy chỉnh để chấp nhận cả URL đầy đủ và đường dẫn tương đối.
        """
        if field.data and not self._is_valid_url_or_path(field.data):
            raise ValidationError('Đường dẫn hình ảnh câu hỏi không hợp lệ. Vui lòng nhập URL đầy đủ hoặc đường dẫn tương đối.')
            
    def validate_question_audio_file(self, field):
        """
        Mô tả: Validator tùy chỉnh để chấp nhận cả URL đầy đủ và đường dẫn tương đối.
        """
        if field.data and not self._is_valid_url_or_path(field.data):
            raise ValidationError('Đường dẫn file âm thanh câu hỏi không hợp lệ. Vui lòng nhập URL đầy đủ hoặc đường dẫn tương đối.')

    def _is_valid_url_or_path(self, value):
        """
        Mô tả: Hàm kiểm tra nội bộ để xác định xem một chuỗi có phải là URL hợp lệ hay đường dẫn tương đối.
        """
        if value.startswith(('http://', 'https://')):
            url_pattern = re.compile(
                r'^(?:http)s?://' 
                r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+(?:[A-Z]{2,6}\.?|[A-Z0-9-]{2,}\.?)|'
                r'localhost|'
                r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'
                r'(?::\d+)?'
                r'(?:/?|[/?]\S+)$', re.IGNORECASE)
            return re.match(url_pattern, value) is not None
        
        return True

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
