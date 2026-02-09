"""
插件模板覆盖系统
允许插件覆盖默认模板，提供自定义界面
"""
import os
import re
from typing import Dict, List, Optional, Callable, Any
from flask import Flask, render_template, abort, template_filter
from jinja2 import FileSystemLoader, Environment, BaseLoader


class TemplateOverrideLoader(BaseLoader):
    """Jinja2模板加载器，支持插件覆盖默认模板"""

    def __init__(
        self,
        original_loader: FileSystemLoader,
        plugin_template_dirs: List[str]
    ):
        self.original_loader = original_loader
        self.plugin_template_dirs = plugin_template_dirs
        self._plugin_cache: Dict[str, str] = {}

    def get_source(self, environment: Environment, template: str) -> tuple:
        """获取模板源，优先从插件目录查找"""
        # 先检查插件目录
        for plugin_dir in self.plugin_template_dirs:
            override_path = os.path.join(plugin_dir, template)
            if os.path.exists(override_path):
                with open(override_path, 'r', encoding='utf-8') as f:
                    source = f.read()
                self._plugin_cache[template] = plugin_dir
                return source, override_path, lambda: True

        # 回退到原始加载器
        return self.original_loader.get_source(environment, template)

    def list_templates(self) -> List[str]:
        """列出所有可用模板"""
        templates = set()

        # 插件模板
        for plugin_dir in self.plugin_template_dirs:
            for root, dirs, files in os.walk(plugin_dir):
                for file in files:
                    if file.endswith(('.html', '.htm', '.txt', '.j2')):
                        rel_path = os.path.relpath(
                            os.path.join(root, file),
                            plugin_dir
                        )
                        templates.add(rel_path)

        # 原始模板
        try:
            original_templates = self.original_loader.list_templates()
            templates.update(original_templates)
        except Exception:
            pass

        return sorted(templates)


class TemplateOverrideManager:
    """模板覆盖管理器"""

    def __init__(self, app: Flask = None):
        self.app = app
        self.plugin_template_dirs: List[str] = []
        self.original_jinja_env: Optional[Environment] = None
        self.custom_filters: Dict[str, Callable] = {}
        self.custom_tests: Dict[str, Callable] = {}

    def init_app(self, app: Flask):
        self.app = app

    def register_plugin_templates(self, plugin_name: str, templates_dir: str):
        """注册插件模板目录"""
        if os.path.isdir(templates_dir):
            self.plugin_template_dirs.append(templates_dir)
            app = self.app
            if app:
                self._update_template_loader(app)

    def _update_template_loader(self, app: Flask):
        """更新Flask的模板加载器"""
        if not hasattr(app, 'jinja_env'):
            return

        original_loader = app.jinja_loader
        if original_loader is None:
            return

        override_loader = TemplateOverrideLoader(
            original_loader,
            self.plugin_template_dirs
        )

        app.jinja_loader = override_loader

        for name, func in self.custom_filters.items():
            app.jinja_env.filters[name] = func

    def add_template_filter(self, name: str, func: Callable):
        """添加自定义模板过滤器"""
        self.custom_filters[name] = func
        if self.app:
            self.app.jinja_env.filters[name] = func

    def add_template_test(self, name: str, func: Callable):
        """添加自定义模板测试"""
        self.custom_tests[name] = func
        if self.app:
            self.app.jinja_env.tests[name] = func

    def render_plugin_template(
        self,
        template_name: str,
        plugin_name: str = None,
        **context
    ) -> str:
        """渲染插件模板"""
        app = self.app
        if app is None:
            raise RuntimeError("TemplateOverrideManager not initialized")

        return render_template(template_name, **context)

    def get_template_source(self, template: str) -> Optional[str]:
        """获取模板源内容"""
        if self.app and hasattr(self.app.jinja_loader, 'get_source'):
            try:
                source, _, _ = self.app.jinja_loader.get_source(
                    self.app.jinja_env,
                    template
                )
                return source
            except Exception:
                pass
        return None

    def template_exists(self, template: str) -> bool:
        """检查模板是否存在"""
        try:
            if self.app:
                self.app.jinja_env.get_or_select_template(template)
                return True
        except Exception:
            pass
        return False

    def list_plugin_templates(self, plugin_name: str = None) -> List[str]:
        """列出插件模板"""
        templates = []

        for plugin_dir in self.plugin_template_dirs:
            if plugin_name and not plugin_dir.endswith(plugin_name):
                continue

            for root, dirs, files in os.walk(plugin_dir):
                for file in files:
                    if file.endswith(('.html', '.htm', '.j2')):
                        rel_path = os.path.relpath(
                            os.path.join(root, file),
                            plugin_dir
                        )
                        templates.append(rel_path)

        return sorted(set(templates))

    def is_template_overridden(self, template: str) -> bool:
        """检查模板是否被插件覆盖"""
        if self.app and hasattr(self.app.jinja_loader, '_plugin_cache'):
            return template in self.app.jinja_loader._plugin_cache
        return False

    def get_overriding_plugin(self, template: str) -> Optional[str]:
        """获取覆盖模板的插件名称"""
        if self.app and hasattr(self.app.jinja_loader, '_plugin_cache'):
            plugin_dir = self.app.jinja_loader._plugin_cache.get(template)
            if plugin_dir:
                return os.path.basename(plugin_dir)
        return None


class UIModule:
    """插件UI模块 - 允许插件注入自定义UI组件"""

    def __init__(
        self,
        name: str,
        template: str = None,
        script: str = None,
        style: str = None
    ):
        self.name = name
        self.template = template
        self.script = script
        self.style = style
        self.dependencies: List[str] = []

    def add_dependency(self, dep: str):
        """添加依赖"""
        self.dependencies.append(dep)


class UIModuleRegistry:
    """UI模块注册表"""

    def __init__(self):
        self.modules: Dict[str, UIModule] = {}
        self.hooks: Dict[str, List[str]] = {}

    def register(self, module: UIModule, hook_points: List[str] = None):
        """注册UI模块"""
        self.modules[module.name] = module

        if hook_points:
            for hook in hook_points:
                if hook not in self.hooks:
                    self.hooks[hook] = []
                self.hooks[hook].append(module.name)

    def get_modules_for_hook(self, hook: str) -> List[UIModule]:
        """获取指定钩子点的所有模块"""
        module_names = self.hooks.get(hook, [])
        return [self.modules[name] for name in module_names if name in self.modules]

    def get_all_modules(self) -> List[UIModule]:
        """获取所有模块"""
        return list(self.modules.values())

    def render_hook(self, hook: str, **context) -> str:
        """渲染钩子点的所有模块"""
        modules = self.get_modules_for_hook(hook)
        rendered = []

        for module in modules:
            if module.template:
                rendered.append(f"<!-- UI Module: {module.name} -->")
                rendered.append(module.template)

        return '\n'.join(rendered)


def create_template_override_system(app: Flask = None) -> TemplateOverrideManager:
    """创建模板覆盖系统"""
    manager = TemplateOverrideManager(app)
    return manager


def create_ui_module_registry() -> UIModuleRegistry:
    """创建UI模块注册表"""
    return UIModuleRegistry()
