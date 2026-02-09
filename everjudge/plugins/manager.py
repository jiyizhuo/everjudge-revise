"""
插件管理器：负责插件的注册、加载、启用、禁用和卸载。
"""
import os
import sys
import importlib
import importlib.util
import json
from typing import Optional, Dict, Any, List, Callable
from flask import Flask
from .models import Plugin as PluginModel
from .api import PluginAPI


class PluginManager:
    def __init__(self, app: Flask = None):
        self.app = app
        self.plugins: Dict[str, Dict[str, Any]] = {}
        self.hooks: Dict[str, List[Callable]] = {}
        self.loaded_plugins: Dict[str, Any] = {}
        self._api: Optional[PluginAPI] = None

    def init_app(self, app: Flask):
        self.app = app
        self._api = PluginAPI(app)

    @property
    def api(self) -> PluginAPI:
        if self._api is None:
            raise RuntimeError("PluginManager not initialized. Call init_app first.")
        return self._api

    def load_plugin_info(self, plugin_dir: str) -> Optional[Dict[str, Any]]:
        """从 plugin.toml 加载插件元数据。"""
        plugin_toml = os.path.join(plugin_dir, "plugin.toml")
        if not os.path.isfile(plugin_toml):
            return None

        try:
            import toml
            with open(plugin_toml, "r", encoding="utf-8") as f:
                return toml.load(f)
        except Exception:
            return None

    def scan_plugins(self) -> List[Dict[str, Any]]:
        """扫描插件目录，返回所有发现的插件信息。"""
        if not self.app:
            return []

        plugins_dir = self.app.config.get("PLUGINS_DIR", "plugins")
        if not os.path.isabs(plugins_dir):
            plugins_dir = os.path.join(self.app.root_path, "..", plugins_dir)
        plugins_dir = os.path.abspath(plugins_dir)

        if not os.path.isdir(plugins_dir):
            return []

        plugins = []
        for name in os.listdir(plugins_dir):
            path = os.path.join(plugins_dir, name)
            if not os.path.isdir(path):
                continue

            init_py = os.path.join(path, "init.py")
            if not os.path.isfile(init_py):
                continue

            info = self.load_plugin_info(path)
            if info:
                info["name"] = name
                info["path"] = path
                plugins.append(info)

        return plugins

    def get_plugin_module(self, name: str, path: str):
        """动态加载插件模块。"""
        init_py = os.path.join(path, "init.py")
        if not os.path.isfile(init_py):
            return None

        spec = importlib.util.spec_from_file_location(f"everjudge_plugin_{name}", init_py)
        if not spec or not spec.loader:
            return None

        module = importlib.util.module_from_spec(spec)
        sys.modules[f"everjudge_plugin_{name}"] = module
        spec.loader.exec_module(module)
        return module

    def register_hook(self, hook_name: str, func: Callable):
        """注册一个钩子函数。"""
        if hook_name not in self.hooks:
            self.hooks[hook_name] = []
        self.hooks[hook_name].append(func)

    def call_hooks(self, hook_name: str, *args, **kwargs):
        """调用所有注册的钩子函数。"""
        results = []
        if hook_name in self.hooks:
            for func in self.hooks[hook_name]:
                try:
                    result = func(*args, **kwargs)
                    results.append(result)
                except Exception:
                    if self.app and self.app.debug:
                        raise
        return results

    def install_plugin(self, name: str) -> bool:
        """安装插件（添加到数据库）。"""
        if not self.app:
            return False

        plugin_info = None
        for p in self.scan_plugins():
            if p.get("name") == name:
                plugin_info = p
                break

        if not plugin_info:
            return False

        existing = PluginModel.query.filter_by(name=name).first()
        if existing:
            return True

        plugin = PluginModel(
            name=name,
            version=plugin_info.get("version", "1.0.0"),
            description=plugin_info.get("description", ""),
            author=plugin_info.get("author", ""),
            enabled=False,
            hooks=",".join(plugin_info.get("hooks", [])),
            config=json.dumps(plugin_info.get("config", {})),
        )
        from ..extensions import db
        db.session.add(plugin)
        db.session.commit()
        return True

    def uninstall_plugin(self, name: str) -> bool:
        """卸载插件（从数据库移除）。"""
        if not self.app:
            return False

        from ..extensions import db
        plugin = PluginModel.query.filter_by(name=name).first()
        if plugin:
            db.session.delete(plugin)
            db.session.commit()
            if name in self.loaded_plugins:
                del self.loaded_plugins[name]
            return True
        return False

    def enable_plugin(self, name: str) -> bool:
        """启用插件。"""
        if not self.app:
            return False

        from ..extensions import db
        plugin = PluginModel.query.filter_by(name=name).first()
        if plugin:
            plugin.enabled = True
            db.session.commit()
            self.load_plugin(name)
            return True
        return False

    def disable_plugin(self, name: str) -> bool:
        """禁用插件。"""
        if not self.app:
            return False

        from ..extensions import db
        plugin = PluginModel.query.filter_by(name=name).first()
        if plugin:
            plugin.enabled = False
            db.session.commit()
            self.unload_plugin(name)
            return True
        return False

    def load_plugin(self, name: str) -> bool:
        """加载已启用插件。"""
        if not self.app:
            return False

        plugin_db = PluginModel.query.filter_by(name=name, enabled=True).first()
        if not plugin_db:
            return False

        if name in self.loaded_plugins:
            return True

        for p in self.scan_plugins():
            if p.get("name") == name:
                module = self.get_plugin_module(name, p.get("path"))
                if module and hasattr(module, "register"):
                    self.loaded_plugins[name] = {
                        "module": module,
                        "info": p,
                        "db": plugin_db,
                    }
                    module.register(self.api)
                    return True
                break

        return False

    def unload_plugin(self, name: str) -> bool:
        """卸载已加载插件。"""
        if name in self.loaded_plugins:
            del self.loaded_plugins[name]
        return True

    def load_all_enabled_plugins(self) -> int:
        """加载所有已启用的插件。"""
        if not self.app:
            return 0

        from ..extensions import db
        enabled_plugins = PluginModel.query.filter_by(enabled=True).all()
        loaded_count = 0

        for plugin_db in enabled_plugins:
            if self.load_plugin(plugin_db.name):
                loaded_count += 1

        return loaded_count

    def get_plugin_status(self, name: str) -> Optional[Dict[str, Any]]:
        """获取插件状态信息。"""
        plugin_db = PluginModel.query.filter_by(name=name).first()
        if not plugin_db:
            return None

        return {
            "database": plugin_db.to_dict(),
            "loaded": name in self.loaded_plugins,
            "path": self.loaded_plugins.get(name, {}).get("info", {}).get("path", ""),
        }

    def list_plugins(self) -> List[Dict[str, Any]]:
        """列出所有插件及其状态。"""
        if not self.app:
            return []

        discovered = {p.get("name"): p for p in self.scan_plugins()}
        plugins = []
        plugin_dbs = PluginModel.query.all()

        for plugin_db in plugin_dbs:
            info = discovered.get(plugin_db.name, {})
            plugins.append({
                "name": plugin_db.name,
                "version": plugin_db.version or info.get("version", "?"),
                "description": plugin_db.description or info.get("description", ""),
                "author": plugin_db.author or info.get("author", ""),
                "enabled": plugin_db.enabled,
                "loaded": plugin_db.name in self.loaded_plugins,
            })

        for name, info in discovered.items():
            if not any(p["name"] == name for p in plugins):
                plugins.append({
                    "name": name,
                    "version": info.get("version", "?"),
                    "description": info.get("description", ""),
                    "author": info.get("author", ""),
                    "enabled": False,
                    "loaded": False,
                })

        return plugins
