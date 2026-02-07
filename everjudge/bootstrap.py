"""
应用启动时的一次性初始化：如默认 root 用户。
"""
import logging
from .extensions import db
from .models import User

logger = logging.getLogger(__name__)


def ensure_root_user(app) -> None:
    """确保默认 root 用户存在，并根据 config 同步密码。"""
    root_username = app.config.get("ROOT_USERNAME", "root")
    root_password = app.config.get("ROOT_PASSWORD", "")
    with app.app_context():
        root = db.session.query(User).filter_by(username=root_username).first()
        if root is None:
            root = User(
                username=root_username,
                email=f"{root_username}@localhost",
                nickname=root_username,
                role="admin",
            )
            root.set_password(root_password if root_password else "__disabled__")
            db.session.add(root)
            db.session.commit()
            logger.info("Root user created: username=%s (login_enabled=%s)",
                       root_username, app.config.get("ROOT_LOGIN_ENABLED", True))
        elif root_password:
            root.set_password(root_password)
            db.session.commit()
            logger.info("Root user password updated: username=%s", root_username)
