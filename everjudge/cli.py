"""
Flask CLI 命令：创建管理员等。
"""
import click
from .extensions import db
from .models import User


def register_cli(app):
    @app.cli.command("create-admin")
    @click.option("--username", default="admin", help="管理员用户名")
    @click.option("--password", prompt=True, hide_input=True, confirmation_prompt=True, help="密码")
    @click.option("--email", default="admin@localhost", help="邮箱")
    def create_admin(username, password, email):
        """创建管理员账户（若已存在则改为管理员角色）。"""
        user = db.session.query(User).filter_by(username=username).first()
        if user:
            user.role = "admin"
            user.is_active = True
            flash_msg = f"用户 {username} 已设为管理员"
        else:
            user = User(username=username, email=email, nickname=username, role="admin")
            user.set_password(password)
            db.session.add(user)
            flash_msg = f"管理员 {username} 已创建"
        db.session.commit()
        click.echo(flash_msg)
    return app
