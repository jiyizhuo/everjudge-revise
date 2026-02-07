"""
从 config.toml 加载配置，并转换为 Flask 可用的配置字典。
支持 SQLite / MySQL / MariaDB / Oracle 数据库 URL 构建。
"""
import os
from pathlib import Path
from typing import Any

try:
    import toml
except ImportError:
    toml = None  # type: ignore


def _find_project_root() -> Path:
    """定位项目根目录（含 config.toml 的目录）。"""
    cur = Path(__file__).resolve().parent
    for _ in range(5):
        if (cur / "config.toml").exists():
            return cur
        cur = cur.parent
    return Path.cwd()


def _load_toml(path: str | Path) -> dict[str, Any]:
    path = Path(path)
    if not path.exists():
        return {}
    if toml is None:
        raise RuntimeError("请安装 toml: pip install toml")
    with open(path, "r", encoding="utf-8") as f:
        return toml.load(f)


def _normalize_hex(s: str) -> str:
    """确保为 #RRGGBB 格式。"""
    s = (s or "").strip()
    if not s:
        return "#39C5BB"
    if s.startswith("#"):
        return s if len(s) >= 7 else "#39C5BB"
    return "#" + s if len(s) >= 6 else "#39C5BB"


def _build_sqlalchemy_url(cfg: dict[str, Any], project_root: Path) -> str:
    """根据 database 配置构建 SQLAlchemy 连接 URL。"""
    db = cfg.get("database", {})
    driver = (db.get("driver") or "sqlite").lower().strip()

    if driver == "sqlite":
        raw = db.get("sqlite_path", "data/everjudge.db")
        if not os.path.isabs(raw):
            raw = str(project_root / raw)
        return f"sqlite:///{raw}"

    if driver == "mysql":
        host = db.get("host", "localhost")
        port = db.get("port", 3306)
        user = db.get("username", "root")
        password = db.get("password", "")
        database = db.get("database", "everjudge")
        return f"mysql+pymysql://{user}:{password}@{host}:{port}/{database}"

    if driver == "mariadb":
        host = db.get("host", "localhost")
        port = db.get("port", 3306)
        user = db.get("username", "root")
        password = db.get("password", "")
        database = db.get("database", "everjudge")
        return f"mysql+pymysql://{user}:{password}@{host}:{port}/{database}"

    if driver == "oracle":
        dsn = db.get("dsn", "localhost:1521/ORCL")
        user = db.get("username", "everjudge")
        password = db.get("password", "")
        # 使用 python-oracledb（pip install oracledb），cx_Oracle 已废弃
        return f"oracle+oracledb://{user}:{password}@{dsn}"

    return f"sqlite:///{project_root / 'data' / 'everjudge.db'}"


class AppConfig:
    """封装从 TOML 解析出的配置，并提供 Flask 配置字典。"""

    def __init__(self, raw: dict[str, Any], project_root: Path):
        self.raw = raw
        self.project_root = project_root
        self._sql_url = _build_sqlalchemy_url(raw, project_root)

    def flask_dict(self) -> dict[str, Any]:
        """生成 Flask app.config 可用的字典。"""
        server = self.raw.get("server", {})
        security = self.raw.get("security", {})
        root_cfg = self.raw.get("root", {})
        judge = self.raw.get("judge", {})
        i18n = self.raw.get("i18n", {})
        storage = self.raw.get("storage", {})
        plugins = self.raw.get("plugins", {})
        theme_cfg = self.raw.get("theme", {})

        # 存储路径转为绝对路径
        def abspath(key: str, default: str) -> str:
            p = storage.get(key, default)
            return str(self.project_root / p) if p and not os.path.isabs(p) else p

        data_root = abspath("data_root", "data")
        problems_dir = abspath("problems_dir", "data/problems")
        submissions_dir = abspath("submissions_dir", "data/submissions")
        blog_uploads_dir = abspath("blog_uploads_dir", "data/blog_uploads")

        # 调试模式：环境变量 FLASK_DEBUG=1 可覆盖 config.toml [server] debug
        debug_cfg = server.get("debug", False)
        debug_env = os.environ.get("FLASK_DEBUG", "").strip().lower()
        debug = debug_env in ("1", "true", "yes") if debug_env else bool(debug_cfg)

        return {
            "DEBUG": debug,
            "SERVER_HOST": os.environ.get("HOST") or server.get("host", "0.0.0.0"),
            "SERVER_PORT": str(server.get("port", 5000)),
            "SECRET_KEY": os.environ.get("SECRET_KEY") or security.get("secret_key", "dev-secret"),
            "SQLALCHEMY_DATABASE_URI": os.environ.get("DATABASE_URI") or self._sql_url,
            "SQLALCHEMY_TRACK_MODIFICATIONS": False,
            "SQLALCHEMY_ENGINE_OPTIONS": {"pool_pre_ping": True},
            "SESSION_COOKIE_SECURE": security.get("session_cookie_secure", False),
            "SESSION_COOKIE_HTTPONLY": security.get("session_cookie_httponly", True),
            "PASSWORD_MIN_LENGTH": security.get("password_min_length", 6),
            "ROOT_USERNAME": (root_cfg.get("username") or "root").strip() or "root",
            "ROOT_PASSWORD": (root_cfg.get("password") or "").strip(),
            "ROOT_LOGIN_ENABLED": bool(root_cfg.get("login_enabled", True)),
            "JUDGE_RPC_HOST": judge.get("rpc_host", "127.0.0.1"),
            "JUDGE_RPC_PORT": judge.get("rpc_port", 3726),
            "BABEL_DEFAULT_LOCALE": i18n.get("default_locale", "zh_CN"),
            "BABEL_SUPPORTED_LOCALES": i18n.get("supported_locales", ["zh_CN", "en_US"]),
            "DATA_ROOT": data_root,
            "PROBLEMS_DIR": problems_dir,
            "SUBMISSIONS_DIR": submissions_dir,
            "BLOG_UPLOADS_DIR": blog_uploads_dir,
            "PLUGINS_ENABLED": plugins.get("enabled", True),
            "PLUGINS_DIR": abspath("plugins_dir", "plugins")
            if plugins.get("plugins_dir")
            else str(self.project_root / "plugins"),
            "THEME_PRIMARY": _normalize_hex((theme_cfg.get("primary") or "#39C5BB").strip()),
        }


def load_config(config_path: str | Path) -> AppConfig:
    """加载 config.toml 并返回 AppConfig。"""
    path = Path(config_path)
    if not path.is_absolute():
        path = _find_project_root() / path
    raw = _load_toml(path)
    root = path.parent if path.name == "config.toml" else path
    return AppConfig(raw, root)
