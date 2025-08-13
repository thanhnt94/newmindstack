# File: Mindstack/web/mindstack_app/modules/auth/forms.py
# Version: 1.3 - Đã sửa UserForm để tách biệt rõ ràng logic Add/Edit
# Mục đích: Định nghĩa các lớp form cho Đăng nhập, Đăng ký và quản lý Người dùng.

from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField, SelectField
from wtforms.validators import DataRequired, EqualTo, ValidationError, Optional
from ...models import User 

class LoginForm(FlaskForm):
    """
    Form đăng nhập.
    """
    username = StringField('Tên đăng nhập', validators=[DataRequired(message="Vui lòng nhập tên đăng nhập.")])
    password = PasswordField('Mật khẩu', validators=[DataRequired(message="Vui lòng nhập mật khẩu.")])
    remember_me = BooleanField('Ghi nhớ đăng nhập')
    submit = SubmitField('Đăng nhập')

class RegistrationForm(FlaskForm):
    """
    Form đăng ký.
    """
    username = StringField('Tên đăng nhập', validators=[DataRequired(message="Vui lòng nhập tên đăng nhập.")])
    password = PasswordField('Mật khẩu', validators=[DataRequired(message="Vui lòng nhập mật khẩu.")]) 
    password2 = PasswordField(
        'Nhập lại mật khẩu', validators=[DataRequired(message="Vui lòng xác nhận mật khẩu."), EqualTo('password', message='Mật khẩu không khớp.')]) 
    submit = SubmitField('Đăng ký')

    def validate_username(self, username):
        """
        Kiểm tra xem tên đăng nhập đã tồn tại trong database chưa.
        """
        user = User.query.filter_by(username=username.data).first()
        if user is not None:
            raise ValidationError('Tên đăng nhập này đã được sử dụng.')

class UserForm(FlaskForm):
    """
    Form để thêm hoặc sửa người dùng bởi admin.
    Mật khẩu sẽ được xử lý riêng trong view function tùy thuộc vào là Thêm hay Sửa.
    """
    username = StringField('Tên đăng nhập', validators=[DataRequired(message="Vui lòng nhập tên đăng nhập.")])
    password = PasswordField('Mật khẩu', validators=[Optional()]) # Luôn Optional trong form
    password2 = PasswordField('Nhập lại mật khẩu', validators=[Optional(), EqualTo('password', message='Mật khẩu không khớp.')]) # Luôn Optional
    user_role = SelectField('Quyền người dùng', choices=[('user', 'Người dùng'), ('admin', 'Quản trị viên')], validators=[DataRequired()])
    submit = SubmitField('Lưu')

    # Xóa phương thức __init__ tùy chỉnh và original_data_setter.

    def validate_username(self, username_field):
        """
        Kiểm tra xem tên đăng nhập đã tồn tại trong database chưa (trừ chính người dùng đang sửa nếu có).
        """
        user_id_to_exclude = None
        # Nếu form được dùng để sửa, user object sẽ được gán vào self.user từ view function
        if hasattr(self, 'user') and self.user:
            user_id_to_exclude = self.user.user_id

        # Kiểm tra nếu username đã tồn tại và không phải là username của người dùng đang được sửa
        existing_user = User.query.filter(User.username == username_field.data).first()
        if existing_user and (existing_user.user_id != user_id_to_exclude):
            raise ValidationError('Tên đăng nhập này đã được sử dụng.')

