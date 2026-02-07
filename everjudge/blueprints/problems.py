"""
题目蓝图：题单、题目详情、提交（Phase 3 完善）。
"""
from flask import Blueprint, render_template

bp = Blueprint("problems", __name__)


@bp.route("/")
def index():
    return render_template("problems/index.html")
