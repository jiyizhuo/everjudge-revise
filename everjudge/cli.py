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

    @app.cli.group("plugins")
    def plugins_group():
        """插件管理命令组。"""
        pass

    @plugins_group.command("list")
    def plugins_list():
        """列出所有插件。"""
        from .plugins import get_plugin_manager
        try:
            manager = get_plugin_manager()
            plugins = manager.list_plugins()
            if not plugins:
                click.echo("未发现任何插件。")
                return

            click.echo("\n插件列表:")
            click.echo("-" * 60)
            for plugin in plugins:
                status = "已启用" if plugin["enabled"] else ("已加载" if plugin["loaded"] else "已禁用")
                click.echo(f"  {plugin['name']}")
                click.echo(f"    版本: {plugin['version']}")
                click.echo(f"    描述: {plugin['description']}")
                click.echo(f"    状态: {status}")
                click.echo("")
        except RuntimeError:
            click.echo("插件系统未启用或初始化失败。")

    @plugins_group.command("info")
    @click.argument("name")
    def plugins_info(name):
        """显示插件详细信息。"""
        from .plugins import get_plugin_manager
        try:
            manager = get_plugin_manager()
            status = manager.get_plugin_status(name)
            if not status:
                click.echo(f"插件 {name} 未找到。")
                return

            click.echo(f"\n插件: {name}")
            click.echo("-" * 60)
            db_info = status["database"]
            click.echo(f"  版本: {db_info.get('version', '?')}")
            click.echo(f"  描述: {db_info.get('description', '')}")
            click.echo(f"  作者: {db_info.get('author', '?')}")
            click.echo(f"  已启用: {'是' if db_info.get('enabled') else '否'}")
            click.echo(f"  已加载: {'是' if status.get('loaded') else '否'}")
            click.echo(f"  Hooks: {', '.join(db_info.get('hooks', [])) or '无'}")
            click.echo(f"  路径: {status.get('path', '?')}")
        except RuntimeError:
            click.echo("插件系统未启用或初始化失败。")

    @plugins_group.command("enable")
    @click.argument("name")
    def plugins_enable(name):
        """启用插件。"""
        from .plugins import get_plugin_manager
        try:
            manager = get_plugin_manager()
            if manager.enable_plugin(name):
                click.echo(f"插件 {name} 已启用。")
            else:
                click.echo(f"插件 {name} 启用失败，可能不存在。")
        except RuntimeError:
            click.echo("插件系统未启用或初始化失败。")

    @plugins_group.command("disable")
    @click.argument("name")
    def plugins_disable(name):
        """禁用插件。"""
        from .plugins import get_plugin_manager
        try:
            manager = get_plugin_manager()
            if manager.disable_plugin(name):
                click.echo(f"插件 {name} 已禁用。")
            else:
                click.echo(f"插件 {name} 禁用失败，可能不存在。")
        except RuntimeError:
            click.echo("插件系统未启用或初始化失败。")

    return app
