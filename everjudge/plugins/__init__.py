"""
插件系统：从 PLUGINS_DIR 加载插件（Phase 5 完善）。
"""
import os
import importlib.util
from flask import Flask
from typing import List, Optional

_plugin_manager: Optional['PluginManager'] = None


def get_plugin_manager() -> 'PluginManager':
    """获取全局插件管理器实例。"""
    global _plugin_manager
    if _plugin_manager is None:
        raise RuntimeError("PluginManager not initialized. Call init_plugins first.")
    return _plugin_manager


def init_plugins(app: Flask) -> 'PluginManager':
    """初始化插件系统。"""
    global _plugin_manager
    from .manager import PluginManager
    from .models import db

    _plugin_manager = PluginManager(app)
    _plugin_manager.init_app(app)

    with app.app_context():
        if app.config.get("PLUGINS_ENABLED", False):
            discovered = _plugin_manager.scan_plugins()
            for plugin_info in discovered:
                name = plugin_info.get("name")
                if not Plugin.query.filter_by(name=name).first():
                    plugin = Plugin(
                        name=name,
                        version=plugin_info.get("version", "1.0.0"),
                        description=plugin_info.get("description", ""),
                        author=plugin_info.get("author", ""),
                        enabled=False,
                        hooks=",".join(plugin_info.get("hooks", [])),
                    )
                    db.session.add(plugin)
            db.session.commit()

            _plugin_manager.load_all_enabled_plugins()

    return _plugin_manager


def load_plugins(app: Flask) -> None:
    """扫描插件目录并加载各插件的 init 钩子。"""
    if app.config.get("PLUGINS_ENABLED", False):
        init_plugins(app)
        app.logger.info("Plugins initialized from %s", app.config.get("PLUGINS_DIR", "plugins"))


from .models import Plugin
