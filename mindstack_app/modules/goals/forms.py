"""Forms used by the learning goals module."""

from __future__ import annotations

from flask_wtf import FlaskForm
from wtforms import DateField, IntegerField, SelectField, StringField, SubmitField, TextAreaField
from wtforms.validators import DataRequired, Length, NumberRange, Optional, ValidationError

from .constants import PERIOD_CHOICES


class LearningGoalForm(FlaskForm):
    """Form used to create or update study goals."""

    goal_type = SelectField('Loại mục tiêu', choices=[], validators=[DataRequired()])
    period = SelectField('Khoảng thời gian', choices=PERIOD_CHOICES, validators=[DataRequired()])
    target_value = IntegerField('Giá trị mục tiêu', validators=[DataRequired(), NumberRange(min=1)])
    title = StringField('Tên mục tiêu', validators=[Optional(), Length(max=120)])
    start_date = DateField('Bắt đầu từ', format='%Y-%m-%d', validators=[Optional()])
    due_date = DateField('Hạn hoàn thành', format='%Y-%m-%d', validators=[Optional()])
    notes = TextAreaField('Ghi chú cá nhân', validators=[Optional(), Length(max=500)])
    submit = SubmitField('Lưu mục tiêu')

    def validate_due_date(self, field: DateField) -> None:  # type: ignore[override]
        if field.data and self.start_date.data and field.data < self.start_date.data:
            raise ValidationError('Hạn hoàn thành phải lớn hơn hoặc bằng ngày bắt đầu.')
