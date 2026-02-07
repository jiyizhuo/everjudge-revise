"""
权限装饰器：要求登录、要求管理员。
"""
from functools import wraps
from flask import redirect, url_for, abort
from flask_login import current_user


def login_required(f):
    """要求已登录（Flask-Login 的 login_required 已处理，此函数供自定义逻辑或复用）。"""
    @wraps(f)
    def inner(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for("auth.login"))
        if getattr(current_user, "is_banned", False):
            abort(403)
        return f(*args, **kwargs)
    return inner


def admin_required(f):
    """要求当前用户为管理员。"""
    @wraps(f)
    def inner(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for("auth.login"))
        if not getattr(current_user, "is_admin", False):
            abort(403)
        return f(*args, **kwargs)
    return inner
