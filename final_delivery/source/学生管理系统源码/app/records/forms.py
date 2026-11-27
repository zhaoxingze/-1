from wtforms import DateField, DateTimeLocalField, SelectField, StringField, SubmitField, TextAreaField
from wtforms.validators import InputRequired, Length, Optional

from app.record_views import RecordForm, StudentRecordForm, form_choices
from app.services.parent_contact_service import CHANNELS, METHODS
from app.services.reward_service import RECORD_TYPES


class RewardForm(RecordForm):
    record_type = SelectField("记录类型", choices=form_choices(RECORD_TYPES), validators=[InputRequired()])
    category = StringField("类别", validators=[InputRequired(), Length(max=50)])
    description = TextAreaField("事由", validators=[InputRequired()])
    occurred_on = DateField("发生日期", validators=[InputRequired()])


class NewRewardForm(RewardForm, StudentRecordForm):
    pass


class ContactForm(RecordForm):
    method = SelectField("联系方法", choices=form_choices(METHODS), validators=[InputRequired()])
    contacted_at = DateTimeLocalField("联系时间（UTC）", format=["%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M"],
                                      validators=[InputRequired()], render_kw={"step": 1})
    content = TextAreaField("联系内容", validators=[InputRequired()])
    result = TextAreaField("联系结果", validators=[Optional()])


class NewContactForm(ContactForm, StudentRecordForm):
    parent_id = SelectField("关联家长", default=0, coerce=int, validators=[Optional()], validate_choice=False)
    contact_person_name = StringField("临时联系人姓名", validators=[Optional(), Length(max=50)])
    contact_person_phone = StringField("临时联系人电话", validators=[Optional(), Length(max=30)])


class NotificationForm(StudentRecordForm):
    parent_id = SelectField("关联家长", default=0, coerce=int, validators=[Optional()], validate_choice=False)
    channel = SelectField("模拟渠道", choices=form_choices(CHANNELS), validators=[InputRequired()])
    recipient_name = StringField("临时收件人姓名", validators=[Optional(), Length(max=50)])
    recipient_address = StringField("临时接收地址", validators=[Optional(), Length(max=100)])
    content = TextAreaField("通知内容", validators=[InputRequired()])
    submit = SubmitField("创建模拟通知")
