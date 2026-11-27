from flask_wtf import FlaskForm
from wtforms import DecimalField, SelectField, StringField, SubmitField, TextAreaField
from wtforms.validators import InputRequired, Length, NumberRange

from app.services.archive_common import MAX_ID


class CourseForm(FlaskForm):
    course_code = StringField("课程编号", validators=[InputRequired(), Length(max=30)])
    course_name = StringField("课程名称", validators=[InputRequired(), Length(max=100)])
    credit = DecimalField("学分", places=None, validators=[InputRequired()], render_kw={"step": "any"})
    teacher_id = SelectField("授课教师", coerce=int, default=0)
    description = TextAreaField("课程说明")
    submit = SubmitField("保存")


class EnrollmentForm(FlaskForm):
    course_id = SelectField("课程", coerce=int, default=0, validate_choice=False,
                            validators=[InputRequired(), NumberRange(min=1, max=MAX_ID, message="请选择课程。")])
    student_id = SelectField("学生", coerce=int, default=0, validate_choice=False,
                             validators=[InputRequired(), NumberRange(min=1, max=MAX_ID, message="请选择学生。")])
    semester = StringField("学期", validators=[InputRequired(), Length(max=30)])
    submit = SubmitField("保存")


class GradeForm(FlaskForm):
    usual_score = DecimalField("平时成绩", places=None, validators=[InputRequired()],
                               render_kw={"min": 0, "max": 100, "step": "any"})
    exam_score = DecimalField("考试成绩", places=None, validators=[InputRequired()],
                              render_kw={"min": 0, "max": 100, "step": "any"})
    submit = SubmitField("保存")
