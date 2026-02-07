"""
插件系统：从 PLUGINS_DIR 加载插件（Phase 5 完善）。
"""
import os
import importlib.util
from flask import Flask
from typing import List


def load_plugins(app: Flask) -> None:
    """扫描插件目录并加载各插件的 init 钩子。"""
    plugins_dir = app.config.get("PLUGINS_DIR", "plugins")
    if not os.path.isabs(plugins_dir):
        plugins_dir = os.path.join(app.root_path, "..", plugins_dir)
    plugins_dir = os.path.abspath(plugins_dir)
    if not os.path.isdir(plugins_dir):
        return
    for name in os.listdir(plugins_dir):
        path = os.path.join(plugins_dir, name)
        if not os.path.isdir(path):
            continue
        init_py = os.path.join(path, "init.py")
        if not os.path.isfile(init_py):
            continue
        try:
            spec = importlib.util.spec_from_file_location(f"everjudge_plugin_{name}", init_py)
            if spec and spec.loader:
                mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(mod)
                if hasattr(mod, "register"):
                    mod.register(app)
        except Exception:
            if app.debug:
                raise
