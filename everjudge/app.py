"""
Flask 应用工厂：根据 config.toml 创建应用，支持多数据库、i18n、插件。
"""
import logging
import os
from flask import Flask
from flask_babel import Babel

from .config import load_config
from .extensions import db, login_manager, migrate
from . import blueprints  # noqa: F401 注册蓝图


def _configure_logging(app: Flask) -> None:
    """根据 DEBUG 配置 logging：调试模式更详细，非调试模式简洁并提高级别。"""
    level = logging.DEBUG if app.config.get("DEBUG") else logging.INFO
    app.logger.setLevel(level)
    # 避免重复添加 handler（Flask 默认已有一个）
    if not app.logger.handlers:
        h = logging.StreamHandler()
        h.setLevel(level)
        app.logger.addHandler(h)
    if app.config.get("DEBUG"):
        fmt = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    else:
        fmt = "%(asctime)s [%(levelname)s] %(message)s"
    for h in app.logger.handlers:
        h.setFormatter(logging.Formatter(fmt))
    # 让第三方库的日志跟随（可选：SQLAlchemy 等）
    logging.getLogger("werkzeug").setLevel(logging.INFO)
    if app.config.get("DEBUG"):
        logging.getLogger("werkzeug").setLevel(logging.DEBUG)
    app.logger.debug("Logging configured: level=%s", logging.getLevelName(level))


def create_app(config_path: str | None = None) -> Flask:
    """根据 TOML 配置创建 Flask 应用。"""
    # 模板与静态文件使用项目根目录下的目录（与 run.py 同层）
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    app = Flask(
        __name__,
        template_folder=os.path.join(root, "templates"),
        static_folder=os.path.join(root, "static"),
        instance_relative_config=True,
    )

    # 加载 TOML 配置
    path = config_path or os.environ.get("EVERJUDGE_CONFIG", "config.toml")
    if not os.path.isabs(path):
        path = os.path.join(os.path.dirname(os.path.dirname(__file__)), path)
    config = load_config(path)
    app.config.from_mapping(config.flask_dict())

    # 先配置日志，便于后续初始化过程打日志
    _configure_logging(app)
    app.logger.info("Config loaded from %s (DEBUG=%s)", path, app.config.get("DEBUG"))

    # 确保数据目录存在
    for key in ("DATA_ROOT", "PROBLEMS_DIR", "SUBMISSIONS_DIR", "BLOG_UPLOADS_DIR"):
        dir_path = app.config.get(key)
        if dir_path:
            os.makedirs(dir_path, exist_ok=True)
            app.logger.debug("Data dir ready: %s=%s", key, dir_path)

    # 数据库连接信息（仅打日志，不输出密码）
    db_uri = app.config.get("SQLALCHEMY_DATABASE_URI", "")
    if "@" in db_uri:
        db_display = db_uri.split("@", 1)[-1]
    else:
        db_display = db_uri.split("///")[-1] if "///" in db_uri else "(hidden)"
    app.logger.info("Database: %s", db_display)

    # 扩展初始化
    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = "auth.login"
    login_manager.login_message = None
    from .models import User
    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(User, int(user_id)) if user_id else None

    migrate.init_app(app, db)

    def get_locale():
        from flask import request
        return (
            request.accept_languages.best_match(
                app.config.get("BABEL_SUPPORTED_LOCALES", ["zh_CN", "en_US"])
            )
            or app.config.get("BABEL_DEFAULT_LOCALE", "zh_CN")
        )

    babel = Babel(app, locale_selector=get_locale)

    @app.context_processor
    def inject_theme():
        return {"theme_primary": app.config.get("THEME_PRIMARY", "#39C5BB")}

    @app.before_request
    def log_request():
        if app.config.get("DEBUG"):
            from flask import request
            app.logger.debug("Request: %s %s", request.method, request.path)

    @app.after_request
    def log_response(response):
        if app.config.get("DEBUG"):
            from flask import request
            app.logger.debug("Response: %s %s -> %d", request.method, request.path, response.status_code)
        return response

    # 注册蓝图
    from .blueprints import register_blueprints
    register_blueprints(app)
    app.logger.debug("Blueprints registered")

    # CLI
    from .cli import register_cli
    register_cli(app)

    # 插件系统（若启用）
    if app.config.get("PLUGINS_ENABLED", False):
        try:
            from .plugins import load_plugins
            load_plugins(app)
            app.logger.info("Plugins loaded from %s", app.config.get("PLUGINS_DIR", "plugins"))
        except Exception as e:
            app.logger.warning("Plugins load skipped: %s", e)

    # 默认 root 用户（根据 config.toml [root] 创建/更新密码）
    try:
        from .bootstrap import ensure_root_user
        ensure_root_user(app)
    except Exception as e:
        app.logger.warning("Bootstrap root user skipped: %s", e)

    app.logger.info("EverJudge app ready (DEBUG=%s)", app.config.get("DEBUG"))
    return app
