"""
插件多语言支持 - LanguageProvider
支持插件提供多种语言的翻译和本地化
"""
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any
from flask import Flask, request, g


class LanguageProvider(ABC):
    """语言提供者基类"""

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """提供者名称"""
        pass

    @abstractmethod
    def get_translations(self, locale: str) -> Dict[str, str]:
        """获取指定语言的翻译字典"""
        pass

    @abstractmethod
    def get_supported_locales(self) -> List[str]:
        """获取支持的语言列表"""
        pass

    @property
    def default_locale(self) -> str:
        """默认语言"""
        return "en_US"


class JSONLanguageProvider(LanguageProvider):
    """基于JSON文件的语言提供者"""

    def __init__(self, translations_dir: str, domain: str = "messages"):
        self.translations_dir = translations_dir
        self.domain = domain
        self._cache: Dict[str, Dict[str, str]] = {}

    @property
    def provider_name(self) -> str:
        return "json"

    def _load_translations(self, locale: str) -> Dict[str, str]:
        """加载翻译文件"""
        if locale in self._cache:
            return self._cache[locale]

        import os
        import json

        file_path = os.path.join(
            self.translations_dir,
            locale,
            f"{self.domain}.json"
        )

        if os.path.exists(file_path):
            with open(file_path, 'r', encoding='utf-8') as f:
                translations = json.load(f)
                self._cache[locale] = translations
                return translations

        self._cache[locale] = {}
        return {}

    def get_translations(self, locale: str) -> Dict[str, str]:
        return self._load_translations(locale)

    def get_supported_locales(self) -> List[str]:
        """扫描支持的语言目录"""
        import os

        if not os.path.isdir(self.translations_dir):
            return []

        locales = []
        for item in os.listdir(self.translations_dir):
            path = os.path.join(self.translations_dir, item)
            if os.path.isdir(path):
                locales.append(item)

        return locales


class PythonLanguageProvider(LanguageProvider):
    """基于Python文件的语言提供者"""

    def __init__(self, translations_dir: str, domain: str = "messages"):
        self.translations_dir = translations_dir
        self.domain = domain
        self._cache: Dict[str, Dict[str, str]] = {}

    @property
    def provider_name(self) -> str:
        return "python"

    def _load_translations(self, locale: str) -> Dict[str, str]:
        """加载Python翻译文件"""
        if locale in self._cache:
            return self._cache[locale]

        import importlib.util
        import os

        file_path = os.path.join(
            self.translations_dir,
            locale,
            f"{self.domain}.py"
        )

        if os.path.exists(file_path):
            spec = importlib.util.spec_from_file_location(
                f"translation_{locale}_{self.domain}",
                file_path
            )
            if spec and spec.loader:
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)

                translations = getattr(module, 'translations', {})
                self._cache[locale] = translations
                return translations

        self._cache[locale] = {}
        return {}

    def get_translations(self, locale: str) -> Dict[str, str]:
        return self._load_translations(locale)

    def get_supported_locales(self) -> List[str]:
        """扫描支持的语言目录"""
        import os

        if not os.path.isdir(self.translations_dir):
            return []

        locales = []
        for item in os.listdir(self.translations_dir):
            path = os.path.join(self.translations_dir, item)
            if os.path.isdir(path):
                locales.append(item)

        return locales


class GetTextLanguageProvider(LanguageProvider):
    """基于GNU gettext的语言提供者"""

    def __init__(self, translations_dir: str, domain: str = "messages"):
        self.translations_dir = translations_dir
        self.domain = domain
        self._locale_dirs: Dict[str, Any] = {}

    @property
    def provider_name(self) -> str:
        return "gettext"

    def _get_translator(self, locale: str):
        """获取翻译器"""
        if locale in self._locale_dirs:
            return self._locale_dirs[locale]

        try:
            import gettext
            locale_dir = os.path.join(self.translations_dir)
            translator = gettext.translation(
                self.domain,
                localedir=locale_dir,
                languages=[locale]
            )
            self._locale_dirs[locale] = translator
            return translator
        except (FileNotFoundError, NotImplementedError):
            null_translator = gettext.NullTranslations()
            self._locale_dirs[locale] = null_translator
            return null_translator

    def get_translations(self, locale: str) -> Dict[str, str]:
        """gettext使用函数式翻译，不返回字典"""
        return {}

    def gettext(self, locale: str, singular: str, plural: str = None) -> str:
        """获取翻译文本"""
        translator = self._get_translator(locale)
        if plural:
            return translator.ngettext(singular, plural)
        return translator.gettext(singular)

    def get_supported_locales(self) -> List[str]:
        """扫描LC_MESSAGES目录"""
        import os

        if not os.path.isdir(self.translations_dir):
            return []

        locales = []
        lc_messages = os.path.join(self.translations_dir, 'LC_MESSAGES')
        if os.path.isdir(lc_messages):
            for item in os.listdir(lc_messages):
                if item.endswith('.mo'):
                    locales.append(item.replace(f'.mo', '').replace(f'{self.domain}.', ''))

        return locales


