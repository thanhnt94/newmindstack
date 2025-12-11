"""Forms used by the learning goals module."""

from __future__ import annotations

from flask_wtf import FlaskForm
from wtforms import DateField, IntegerField, SelectField, StringField, SubmitField, TextAreaField, HiddenField
from wtforms.validators import DataRequired, Length, NumberRange, Optional, ValidationError

from .constants import PERIOD_CHOICES, DOMAIN_CHOICES, SCOPE_CHOICES

class LearningGoalForm(FlaskForm):
    """Form used to create or update study goals."""

    # Enhanced fields
    domain = SelectField('Lĩnh vực', choices=DOMAIN_CHOICES, default='general', validators=[DataRequired()])
    scope = SelectField('Phạm vi', choices=SCOPE_CHOICES, default='global', validators=[DataRequired()])
    metric = SelectField('Tiêu chí', choices=[], validate_choice=False) # Dynamic choices via JS
    reference_id = HiddenField('Container ID') # Populated via JS selector

    period = SelectField('Chu kỳ', choices=PERIOD_CHOICES, default='daily', validators=[DataRequired()])
    target_value = IntegerField('Mục tiêu', validators=[DataRequired(), NumberRange(min=1)])
    
    title = StringField('Tên mục tiêu', validators=[Optional(), Length(max=120)])
    description = TextAreaField('Mô tả', validators=[Optional(), Length(max=255)])
    
    start_date = DateField('Bắt đầu từ', format='%Y-%m-%d', validators=[Optional()])
    due_date = DateField('Hạn hoàn thành', format='%Y-%m-%d', validators=[Optional()])
    
    notes = TextAreaField('Ghi chú cá nhân', validators=[Optional(), Length(max=500)])
    
    submit = SubmitField('Lưu mục tiêu')

    def validate_due_date(self, field: DateField) -> None:  # type: ignore[override]
        if field.data and self.start_date.data and field.data < self.start_date.data:
            raise ValidationError('Hạn hoàn thành phải lớn hơn hoặc bằng ngày bắt đầu.')

    def validate_reference_id(self, field: HiddenField) -> None:
        if self.scope.data == 'container' and not field.data:
             raise ValidationError('Vui lòng chọn bộ học liệu áp dụng.')
