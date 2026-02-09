from flask_wtf import FlaskForm
from wtforms import SelectField, SubmitField
from wtforms.validators import DataRequired


class UserForm(FlaskForm):
    """
    用户表单：用于编辑用户权限。
    """
    role = SelectField('权限组', validators=[DataRequired()])
    submit = SubmitField('保存')
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from flask_login import current_user
        # 根据当前用户的角色动态调整可用的角色选项
        if current_user.is_root:
            # root用户可以设置所有角色
            self.role.choices = [
                ('guest', 'Guest (未登录)'),
                ('unauthorized', 'Unauthorized (已登录但未认证)'),
                ('user', 'User (正常用户)'),
                ('admin', 'Admin (管理员)'),
                ('root', 'Root (根用户)')
            ]
        else:
            # admin用户只能设置到admin角色，不能设置root角色
            self.role.choices = [
                ('guest', 'Guest (未登录)'),
                ('unauthorized', 'Unauthorized (已登录但未认证)'),
                ('user', 'User (正常用户)'),
                ('admin', 'Admin (管理员)')
            ]
