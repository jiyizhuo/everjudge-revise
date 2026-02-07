"""
认证蓝图：登录、注册、登出。
"""
import logging
from datetime import datetime
from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app
from flask_login import login_user, logout_user, current_user

from ..extensions import db
from ..models import User
from ..forms.auth import LoginForm, RegisterForm

bp = Blueprint("auth", __name__)
logger = logging.getLogger(__name__)


def _root_username():
    return current_app.config.get("ROOT_USERNAME", "root")


@bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("main.index"))
    form = LoginForm()
    if form.validate_on_submit():
        username = form.username.data.strip()
        user = db.session.query(User).filter_by(username=username).first()
        if user is None or not user.check_password(form.password.data):
            logger.info("Login failed: username=%s (user not found or bad password)", username)
            flash("用户名或密码错误", "error")
            return render_template("auth/login.html", form=form)
        if not user.is_active or user.is_banned:
            logger.warning("Login rejected: user=%s disabled or banned", username)
            flash("该账户已被禁用", "error")
            return render_template("auth/login.html", form=form)
        # 配置禁止 root 登录时，拒绝 root 通过登录页登录
        if user.username == _root_username() and not current_app.config.get("ROOT_LOGIN_ENABLED", True):
            logger.info("Login rejected: root login disabled by config")
            flash("当前配置不允许 root 账户登录", "error")
            return render_template("auth/login.html", form=form)
        user.last_login_at = datetime.utcnow()
        db.session.commit()
        login_user(user, remember=form.remember_me.data)
        logger.info("User logged in: id=%s username=%s", user.id, user.username)
        flash("登录成功", "success")
        next_url = request.args.get("next")
        if next_url and next_url.startswith("/"):
            return redirect(next_url)
        return redirect(url_for("main.index"))
    return render_template("auth/login.html", form=form)


@bp.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("main.index"))
    form = RegisterForm()
    if form.validate_on_submit():
        username = form.username.data.strip()
        email = form.email.data.strip().lower()
        if username == _root_username():
            flash("该用户名为系统保留", "error")
            return render_template("auth/register.html", form=form)
        if db.session.query(User).filter_by(username=username).first():
            flash("该用户名已被注册", "error")
            return render_template("auth/register.html", form=form)
        if db.session.query(User).filter_by(email=email).first():
            flash("该邮箱已被注册", "error")
            return render_template("auth/register.html", form=form)
        user = User(
            username=username,
            email=email,
            nickname=(form.nickname.data or "").strip() or username,
        )
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        login_user(user)
        logger.info("User registered: id=%s username=%s email=%s", user.id, user.username, user.email)
        flash("注册成功，已自动登录", "success")
        return redirect(url_for("main.index"))
    return render_template("auth/register.html", form=form)


@bp.route("/logout")
def logout():
    if current_user.is_authenticated:
        logger.info("User logged out: id=%s username=%s", current_user.id, current_user.username)
    logout_user()
    flash("已退出登录", "info")
    return redirect(url_for("main.index"))
