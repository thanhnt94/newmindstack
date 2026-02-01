# File: mindstack_app/modules/auth/forms.py
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField, SelectField
from wtforms.validators import DataRequired, EqualTo, ValidationError, Optional, Email
from flask_login import current_user
from .models import User

class LoginForm(FlaskForm):
    """Form đăng nhập."""
    username = StringField('Tên đăng nhập', validators=[DataRequired(message="Vui lòng nhập tên đăng nhập.")])
    password = PasswordField('Mật khẩu', validators=[DataRequired(message="Vui lòng nhập mật khẩu.")])
    remember_me = BooleanField('Ghi nhớ đăng nhập')
    submit = SubmitField('Đăng nhập')

class RegistrationForm(FlaskForm):
    """Form đăng ký."""
    username = StringField('Tên đăng nhập', validators=[DataRequired(message="Vui lòng nhập tên đăng nhập.")])
    email = StringField('Email', validators=[DataRequired(message="Vui lòng nhập email."), Email(message="Email không hợp lệ.")])
    password = PasswordField('Mật khẩu', validators=[DataRequired(message="Vui lòng nhập mật khẩu.")])
    password2 = PasswordField(
        'Nhập lại mật khẩu', validators=[DataRequired(message="Vui lòng xác nhận mật khẩu."), EqualTo('password', message='Mật khẩu không khớp.')])
    submit = SubmitField('Đăng ký')

    def validate_username(self, username):
        user = User.query.filter_by(username=username.data).first()
        if user is not None:
            raise ValidationError('Tên đăng nhập này đã được sử dụng.')

    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if user is not None:
            raise ValidationError('Email này đã được sử dụng.')

class UserForm(FlaskForm):
    """Form quản trị người dùng."""
    username = StringField('Tên đăng nhập', validators=[DataRequired(message="Vui lòng nhập tên đăng nhập.")])
    email = StringField('Email', validators=[DataRequired(message="Vui lòng nhập email."), Email(message="Email không hợp lệ.")])
    password = PasswordField('Mật khẩu', validators=[Optional()])
    password2 = PasswordField('Nhập lại mật khẩu', validators=[Optional()])
    user_role = SelectField('Quyền người dùng', validators=[DataRequired()])
    timezone = SelectField('Múi giờ', validators=[Optional()])
    submit = SubmitField('Lưu')

    def __init__(self, *args, include_anonymous=None, **kwargs):
        super().__init__(*args, **kwargs)
        allow_anonymous = include_anonymous
        if allow_anonymous is None:
            try:
                allow_anonymous = current_user.is_authenticated and current_user.user_role == User.ROLE_ADMIN
            except RuntimeError:
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
            
        common_timezones = [
            ('UTC', 'UTC'),
            ('Asia/Ho_Chi_Minh', 'Vietnam (GMT+7)'),
            ('Asia/Bangkok', 'Bangkok (GMT+7)'),
            ('Asia/Tokyo', 'Tokyo (GMT+9)'),
            ('Asia/Seoul', 'Seoul (GMT+9)'),
            ('Asia/Shanghai', 'Shanghai (GMT+8)'),
            ('Asia/Singapore', 'Singapore (GMT+8)'),
            ('Europe/London', 'London (GMT+0/BST)'),
            ('Europe/Paris', 'Paris (GMT+1/CET)'),
            ('Europe/Berlin', 'Berlin (GMT+1/CET)'),
            ('America/New_York', 'New York (GMT-5/EST)'),
            ('America/Los_Angeles', 'Los Angeles (GMT-8/PST)'),
            ('Australia/Sydney', 'Sydney (GMT+10/AEDT)'),
        ]
        self.timezone.choices = common_timezones
        if not self.timezone.data:
            self.timezone.data = 'UTC'

    def validate_username(self, username_field):
        user_id_to_exclude = None
        if hasattr(self, 'user') and self.user:
            user_id_to_exclude = self.user.user_id
        existing_user = User.query.filter(User.username == username_field.data).first()
        if existing_user and (existing_user.user_id != user_id_to_exclude):
            raise ValidationError('Tên đăng nhập này đã được sử dụng.')

    def validate_email(self, email_field):
        user_id_to_exclude = None
        if hasattr(self, 'user') and self.user:
            user_id_to_exclude = self.user.user_id
        existing_user = User.query.filter(User.email == email_field.data).first()
        if existing_user and (existing_user.user_id != user_id_to_exclude):
            raise ValidationError('Email này đã được sử dụng.')

from flask_wtf.file import FileField, FileAllowed

class ProfileEditForm(FlaskForm):
    """Form cập nhật hồ sơ cá nhân."""
    username = StringField('Tên đăng nhập', validators=[DataRequired(message="Vui lòng nhập tên đăng nhập.")])
    email = StringField('Email', validators=[DataRequired(message="Vui lòng nhập email."), Email(message="Email không hợp lệ.")])
    timezone = SelectField('Múi giờ', validators=[Optional()])
    avatar = FileField('Ảnh đại diện', validators=[
        FileAllowed(['jpg', 'png', 'jpeg', 'gif'], 'Chỉ hỗ trợ ảnh (jpg, png, jpeg, gif)!')
    ])
    submit = SubmitField('Lưu thay đổi')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        common_timezones = [
            ('UTC', 'UTC'),
            ('Asia/Ho_Chi_Minh', 'Vietnam (GMT+7)'),
            ('Asia/Bangkok', 'Bangkok (GMT+7)'),
            ('Asia/Tokyo', 'Tokyo (GMT+9)'),
            ('Asia/Seoul', 'Seoul (GMT+9)'),
            ('Asia/Shanghai', 'Shanghai (GMT+8)'),
            ('Asia/Singapore', 'Singapore (GMT+8)'),
            ('Europe/London', 'London (GMT+0/BST)'),
            ('Europe/Paris', 'Paris (GMT+1/CET)'),
            ('Europe/Berlin', 'Berlin (GMT+1/CET)'),
            ('America/New_York', 'New York (GMT-5/EST)'),
            ('America/Los_Angeles', 'Los Angeles (GMT-8/PST)'),
            ('Australia/Sydney', 'Sydney (GMT+10/AEDT)'),
        ]
        self.timezone.choices = common_timezones

    def validate_username(self, username_field):
        user_id_to_exclude = current_user.user_id if current_user.is_authenticated else None
        existing_user = User.query.filter(User.username == username_field.data).first()
        if existing_user and (existing_user.user_id != user_id_to_exclude):
            raise ValidationError('Tên đăng nhập này đã được sử dụng.')

    def validate_email(self, email_field):
        user_id_to_exclude = current_user.user_id if current_user.is_authenticated else None
        existing_user = User.query.filter(User.email == email_field.data).first()
        if existing_user and (existing_user.user_id != user_id_to_exclude):
            raise ValidationError('Email này đã được sử dụng.')

class ChangePasswordForm(FlaskForm):
    """Form đổi mật khẩu."""
    old_password = PasswordField('Mật khẩu hiện tại', validators=[DataRequired(message="Vui lòng nhập mật khẩu hiện tại.")])
    password = PasswordField('Mật khẩu mới', validators=[DataRequired(message="Vui lòng nhập mật khẩu mới.")])
    password2 = PasswordField('Xác nhận mật khẩu mới', validators=[
        DataRequired(message="Vui lòng xác nhận mật khẩu mới."),
        EqualTo('password', message='Mật khẩu mới không khớp.')
    ])
    submit = SubmitField('Đổi mật khẩu')

    def validate_old_password(self, field):
        if not current_user.check_password(field.data):
            raise ValidationError('Mật khẩu hiện tại không chính xác.')