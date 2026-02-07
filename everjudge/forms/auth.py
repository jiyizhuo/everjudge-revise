"""
认证相关表单：登录、注册。
"""
from flask import current_app
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField
from wtforms.validators import DataRequired, Email, EqualTo, Length, Optional


class LoginForm(FlaskForm):
    """登录表单。"""
    username = StringField("用户名", validators=[DataRequired(message="请输入用户名")])
    password = PasswordField("密码", validators=[DataRequired(message="请输入密码")])
    remember_me = BooleanField("记住我", default=False)


class RegisterForm(FlaskForm):
    """注册表单。"""
    username = StringField(
        "用户名",
        validators=[
            DataRequired(message="请输入用户名"),
            Length(min=2, max=64, message="用户名长度应为 2～64 个字符"),
        ],
    )
    email = StringField(
        "邮箱",
        validators=[
            DataRequired(message="请输入邮箱"),
            Email(message="请输入有效的邮箱地址"),
        ],
    )
    nickname = StringField("昵称", validators=[Optional(), Length(max=64)])
    password = PasswordField(
        "密码",
        validators=[DataRequired(message="请输入密码")],
    )
    password_confirm = PasswordField(
        "确认密码",
        validators=[
            DataRequired(message="请再次输入密码"),
            EqualTo("password", message="两次输入的密码不一致"),
        ],
    )

    def validate_password(self, field):
        min_len = current_app.config.get("PASSWORD_MIN_LENGTH", 6)
        if field.data and len(field.data) < min_len:
            from wtforms import ValidationError
            raise ValidationError(f"密码至少 {min_len} 位")
        return True
