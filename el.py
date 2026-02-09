#!/usr/bin/env python3
"""
EverLaunch - EverJudge CLI 工具
整合所有CLI命令，提供独立的命令行入口
"""
import sys
import os

# 确保项目根目录在路径中
project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)


def print_banner():
    """打印欢迎横幅"""
    banner = """
╔════════════════════════════════════════════════════════════╗
║                    EverJudge Launcher                      ║
║                    EverLaunch v1.0.0                       ║
╠════════════════════════════════════════════════════════════════╣
║  功能: 启动服务、管理数据库、管理插件、管理用户等           ║
╚════════════════════════════════════════════════════════════╝
    """
    print(banner)


def print_help():
    """打印帮助信息"""
    help_text = """
用法: python el.py <命令> [选项]

可用命令:
  启动服务:
    run              启动开发服务器 (默认端口 5000)
    run --port 8080  指定端口启动
    run --debug      启用调试模式
    wsgi             启动 uWSGI 生产服务器

  数据库:
    db init          初始化数据库迁移
    db migrate       生成迁移脚本
    db upgrade       应用迁移到数据库
    db downgrade     回滚迁移
    db stamp         将数据库标记为特定版本

  用户管理:
    create-admin --username <用户名> --email <邮箱>  创建管理员账户
    create-user --username <用户名> --email <邮箱>   创建普通用户

  插件管理:
    plugins list                         列出所有插件
    plugins info <插件名>                 显示插件详情
    plugins enable <插件名>               启用插件
    plugins disable <插件名>              禁用插件
    plugins install <插件路径>            安装插件
    plugins uninstall <插件名>            卸载插件

  评测机:
    judge start          启动评测机服务
    judge start --port 3726  指定端口启动

  系统信息:
    status               显示系统状态
    version              显示版本信息

  其他:
    shell                启动 Python shell (需安装 ipython)
    routes               列出所有路由

示例:
    python el.py run --port 5000 --debug
    python el.py db migrate -m "添加新表"
    python el.py create-admin --username admin --email admin@example.com
    python el.py plugins list
    python el.py plugins enable hello_world
"""
    print(help_text)


def run_server(port: int = 5000, debug: bool = False, use_reloader: bool = True):
    """启动Flask开发服务器"""
    os.environ['FLASK_DEBUG'] = '1' if debug else '0'
    os.environ['EVERJUDGE_CONFIG'] = os.path.join(project_root, 'config.toml')

    from everjudge.app import create_app
    app = create_app()
    print(f"启动EverJudge开发服务器...")
    print(f"  端口: {port}")
    print(f"  调试: {'启用' if debug else '禁用'}")
    print(f"  访问: http://0.0.0.0:{port}")
    app.run(host='0.0.0.0', port=port, debug=debug, use_reloader=use_reloader)


def run_wsgi():
    """启动uWSGI生产服务器"""
    print("使用 uWSGI 启动...")
    print("配置文件: uwsgi.ini")
    os.system('uwsgi --ini uwsgi.ini')


def create_admin(username: str, email: str, password: str = None):
    """创建管理员"""
    from everjudge.extensions import db
    from everjudge.models import User

    if not password:
        import getpass
        password = getpass.getpass("密码: ")
        confirm = getpass.getpass("确认密码: ")
        if password != confirm:
            print("错误: 密码不匹配")
            return False

    user = db.session.query(User).filter_by(username=username).first()
    if user:
        user.role = "admin"
        print(f"用户 {username} 已设为管理员")
    else:
        user = User(username=username, email=email, nickname=username, role="admin")
        user.set_password(password)
        db.session.add(user)
        print(f"管理员 {username} 已创建")

    db.session.commit()
    return True


def db_command(cmd: str, *args):
    """数据库迁移命令"""
    sys.argv = ['flask', cmd] + list(args)
    from flask_migrate.cli import db

    if cmd == 'init':
        os.chdir(project_root)
        from flask import Flask
        from everjudge.app import create_app
        from everjudge.extensions import db, migrate

        app = create_app()
        migrate.init_app(app, db)
        db.init_app(app)

        print("初始化数据库迁移...")
        db.init_app(app)
    else:
        from flask.cli import main as flask_main
        sys.argv[0] = 'flask'
        flask_main()


