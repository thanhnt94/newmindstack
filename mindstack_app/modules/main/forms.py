"""Forms for the main dashboard module."""

from flask_wtf import FlaskForm
from wtforms import IntegerField, SelectField, SubmitField
from wtforms.validators import DataRequired, NumberRange


class GoalForm(FlaskForm):
    """Form used to create or update study goals on the dashboard."""

    goal_type = SelectField('Loại mục tiêu', choices=[], validators=[DataRequired()])
    period = SelectField(
        'Khoảng thời gian',
        choices=[('daily', 'Hôm nay'), ('weekly', '7 ngày qua'), ('total', 'Tổng cộng')],
        validators=[DataRequired()],
    )
    target_value = IntegerField(
        'Giá trị mục tiêu', validators=[DataRequired(), NumberRange(min=1)]
    )
    submit = SubmitField('Lưu mục tiêu')
