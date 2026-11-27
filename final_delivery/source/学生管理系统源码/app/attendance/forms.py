from wtforms import DateField, SelectField, StringField, TextAreaField
from wtforms.validators import InputRequired, Length, Optional

from app.record_views import RecordForm, StudentRecordForm, form_choices
from app.services.attendance_service import STATUSES


class AttendanceForm(RecordForm):
    attendance_date = DateField("考勤日期", validators=[InputRequired()])
    period = StringField("节次或时段", validators=[InputRequired(), Length(max=30)])
    status = SelectField("考勤状态", choices=form_choices(STATUSES), validators=[InputRequired()])
    note = TextAreaField("备注", validators=[Optional(), Length(max=255)])


class NewAttendanceForm(AttendanceForm, StudentRecordForm):
    pass