def plugins_command(subcmd: str, *args):
    """插件管理命令"""
    os.environ['FLASK_DEBUG'] = '0'
    os.environ['EVERJUDGE_CONFIG'] = os.path.join(project_root, 'config.toml')

    if subcmd == 'list':
        from everjudge.plugins import get_plugin_manager
        from everjudge import create_app

        app = create_app()
        with app.app_context():
            try:
                manager = get_plugin_manager()
                plugins = manager.list_plugins()
                if not plugins:
                    print("未发现任何插件。")
                    return

                print("\n插件列表:")
                print("-" * 60)
                for plugin in plugins:
                    status = "已启用" if plugin["enabled"] else ("已加载" if plugin["loaded"] else "已禁用")
                    print(f"  {plugin['name']}")
                    print(f"    版本: {plugin['version']}")
                    print(f"    描述: {plugin['description']}")
                    print(f"    状态: {status}")
                    print("")
            except RuntimeError:
                print("插件系统未启用或初始化失败。")

    elif subcmd == 'info':
        if not args:
            print("用法: el.py plugins info <插件名>")
            return
        name = args[0]

        from everjudge.plugins import get_plugin_manager
        from everjudge import create_app

        app = create_app()
        with app.app_context():
            try:
                manager = get_plugin_manager()
                status = manager.get_plugin_status(name)
                if not status:
                    print(f"插件 {name} 未找到。")
                    return

                print(f"\n插件: {name}")
                print("-" * 60)
                db_info = status["database"]
                print(f"  版本: {db_info.get('version', '?')}")
                print(f"  描述: {db_info.get('description', '')}")
                print(f"  作者: {db_info.get('author', '?')}")
                print(f"  已启用: {'是' if db_info.get('enabled') else '否'}")
                print(f"  已加载: {'是' if status.get('loaded') else '否'}")
                print(f"  Hooks: {', '.join(db_info.get('hooks', [])) or '无'}")
                print(f"  路径: {status.get('path', '?')}")
            except RuntimeError:
                print("插件系统未启用或初始化失败。")

    elif subcmd == 'enable':
        if not args:
            print("用法: el.py plugins enable <插件名>")
            return
        name = args[0]

        from everjudge.plugins import get_plugin_manager
        from everjudge import create_app

        app = create_app()
        with app.app_context():
            try:
                manager = get_plugin_manager()
                if manager.enable_plugin(name):
                    print(f"插件 {name} 已启用。")
                else:
                    print(f"插件 {name} 启用失败，可能不存在。")
            except RuntimeError:
                print("插件系统未启用或初始化失败。")

    elif subcmd == 'disable':
        if not args:
            print("用法: el.py plugins disable <插件名>")
            return
        name = args[0]

        from everjudge.plugins import get_plugin_manager
        from everjudge import create_app

        app = create_app()
        with app.app_context():
            try:
                manager = get_plugin_manager()
                if manager.disable_plugin(name):
                    print(f"插件 {name} 已禁用。")
                else:
                    print(f"插件 {name} 禁用失败，可能不存在。")
            except RuntimeError:
                print("插件系统未启用或初始化失败。")

    elif subcmd == 'install':
        if not args:
            print("用法: el.py plugins install <插件路径>")
            return
        path = args[0]

        from everjudge.plugins import get_plugin_manager
        from everjudge import create_app

        app = create_app()
        with app.app_context():
            try:
                manager = get_plugin_manager()
                plugin_name = os.path.basename(os.path.abspath(path))
                if manager.install_plugin(plugin_name):
                    print(f"插件 {plugin_name} 已安装。")
                else:
                    print(f"插件 {plugin_name} 安装失败。")
            except RuntimeError:
                print("插件系统未启用或初始化失败。")

    elif subcmd == 'uninstall':
        if not args:
            print("用法: el.py plugins uninstall <插件名>")
            return
        name = args[0]

        from everjudge.plugins import get_plugin_manager
        from everjudge import create_app

        app = create_app()
        with app.app_context():
            try:
                manager = get_plugin_manager()
                if manager.uninstall_plugin(name):
                    print(f"插件 {name} 已卸载。")
                else:
                    print(f"插件 {name} 卸载失败。")
            except RuntimeError:
                print("插件系统未启用或初始化失败。")

    else:
        print(f"未知插件命令: {subcmd}")
        print("可用命令: list, info, enable, disable, install, uninstall")


def judge_command(subcmd: str, *args):
    """评测机管理命令"""
    judge_backend_dir = os.path.join(project_root, 'judge-backend')

    if subcmd == 'start':
        port = 3726
        for i, arg in enumerate(args):
            if arg == '--port' and i + 1 < len(args):
                try:
                    port = int(args[i + 1])
                except ValueError:
                    print(f"错误: 无效端口 {args[i + 1]}")
                    return

        if not os.path.isdir(judge_backend_dir):
            print("错误: 评测机后端目录不存在")
            return

        import subprocess
        print(f"启动评测机服务...")
        print(f"  端口: {port}")
        print(f"  目录: {judge_backend_dir}")

        os.chdir(judge_backend_dir)
        env = os.environ.copy()
        env['JUDGE_PORT'] = str(port)

        subprocess.run(['cargo', 'run'], env=env)

    elif subcmd == 'build':
        if not os.path.isdir(judge_backend_dir):
            print("错误: 评测机后端目录不存在")
            return

        import subprocess
        print("构建评测机...")
        os.chdir(judge_backend_dir)
        subprocess.run(['cargo', 'build', '--release'])

    elif subcmd == 'status':
        print("获取评测机状态...")
        print("请启动评测机后端后查看日志")

    else:
        print(f"未知评测机命令: {subcmd}")
        print("可用命令: start, build, status")


