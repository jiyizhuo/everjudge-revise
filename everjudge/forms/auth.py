"""
认证相关表单：登录、注册。
"""
from flask import current_app
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField
from wtforms import SubmitField
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
        render_kw={
            "placeholder": "至少8位，包含大写字母、小写字母、数字、符号中的任意四项",
            "title": "密码至少8位，必须包含以下类型中的任意四项：大写字母、小写字母、数字、ASCII符号、其他Unicode字符"
        }
    )
    password_confirm = PasswordField(
        "确认密码",
        validators=[
            DataRequired(message="请再次输入密码"),
            EqualTo("password", message="两次输入的密码不一致"),
        ],
    )

    def validate_password(self, field):
        min_len = current_app.config.get("PASSWORD_MIN_LENGTH", 8)
        if field.data and len(field.data) < min_len:
            from wtforms import ValidationError
            raise ValidationError(f"密码至少 {min_len} 位")
        
        # 检查密码强度
        import re
        has_upper = bool(re.search(r'[A-Z]', field.data))
        has_lower = bool(re.search(r'[a-z]', field.data))
        has_digit = bool(re.search(r'[0-9]', field.data))
        has_ascii_symbol = bool(re.search(r'[!"#$%&\'()*+,-./:;<=>?@[\\\]^_`{|}~]', field.data))
        has_other_unicode = bool(re.search(r'[^A-Za-z0-9!"#$%&\'()*+,-./:;<=>?@[\\\]^_`{|}~]', field.data))
        
        strength_count = sum([has_upper, has_lower, has_digit, has_ascii_symbol, has_other_unicode])
        if strength_count < 4:
            from wtforms import ValidationError
            raise ValidationError("密码强度不足，至少需要包含大写字母、小写字母、数字、ASCII符号以及其他Unicode字符中的任意四项")
        
        return True


class ForgotPasswordForm(FlaskForm):
    """忘记密码表单。"""
    email = StringField(
        "邮箱",
        validators=[
            DataRequired(message="请输入邮箱"),
            Email(message="请输入有效的邮箱地址"),
        ],
    )
    submit = SubmitField("发送重置链接")


class ResetPasswordForm(FlaskForm):
    """重置密码表单。"""
    password = PasswordField(
        "新密码",
        validators=[DataRequired(message="请输入新密码")],
        render_kw={
            "placeholder": "至少8位，包含大写字母、小写字母、数字、符号中的任意四项",
            "title": "密码至少8位，必须包含以下类型中的任意四项：大写字母、小写字母、数字、ASCII符号、其他Unicode字符"
        }
    )
    password_confirm = PasswordField(
        "确认新密码",
        validators=[
            DataRequired(message="请再次输入新密码"),
            EqualTo("password", message="两次输入的密码不一致"),
        ],
    )
    submit = SubmitField("重置密码")

    def validate_password(self, field):
        min_len = current_app.config.get("PASSWORD_MIN_LENGTH", 8)
        if field.data and len(field.data) < min_len:
            from wtforms import ValidationError
            raise ValidationError(f"密码至少 {min_len} 位")
        
        # 检查密码强度
        import re
        has_upper = bool(re.search(r'[A-Z]', field.data))
        has_lower = bool(re.search(r'[a-z]', field.data))
        has_digit = bool(re.search(r'[0-9]', field.data))
        has_ascii_symbol = bool(re.search(r'[!"#$%&\'()*+,-./:;<=>?@[\\\]^_`{|}~]', field.data))
        has_other_unicode = bool(re.search(r'[^A-Za-z0-9!"#$%&\'()*+,-./:;<=>?@[\\\]^_`{|}~]', field.data))
        
        strength_count = sum([has_upper, has_lower, has_digit, has_ascii_symbol, has_other_unicode])
        if strength_count < 4:
            from wtforms import ValidationError
            raise ValidationError("密码强度不足，至少需要包含大写字母、小写字母、数字、ASCII符号以及其他Unicode字符中的任意四项")
        
        return True
