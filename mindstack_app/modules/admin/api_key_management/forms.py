# File: mindstack_app/modules/admin/api_key_management/forms.py
# Phiên bản: 1.0
# Mục đích: Định nghĩa form cho việc thêm và sửa API key.

from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, BooleanField, SubmitField
from wtforms.validators import DataRequired, Optional

class ApiKeyForm(FlaskForm):
    """
    Mô tả: Form để tạo hoặc chỉnh sửa một API key.
    """
    key_value = StringField('Giá trị API Key', 
                            validators=[DataRequired(message="Vui lòng nhập giá trị cho API key.")])
    notes = TextAreaField('Ghi chú', 
                          description='Mô tả mục đích hoặc nguồn gốc của key này (ví dụ: "Key Google AI Studio cá nhân").',
                          validators=[Optional()])
    is_active = BooleanField('Kích hoạt', default=True)
    is_exhausted = BooleanField('Đã cạn kiệt', default=False)
    submit = SubmitField('Lưu API Key')