def show_status():
    """显示系统状态"""
    print("\n" + "=" * 60)
    print("EverJudge 系统状态")
    print("=" * 60)

    import os
    import json

    config_path = os.path.join(project_root, 'config.toml')
    print(f"\n配置文件: {config_path}")
    print(f"配置文件存在: {'是' if os.path.exists(config_path) else '否'}")

    data_dir = os.path.join(project_root, 'data')
    print(f"\n数据目录: {data_dir}")
    print(f"数据目录存在: {'是' if os.path.exists(data_dir) else '否'}")

    from everjudge import create_app
    from everjudge.extensions import db
    from everjudge.models import User

    app = create_app()
    with app.app_context():
        user_count = User.query.count()
        print(f"\n用户数量: {user_count}")

        try:
            from everjudge.plugins import get_plugin_manager
            manager = get_plugin_manager()
            plugins = manager.list_plugins()
            enabled = sum(1 for p in plugins if p['enabled'])
            print(f"插件数量: {len(plugins)} (已启用: {enabled})")
        except RuntimeError:
            print("插件系统: 未启用")

    print(f"\nPython 版本: {sys.version.split()[0]}")
    print(f"项目根目录: {project_root}")
    print("=" * 60)


def show_version():
    """显示版本信息"""
    version_info = {
        "name": "EverJudge",
        "version": "1.0.0",
        "launcher": "EverLaunch",
        "launcher_version": "1.0.0",
        "phases": ["Phase 1-4 ✅", "Phase 5 ✅", "Phase 6-7 📅"],
    }

    print(f"""
╔════════════════════════════════════════════════════════════╗
║                    EverJudge                               ║
║                    版本 {version_info['version']}                              ║
╠════════════════════════════════════════════════════════════════╣
║  Launcher: EverLaunch v{version_info['launcher_version']}                         ║
║  实现阶段: {version_info['phases'][0]}, {version_info['phases'][1]}, {version_info['phases'][2]}       ║
╚════════════════════════════════════════════════════════════╝
    """)


def main():
    """主函数"""
    print_banner()

    if len(sys.argv) < 2:
        print_help()
        return

    cmd = sys.argv[1]

    if cmd in ['-h', '--help', 'help']:
        print_help()
        return

    if cmd == 'version':
        show_version()
        return

    if cmd == 'status':
        show_status()
        return

    if cmd == 'run':
        port = 5000
        debug = False
        use_reloader = True

        i = 2
        while i < len(sys.argv):
            if sys.argv[i] == '--port' and i + 1 < len(sys.argv):
                try:
                    port = int(sys.argv[i + 1])
                except ValueError:
                    print(f"错误: 无效端口 {sys.argv[i + 1]}")
                    return
                i += 2
            elif sys.argv[i] == '--debug':
                debug = True
                i += 1
            elif sys.argv[i] == '--no-reload':
                use_reloader = False
                i += 1
            else:
                print(f"未知参数: {sys.argv[i]}")
                return

        run_server(port=port, debug=debug, use_reloader=use_reloader)
        return

    if cmd == 'wsgi':
        run_wsgi()
        return

    if cmd == 'db':
        if len(sys.argv) < 3:
            print("用法: el.py db <命令>")
            print("可用命令: init, migrate, upgrade, downgrade, stamp")
            return
        db_command(sys.argv[2], *sys.argv[3:])
        return

    if cmd == 'create-admin':
        username = 'admin'
        email = 'admin@localhost'
        password = None

        i = 2
        while i < len(sys.argv):
            if sys.argv[i] == '--username' and i + 1 < len(sys.argv):
                username = sys.argv[i + 1]
                i += 2
            elif sys.argv[i] == '--email' and i + 1 < len(sys.argv):
                email = sys.argv[i + 1]
                i += 2
            elif sys.argv[i] == '--password' and i + 1 < len(sys.argv):
                password = sys.argv[i + 1]
                i += 2
            else:
                i += 1

        create_admin(username, email, password)
        return

    if cmd == 'plugins':
        if len(sys.argv) < 3:
            print("用法: el.py plugins <命令>")
            print("可用命令: list, info, enable, disable, install, uninstall")
            return
        plugins_command(sys.argv[2], *sys.argv[3:])
        return

    if cmd == 'judge':
        if len(sys.argv) < 3:
            print("用法: el.py judge <命令>")
            print("可用命令: start, build, status")
            return
        judge_command(sys.argv[2], *sys.argv[3:])
        return

    if cmd == 'shell':
        try:
            from IPython import start_ipython
            argv = ['--no-banner', '--no-confirm-exit']
            start_ipython(argv=argv)
        except ImportError:
            print("错误: 未安装 IPython")
            print("请运行: pip install ipython")
        return

    if cmd == 'routes':
        from everjudge import create_app
        app = create_app()
        print("\n已注册路由:")
        print("-" * 60)
        for rule in app.url_map.iter_rules():
            methods = ','.join(sorted(rule.methods - {'HEAD', 'OPTIONS'}))
            print(f"  {methods:15} {rule.rule}")
        return

    print(f"未知命令: {cmd}")
    print("运行 'python el.py --help' 查看帮助")


if __name__ == '__main__':
    main()
