"""
工具函数：通用工具函数和装饰器。
"""
from functools import wraps
from flask import flash, redirect, url_for
from flask_login import current_user


def admin_required(f):
    """
    只允许管理员和根用户访问的装饰器
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            flash("请先登录", "error")
            return redirect(url_for("auth.login"))
        import logging
        from flask import current_app
        logger = logging.getLogger(__name__)
        logger.info("Admin required check: user=%s, role=%s", current_user.username, current_user.role)
        if current_user.is_admin or current_user.is_root:
            logger.info("Access granted: user=%s, role=%s", current_user.username, current_user.role)
            return f(*args, **kwargs)
        logger.warning("Permission denied: user=%s, role=%s", current_user.username, current_user.role)
        flash("权限不足", "error")
        return redirect(url_for("main.index"))
    return decorated_function
