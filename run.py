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
    
    if debug:
        try:
            from werkzeug.serving import run_simple
            import watchdog.observers
            import watchdog.events
            import time
            import threading
            
            class FileChangeHandler(watchdog.events.FileSystemEventHandler):
                def __init__(self):
                    self.should_restart = False
                
                def on_any_event(self, event):
                    if event.event_type in ['created', 'modified', 'deleted']:
                        if event.src_path.endswith(('.py', '.html', '.css', '.js', '.toml')):
                            app.logger.info(f"File changed: {event.src_path}")
                            self.should_restart = True
            
            def watch_files():
                event_handler = FileChangeHandler()
                observer = watchdog.observers.Observer()
                observer.schedule(event_handler, path='.', recursive=True)
                observer.start()
                
                try:
                    while True:
                        time.sleep(1)
                        if event_handler.should_restart:
                            observer.stop()
                            observer.join()
                            os.execv(sys.executable, [sys.executable] + sys.argv)
                except KeyboardInterrupt:
                    observer.stop()
                    observer.join()
            
            import sys
            # 启动文件监听线程
            watcher_thread = threading.Thread(target=watch_files, daemon=True)
            watcher_thread.start()
            
            app.logger.info("Starting server at http://%s:%s (DEBUG=%s, with watchdog reloader)", host, port, debug)
            app.run(host=host, port=port, debug=debug, use_reloader=False)
        except ImportError:
            # 如果没有安装watchdog，使用Flask默认的重载器
            app.logger.info("Starting server at http://%s:%s (DEBUG=%s, with default reloader)", host, port, debug)
            app.run(host=host, port=port, debug=debug)
    else:
        app.logger.info("Starting server at http://%s:%s (DEBUG=%s)", host, port, debug)
        app.run(host=host, port=port, debug=debug)
