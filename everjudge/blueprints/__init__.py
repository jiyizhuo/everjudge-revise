"""
注册所有蓝图到 Flask 应用。
"""
from .main import bp as main_bp


def register_blueprints(app):
    app.register_blueprint(main_bp, url_prefix="/")
    # 后续在此注册: auth, problems, judge, blog, discuss, admin 等
    try:
        from .auth import bp as auth_bp
        app.register_blueprint(auth_bp, url_prefix="/auth")
    except ImportError:
        pass
    try:
        from .problems import bp as problems_bp
        app.register_blueprint(problems_bp, url_prefix="/problems")
    except ImportError:
        pass
    try:
        from .admin import bp as admin_bp
        app.register_blueprint(admin_bp, url_prefix="/admin")
    except ImportError:
        pass
