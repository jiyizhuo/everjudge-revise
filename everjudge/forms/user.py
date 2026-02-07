from flask_wtf import FlaskForm
from wtforms import SelectField, SubmitField
from wtforms.validators import DataRequired


class UserForm(FlaskForm):
    """
    用户表单：用于编辑用户权限。
    """
    role = SelectField('权限组', validators=[DataRequired()], choices=[
        ('guest', 'Guest (未登录)'),
        ('unauthorized', 'Unauthorized (已登录但未认证)'),
        ('user', 'User (正常用户)'),
        ('admin', 'Admin (管理员)'),
        ('root', 'Root (根用户)')
    ])
    submit = SubmitField('保存')
