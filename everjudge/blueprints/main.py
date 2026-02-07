"""
首页与静态页面蓝图。
"""
from flask import Blueprint, render_template

bp = Blueprint("main", __name__)


@bp.route("/")
def index():
    return render_template("main/index.html")
