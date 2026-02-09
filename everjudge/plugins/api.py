"""
插件API：提供给插件的实用工具函数。
"""
from typing import Optional, Dict, Any, List, Callable
from flask import Flask, Blueprint, render_template, current_app, g
from ..extensions import db
from ..models import User, Problem, Submission, TestCase


class PluginAPI:
    def __init__(self, app: Flask):
        self.app = app

    @property
    def config(self) -> Any:
        """获取Flask应用配置。"""
        return current_app.config

    def get_db(self):
        """获取SQLAlchemy数据库实例。"""
        return db

    def get_model(self, model_name: str) -> Any:
        """获取数据库模型类。"""
        models = {
            "User": User,
            "Problem": Problem,
            "Submission": Submission,
            "TestCase": TestCase,
        }
        return models.get(model_name)

    def register_blueprint(self, blueprint: Blueprint, **options):
        """注册Flask蓝图。"""
        self.app.register_blueprint(blueprint, **options)

    def add_template_filter(self, f, name: Optional[str] = None):
        """添加模板过滤器。"""
        self.app.template_filter(name or f.__name__)(f)

    def add_template_global(self, f, name: Optional[str] = None):
        """添加模板全局函数。"""
        name = name or f.__name__
        self.app.context_processor(lambda: {name: f})

    def add_url_rule(self, rule: str, endpoint: Optional[str] = None, view_func=None, **options):
        """添加URL规则。"""
        self.app.add_url_rule(rule, endpoint, view_func, **options)

    def register_hook(self, hook_name: str, func):
        """注册插件钩子。"""
        from .manager import PluginManager
        manager = self.app.extensions.get("plugin_manager")
        if manager:
            manager.register_hook(hook_name, func)

    def before_request(self, f):
        """注册before_request钩子。"""
        self.register_hook("before_request", f)
        return f

    def after_request(self, f):
        """注册after_request钩子。"""
        self.register_hook("after_request", f)
        return f

    def on_judge_complete(self, f):
        """注册评测完成钩子。"""
        self.register_hook("on_judge_complete", f)
        return f

    def on_submission_created(self, f):
        """注册提交创建钩子。"""
        self.register_hook("on_submission_created", f)
        return f

    def on_problem_created(self, f):
        """注册题目创建钩子。"""
        self.register_hook("on_problem_created", f)
        return f

    def on_user_registered(self, f):
        """注册用户注册钩子。"""
        self.register_hook("on_user_registered", f)
        return f

    def get_plugin_config(self, plugin_name: str, key: str, default: Any = None) -> Any:
        """获取插件配置。"""
        from .models import Plugin
        plugin = Plugin.query.filter_by(name=plugin_name).first()
        if plugin and plugin.config:
            import json
            try:
                config = json.loads(plugin.config)
                return config.get(key, default)
            except Exception:
                pass
        return default

    def set_plugin_config(self, plugin_name: str, key: str, value: Any) -> bool:
        """设置插件配置。"""
        from .models import Plugin
        import json
        plugin = Plugin.query.filter_by(name=plugin_name).first()
        if plugin:
            try:
                config = json.loads(plugin.config) if plugin.config else {}
                config[key] = value
                plugin.config = json.dumps(config)
                db.session.commit()
                return True
            except Exception:
                pass
        return False

    def render_template(self, template_name: str, **context) -> str:
        """渲染模板字符串。"""
        return render_template(template_name, **context)

    def flash(self, message: str, category: str = "message"):
        """显示flash消息。"""
        from flask import flash
        flash(message, category)

    def log_info(self, message: str):
        """记录INFO级别日志。"""
        current_app.logger.info(message)

    def log_warning(self, message: str):
        """记录WARNING级别日志。"""
        current_app.logger.warning(message)

    def log_error(self, message: str):
        """记录ERROR级别日志。"""
        current_app.logger.error(message)

    def log_debug(self, message: str):
        """记录DEBUG级别日志。"""
        current_app.logger.debug(message)

    def register_i18n_provider(self, plugin_name: str, provider):
        """注册国际化提供者。"""
        from .i18n import PluginI18nManager
        manager = self.app.extensions.get("plugin_i18n_manager")
        if manager:
            manager.register_provider(plugin_name, provider)

    def register_translations(
        self,
        plugin_name: str,
        locale: str,
        translations: Dict[str, str]
    ):
        """直接注册翻译。"""
        from .i18n import PluginI18nManager
        manager = self.app.extensions.get("plugin_i18n_manager")
        if manager:
            manager.register_translations(plugin_name, locale, translations)

    def register_template_dir(self, plugin_name: str, templates_dir: str):
        """注册插件模板目录以支持模板覆盖。"""
        from .template_overrides import TemplateOverrideManager
        manager = self.app.extensions.get("template_override_manager")
        if manager:
            manager.register_plugin_templates(plugin_name, templates_dir)

    def add_ui_module(self, module):
        """注册UI模块。"""
        from .template_overrides import UIModuleRegistry
        registry = self.app.extensions.get("ui_module_registry")
        if registry:
            registry.register(module)

    def add_hook_ui(self, hook_name: str, module):
        """在指定钩子点添加UI模块。"""
        from .template_overrides import UIModuleRegistry
        registry = self.app.extensions.get("ui_module_registry")
        if registry:
            registry.register(module, [hook_name])

    def register_judge_provider(self, provider, as_default: bool = False):
        """注册评测机提供者。"""
        from .judge_provider import PluginJudgeManager
        manager = self.app.extensions.get("judge_manager")
        if manager:
            manager.register_provider(provider, as_default)

    def judge(self, request) -> Any:
        """执行评测。"""
        from .judge_provider import PluginJudgeManager, JudgeRequest
        manager = self.app.extensions.get("judge_manager")
        if manager:
            if isinstance(request, dict):
                request = JudgeRequest.from_dict(request)
            return manager.judge(request)
        return None

    def is_language_supported(self, language: str) -> bool:
        """检查语言是否被支持。"""
        from .judge_provider import PluginJudgeManager
        manager = self.app.extensions.get("judge_manager")
        if manager:
            return manager.is_language_supported(language)
        return False

    def add_cli_command(self, name: str, callback: Callable, **options):
        """注册CLI命令。"""
        from flask import Flask
        if hasattr(self.app, 'cli'):
            self.app.cli.command(name, **options)(callback)

    def add_teardown(self, exc):
        """注册请求清理函数。"""
        from flask import Flask
        self.app.teardown_request_callbacks.append(exc)

    def add_url_value_preprocessor(self, f):
        """注册URL值预处理器。"""
        self.app.url_value_preprocessor(f)

    def add_template_context_processor(self, f):
        """注册模板上下文处理器。"""
        self.app.context_processor(f)
