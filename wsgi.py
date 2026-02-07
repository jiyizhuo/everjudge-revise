"""
uWSGI 入口：uwsgi --ini uwsgi.ini 将使用本模块的 app。
"""
from everjudge import create_app
app = create_app()
