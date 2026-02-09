"""
管理蓝图：用户管理、权限管理等。
"""
from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import current_user, login_required

from ..extensions import db
from ..models import User
from ..forms import UserForm
from ..utils import admin_required


bp = Blueprint("admin", __name__)


@bp.route("/users")
@login_required
@admin_required
def users():
    """
    用户管理页面
    """
    users = User.query.all()
    return render_template("admin/users.html", users=users)


@bp.route("/users/<int:id>/edit", methods=["GET", "POST"])
@login_required
@admin_required
def edit_user(id):
    """
    编辑用户页面
    """
    user = User.query.get_or_404(id)
    if user.is_root and not current_user.is_root:
        flash("权限不足，无法修改根用户权限", "error")
        return redirect(url_for("admin.users"))
    form = UserForm(obj=user)
    if form.validate_on_submit():
        if form.role.data == "root" and not current_user.is_root:
            flash("权限不足，无法赋予其他用户根用户权限", "error")
            return redirect(url_for("admin.users"))
        user.role = form.role.data
        db.session.commit()
        flash("用户权限更新成功", "success")
        return redirect(url_for("admin.users"))
    return render_template("admin/edit_user.html", form=form, user=user)


@bp.route("/plugins")
@login_required
@admin_required
def plugins():
    """
    插件管理页面
    """
    from ..plugins import get_plugin_manager
    try:
        manager = get_plugin_manager()
        plugins_list = manager.list_plugins()
    except RuntimeError:
        plugins_list = []
    return render_template("admin/plugins.html", plugins=plugins_list)


@bp.route("/plugins/<name>/enable", methods=["POST"])
@login_required
@admin_required
def enable_plugin(name):
    """
    启用插件
    """
    from ..plugins import get_plugin_manager
    try:
        manager = get_plugin_manager()
        if manager.enable_plugin(name):
            flash(f"插件 {name} 已启用", "success")
        else:
            flash(f"插件 {name} 启用失败", "error")
    except RuntimeError:
        flash("插件系统未启用", "error")
    return redirect(url_for("admin.plugins"))


@bp.route("/plugins/<name>/disable", methods=["POST"])
@login_required
@admin_required
def disable_plugin(name):
    """
    禁用插件
    """
    from ..plugins import get_plugin_manager
    try:
        manager = get_plugin_manager()
        if manager.disable_plugin(name):
            flash(f"插件 {name} 已禁用", "success")
        else:
            flash(f"插件 {name} 禁用失败", "error")
    except RuntimeError:
        flash("插件系统未启用", "error")
    return redirect(url_for("admin.plugins"))
