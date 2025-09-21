# File: Mindstack/web/mindstack_app/modules/auth/forms.py
# Version: 1.5 - Bổ sung quản lý role bằng hằng số và cập nhật form đăng ký/ quản trị người dùng.
# Mục đích: Định nghĩa các lớp form cho Đăng nhập, Đăng ký và quản lý Người dùng.

from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField, SelectField
from wtforms.validators import DataRequired, EqualTo, ValidationError, Optional, Email
from flask_login import current_user
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
    email = StringField('Email', validators=[DataRequired(message="Vui lòng nhập email."), Email(message="Email không hợp lệ.")])
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

    def validate_email(self, email):
        """
        Đảm bảo địa chỉ email chưa được đăng ký.
        """
        user = User.query.filter_by(email=email.data).first()
        if user is not None:
            raise ValidationError('Email này đã được sử dụng.')

class UserForm(FlaskForm):
    """
    Form để thêm hoặc sửa người dùng bởi admin.
    Mật khẩu sẽ được xử lý riêng trong view function tùy thuộc vào là Thêm hay Sửa.
    """
    username = StringField('Tên đăng nhập', validators=[DataRequired(message="Vui lòng nhập tên đăng nhập.")])
    email = StringField('Email', validators=[DataRequired(message="Vui lòng nhập email."), Email(message="Email không hợp lệ.")])
    password = PasswordField('Mật khẩu', validators=[Optional()]) # Luôn Optional trong form
    password2 = PasswordField('Nhập lại mật khẩu', validators=[Optional(), EqualTo('password', message='Mật khẩu không khớp.')]) # Luôn Optional
    user_role = SelectField('Quyền người dùng', validators=[DataRequired()])
    submit = SubmitField('Lưu')

    # Xóa phương thức __init__ tùy chỉnh và original_data_setter.

    def __init__(self, *args, include_anonymous=None, **kwargs):
        super().__init__(*args, **kwargs)
        allow_anonymous = include_anonymous
        if allow_anonymous is None:
            try:
                allow_anonymous = current_user.is_authenticated and current_user.user_role == User.ROLE_ADMIN
            except RuntimeError:
                # Khi form được sử dụng ngoài request context (ví dụ: script CLI)
                allow_anonymous = False

        role_choices = [
            (User.ROLE_USER, User.ROLE_LABELS[User.ROLE_USER]),
            (User.ROLE_FREE, User.ROLE_LABELS[User.ROLE_FREE]),
            (User.ROLE_ADMIN, User.ROLE_LABELS[User.ROLE_ADMIN]),
        ]
        if allow_anonymous:
            role_choices.append((User.ROLE_ANONYMOUS, User.ROLE_LABELS[User.ROLE_ANONYMOUS]))
        self.user_role.choices = role_choices
        if not self.user_role.data:
            self.user_role.data = User.ROLE_FREE

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

