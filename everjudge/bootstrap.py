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
    logger.info("Starting ensure_root_user: username=%s", root_username)
    with app.app_context():
        try:
            root = db.session.query(User).filter_by(username=root_username).first()
            logger.info("Root user found: %s", root)
            if root is None:
                logger.info("Creating new root user: username=%s", root_username)
                root = User(
                    username=root_username,
                    email=f"{root_username}@localhost",
                    nickname=root_username,
                    role="root",
                )
                root.set_password(root_password if root_password else "__disabled__")
                db.session.add(root)
                db.session.commit()
                logger.info("Root user created: username=%s, role=%s (login_enabled=%s)",
                           root_username, root.role, app.config.get("ROOT_LOGIN_ENABLED", True))
            else:
                logger.info("Existing root user found: username=%s, current role=%s", root_username, root.role)
                # 确保root用户的角色始终为root
                updated = False
                if root.role != "root":
                    logger.info("Updating root user role from %s to root", root.role)
                    root.role = "root"
                    updated = True
                if root_password:
                    logger.info("Updating root user password")
                    root.set_password(root_password)
                    updated = True
                if updated:
                    db.session.commit()
                    logger.info("Root user updated: username=%s, new role=%s", root_username, root.role)
                else:
                    logger.info("Root user already up-to-date: username=%s, role=%s", root_username, root.role)
        except Exception as e:
            logger.error("Error in ensure_root_user: %s", str(e))
            raise
