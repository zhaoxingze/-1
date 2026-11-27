from flask_wtf import FlaskForm
from wtforms import PasswordField, SelectField, StringField, SubmitField
from wtforms.validators import EqualTo, InputRequired, Length, Optional


class UserForm(FlaskForm):
    username = StringField("用户名", validators=[InputRequired(), Length(max=50)])
    role = SelectField("角色", validators=[InputRequired()])
    student_id = SelectField("学生档案", coerce=int, default=0, validators=[Optional()], validate_choice=False)
    teacher_id = SelectField("教师档案", coerce=int, default=0, validators=[Optional()], validate_choice=False)
    submit = SubmitField("保存账号")


class CreateUserForm(UserForm):
    password = PasswordField("初始密码", validators=[InputRequired(), Length(max=1024)],
                             render_kw={"autocomplete": "new-password"})
    confirm_password = PasswordField("确认初始密码", validators=[
        InputRequired(), EqualTo("password", message="两次密码不一致。")
    ], render_kw={"autocomplete": "new-password"})
