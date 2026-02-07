"""
开发环境运行入口：python run.py
生产环境请使用 uWSGI 加载 wsgi:app。
"""
import os
os.environ.setdefault("FLASK_APP", "everjudge")

from everjudge import create_app
app = create_app()

if __name__ == "__main__":
    host = app.config.get("SERVER_HOST", "0.0.0.0")
    port = int(app.config.get("SERVER_PORT", "5000"))
    debug = app.config.get("DEBUG", False)
    app.logger.info("Starting server at http://%s:%s (DEBUG=%s)", host, port, debug)
    app.run(host=host, port=port, debug=debug)
