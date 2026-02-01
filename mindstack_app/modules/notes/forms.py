# File: mindstack_app/modules/notes/forms.py
# Phiên bản: 1.0
# Mục đích: Định nghĩa form cho việc tạo và sửa ghi chú.

from flask_wtf import FlaskForm
from wtforms import TextAreaField, SubmitField
from wtforms.validators import DataRequired

class NoteForm(FlaskForm):
    """
    Mô tả: Form để người dùng nhập nội dung ghi chú.
    """
    content = TextAreaField('Nội dung Ghi chú', 
                            validators=[DataRequired(message="Nội dung không được để trống.")])
    submit = SubmitField('Lưu Ghi chú')
