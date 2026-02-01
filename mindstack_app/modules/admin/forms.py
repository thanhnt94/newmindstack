from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField
from wtforms.validators import DataRequired

class AdminLoginForm(FlaskForm):
    """
    Form đăng nhập dành riêng cho Admin.
    Độc lập với LoginForm của user thường.
    """
    username = StringField('Admin ID', validators=[DataRequired(message="Vui lòng nhập Admin ID")])
    password = PasswordField('Security Key', validators=[DataRequired(message="Vui lòng nhập Security Key")])
    remember_me = BooleanField('Ghi nhớ phiên làm việc')
