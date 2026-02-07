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
    form = UserForm(obj=user)
    if form.validate_on_submit():
        user.role = form.role.data
        db.session.commit()
        flash("用户权限更新成功", "success")
        return redirect(url_for("admin.users"))
    return render_template("admin/edit_user.html", form=form, user=user)
