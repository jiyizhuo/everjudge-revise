"""
认证蓝图：登录、注册、登出。
"""
import logging
import secrets
import string
from datetime import datetime, timedelta
from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app
from flask_login import login_user, logout_user, current_user
from itsdangerous import URLSafeTimedSerializer, SignatureExpired

from ..extensions import db
from ..models import User
from ..forms.auth import LoginForm, RegisterForm, ForgotPasswordForm, ResetPasswordForm

bp = Blueprint("auth", __name__)
logger = logging.getLogger(__name__)


def _root_username():
    return current_app.config.get("ROOT_USERNAME", "root")


def _generate_token(user_id):
    """
    生成重置密码令牌
    """
    serializer = URLSafeTimedSerializer(current_app.config.get("SECRET_KEY"))
    return serializer.dumps(user_id, salt="password-reset-salt")


def _verify_token(token, expiration=3600):
    """
    验证重置密码令牌
    """
    serializer = URLSafeTimedSerializer(current_app.config.get("SECRET_KEY"))
    try:
        user_id = serializer.loads(token, salt="password-reset-salt", max_age=expiration)
        return user_id
    except SignatureExpired:
        return None


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


@bp.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():
    """
    忘记密码页面
    """
    if current_user.is_authenticated:
        return redirect(url_for("main.index"))
    form = ForgotPasswordForm()
    if form.validate_on_submit():
        email = form.email.data.strip().lower()
        user = db.session.query(User).filter_by(email=email).first()
        if user:
            # 生成重置密码令牌
            token = _generate_token(user.id)
            reset_url = url_for("auth.reset_password", token=token, _external=True)
            
            # 这里应该发送邮件，现在只是模拟
            logger.info("Password reset requested for user: id=%s email=%s", user.id, user.email)
            logger.info("Reset URL: %s", reset_url)
            
            # 模拟发送邮件成功
            flash("重置密码链接已发送到您的邮箱，请查收", "success")
            return redirect(url_for("auth.login"))
        else:
            # 即使邮箱不存在，也返回成功信息，防止邮箱枚举攻击
            flash("重置密码链接已发送到您的邮箱，请查收", "success")
            return redirect(url_for("auth.login"))
    return render_template("auth/forgot_password.html", form=form)


@bp.route("/reset-password/<token>", methods=["GET", "POST"])
def reset_password(token):
    """
    重置密码页面
    """
    if current_user.is_authenticated:
        return redirect(url_for("main.index"))
    
    # 验证令牌
    user_id = _verify_token(token)
    if not user_id:
        flash("重置密码链接已过期或无效", "error")
        return redirect(url_for("auth.forgot_password"))
    
    user = db.session.query(User).get(user_id)
    if not user:
        flash("用户不存在", "error")
        return redirect(url_for("auth.forgot_password"))
    
    form = ResetPasswordForm()
    if form.validate_on_submit():
        user.set_password(form.password.data)
        db.session.commit()
        logger.info("Password reset for user: id=%s username=%s", user.id, user.username)
        flash("密码重置成功，请登录", "success")
        return redirect(url_for("auth.login"))
    
    return render_template("auth/reset_password.html", form=form, token=token)
