# File: Mindstack/web/mindstack_app/modules/my_content/flashcards/forms.py
# Version: 1.1 - Đã thêm các trường AI và upload Excel vào form.
# Mục đích: Định nghĩa các form để quản lý bộ Flashcard và thẻ Flashcard.

from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, BooleanField, SubmitField, URLField, FileField
from wtforms.validators import DataRequired, Length, Optional
from flask_wtf.file import FileAllowed # Để xác thực loại file

class FlashcardSetForm(FlaskForm):
    """
    Form để tạo hoặc sửa một bộ Flashcard (LearningContainer).
    """
    title = StringField('Tiêu đề bộ thẻ', validators=[DataRequired(message="Vui lòng nhập tiêu đề bộ thẻ."), Length(max=255)])
    description = TextAreaField('Mô tả', validators=[Optional()])
    tags = StringField('Thẻ (cách nhau bởi dấu phẩy)', validators=[Optional(), Length(max=255)])
    is_public = BooleanField('Công khai (người khác có thể tìm thấy và học)')
    
    # TRƯỜNG MỚI: AI Prompt Tùy chỉnh cho bộ thẻ
    ai_prompt = TextAreaField('AI Prompt Tùy chỉnh (cho bộ thẻ)', 
                              description='Nhập prompt tùy chỉnh để AI tạo thẻ. Nếu để trống, hệ thống sẽ sử dụng prompt mặc định.',
                              validators=[Optional()])
    
    # TRƯỜNG MỚI: Upload file Excel
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
    
    # Các trường tùy chọn cho audio và hình ảnh
    front_audio_content = TextAreaField('Văn bản tạo âm thanh mặt trước (TTS)', validators=[Optional()])
    front_audio_url = URLField('URL file âm thanh mặt trước', validators=[Optional()])
    
    back_audio_content = TextAreaField('Văn bản tạo âm thanh mặt sau (TTS)', validators=[Optional()])
    back_audio_url = URLField('URL file âm thanh mặt sau', validators=[Optional()])
    
    front_img = URLField('URL hình ảnh mặt trước', validators=[Optional()])
    back_img = URLField('URL hình ảnh mặt sau', validators=[Optional()])

    # TRƯỜNG MỚI: Nội dung giải thích do AI (chỉ để hiển thị, không cho sửa trực tiếp qua form này)
    ai_explanation = TextAreaField('Giải thích AI', render_kw={'readonly': True}, validators=[Optional()])

    submit = SubmitField('Lưu thẻ')
