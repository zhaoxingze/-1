"""Authentication forms keep credential validation on the server."""

from flask_wtf import FlaskForm
from wtforms import PasswordField, StringField, SubmitField
from wtforms.validators import EqualTo, InputRequired, Length


class LoginForm(FlaskForm):
    username = StringField("用户名", validators=[InputRequired("请输入用户名。"), Length(min=1, max=50)])
    password = PasswordField("密码", validators=[InputRequired("请输入密码。"), Length(min=1, max=1024)])
    submit = SubmitField("登录系统")


class ChangePasswordForm(FlaskForm):
    current_password = PasswordField("当前密码", validators=[InputRequired("请输入当前密码。"), Length(max=1024)])
    new_password = PasswordField("新密码", validators=[InputRequired("请输入新密码。"), Length(min=1, max=1024)])
    confirm_password = PasswordField("确认新密码", validators=[InputRequired(), EqualTo("new_password", message="两次新密码不一致。")])
    submit = SubmitField("更新密码")


class ResetPasswordForm(FlaskForm):
    admin_password = PasswordField("你的管理员密码", validators=[InputRequired("请重新验证管理员密码。"), Length(max=1024)])
    new_password = PasswordField("目标账号新密码", validators=[InputRequired("请输入新密码。"), Length(min=1, max=1024)])
    confirm_password = PasswordField("确认新密码", validators=[InputRequired(), EqualTo("new_password", message="两次新密码不一致。")])
    submit = SubmitField("重置目标密码")


class LookupUserForm(FlaskForm):
    username = StringField("目标用户名", validators=[InputRequired("请输入目标用户名。"), Length(min=1, max=50)])
    submit = SubmitField("查找并重置密码")