class PluginI18nManager:
    """插件国际化管理器"""

    def __init__(self, app: Flask = None):
        self.app = app
        self.providers: Dict[str, LanguageProvider] = {}
        self.plugin_translations: Dict[str, Dict[str, Dict[str, str]]] = {}

    def init_app(self, app: Flask):
        self.app = app

    def register_provider(self, plugin_name: str, provider: LanguageProvider):
        """注册语言提供者"""
        key = f"{plugin_name}_{provider.provider_name}"
        self.providers[key] = provider

    def register_translations(
        self,
        plugin_name: str,
        locale: str,
        translations: Dict[str, str]
    ):
        """直接注册翻译字典"""
        if plugin_name not in self.plugin_translations:
            self.plugin_translations[plugin_name] = {}

        if locale not in self.plugin_translations[plugin_name]:
            self.plugin_translations[plugin_name][locale] = {}

        self.plugin_translations[plugin_name][locale].update(translations)

    def get_translations(self, plugin_name: str, locale: str) -> Dict[str, str]:
        """获取插件的翻译"""
        translations = {}

        # 首先检查直接注册的翻译
        if plugin_name in self.plugin_translations:
            if locale in self.plugin_translations[plugin_name]:
                translations.update(self.plugin_translations[plugin_name][locale])

        # 然后检查注册的提供者
        for key, provider in self.providers.items():
            if key.startswith(f"{plugin_name}_"):
                provider_translations = provider.get_translations(locale)
                translations.update(provider_translations)

        return translations

    def get_all_translations(self, locale: str) -> Dict[str, Dict[str, str]]:
        """获取所有插件的翻译"""
        all_translations = {}
        for plugin_name in self._get_all_plugin_names():
            translations = self.get_translations(plugin_name, locale)
            if translations:
                all_translations[plugin_name] = translations
        return all_translations

    def _get_all_plugin_names(self) -> set:
        """获取所有插件名称"""
        names = set()

        # 从提供者key中提取
        for key in self.providers.keys():
            parts = key.split('_', 1)
            if len(parts) >= 1:
                names.add(parts[0])

        # 从直接注册的翻译中提取
        names.update(self.plugin_translations.keys())

        return names

    def add_template_filters(self, app: Flask):
        """添加模板过滤器用于翻译"""

        def plugin_translate(key, plugin_name: str = None, locale: str = None):
            """翻译插件文本"""
            if locale is None:
                locale = getattr(g, 'locale', None) or self._get_locale()

            if plugin_name is None:
                return key

            translations = self.get_translations(plugin_name, locale)
            return translations.get(key, key)

        def plugin_ntranslate(
            singular: str,
            plural: str,
            n: int,
            plugin_name: str = None,
            locale: str = None
        ):
            """复数形式翻译"""
            if locale is None:
                locale = getattr(g, 'locale', None) or self._get_locale()

            if plugin_name is None:
                return singular if n == 1 else plural

            translations = self.get_translations(plugin_name, locale)
            singular_trans = translations.get(singular, singular)
            plural_trans = translations.get(plural, plural)

            return singular_trans if n == 1 else plural_trans

        app.jinja_env.filters['plugin_translate'] = plugin_translate
        app.jinja_env.filters['plugin_ntranslate'] = plugin_ntranslate

    def _get_locale(self) -> str:
        """获取当前语言"""
        if self.app:
            return self.app.config.get('BABEL_DEFAULT_LOCALE', 'zh_CN')
        return 'zh_CN'


import os


def create_language_provider(
    plugin_dir: str,
    provider_type: str = "json",
    translations_dir: str = "translations",
    domain: str = "messages"
) -> Optional[LanguageProvider]:
    """创建语言提供者工厂函数"""

    full_path = os.path.join(plugin_dir, translations_dir)

    if provider_type == "json":
        return JSONLanguageProvider(full_path, domain)
    elif provider_type == "python":
        return PythonLanguageProvider(full_path, domain)
    elif provider_type == "gettext":
        return GetTextLanguageProvider(full_path, domain)
    else:
        return None
