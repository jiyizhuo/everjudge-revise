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
        if not (current_user.is_admin or current_user.is_root):
            flash("权限不足", "error")
            return redirect(url_for("main.index"))
        return f(*args, **kwargs)
    return decorated_function
