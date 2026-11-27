"""Server-side archive forms; status and archive flags are never edit fields."""

from flask_wtf import FlaskForm
from wtforms import BooleanField, DateField, SelectField, StringField, SubmitField, TextAreaField
from wtforms.validators import DataRequired, InputRequired, Length, Optional
from wtforms.fields import SelectChoice


class StudentForm(FlaskForm):
    student_no=StringField("学号",validators=[InputRequired("请输入学号。"),Length(max=30)])
    name=StringField("姓名",validators=[InputRequired("请输入姓名。"),Length(max=50)])
    gender=StringField("性别",validators=[InputRequired("请输入性别。"),Length(max=10)])
    birth_date=DateField("出生日期",validators=[Optional()],format="%Y-%m-%d")
    phone=StringField("联系电话",validators=[Optional(),Length(max=30)])
    address=TextAreaField("家庭住址",validators=[Optional(),Length(max=255)])
    class_id=SelectField("班级",coerce=int,default=0)
    enrollment_date=DateField("入学日期",validators=[InputRequired("请选择入学日期。")],format="%Y-%m-%d")
    submit=SubmitField("保存学生档案")


class TeacherForm(FlaskForm):
    teacher_no=StringField("教师编号",validators=[InputRequired("请输入教师编号。"),Length(max=30)])
    name=StringField("姓名",validators=[InputRequired("请输入姓名。"),Length(max=50)])
    phone=StringField("联系电话",validators=[Optional(),Length(max=30)])
    email=StringField("邮箱",validators=[Optional(),Length(max=100)])
    submit=SubmitField("保存教师档案")


class ClassForm(FlaskForm):
    class_name=StringField("班级名称",validators=[InputRequired("请输入班级名称。"),Length(max=50)])
    grade=StringField("年级",validators=[InputRequired("请输入年级。"),Length(max=30)])
    homeroom_teacher_id=SelectField("班主任",coerce=int,default=0)
    submit=SubmitField("保存班级")


class ParentForm(FlaskForm):
    name=StringField("家长姓名",validators=[InputRequired("请输入家长姓名。"),Length(max=50)])
    relationship=SelectField("与学生关系",choices=[SelectChoice(value=code,label=label) for code,label in [("father","父亲"),("mother","母亲"),("guardian","监护人"),("other","其他")]])
    phone=StringField("联系电话",validators=[InputRequired("请输入联系电话。"),Length(max=30)])
    email=StringField("邮箱",validators=[Optional(),Length(max=100)])
    is_primary=BooleanField("设为主要联系人")
    submit=SubmitField("保存家长档案")


class StatusForm(FlaskForm):
    status=SelectField("新学籍状态",validators=[InputRequired("请选择有效的后续状态。")])
    submit=SubmitField("确认变更学籍")


class ConfirmForm(FlaskForm):
    confirm=BooleanField("我已核对信息，确认执行此操作",validators=[DataRequired("请先勾选确认。")])
    submit=SubmitField("确认执行")
