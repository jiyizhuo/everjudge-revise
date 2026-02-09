# EverJudge 插件系统

EverJudge 提供了一个功能强大的插件系统，支持插件扩展应用的各个方面。

## 目录

- [快速开始](#快速开始)
- [插件目录结构](#插件目录结构)
- [插件配置](#插件配置)
- [插件入口](#插件入口)
- [钩子系统](#钩子系统)
- [多语言支持](#多语言支持)
- [模板覆盖](#模板覆盖)
- [评测机替换](#评测机替换)
- [UI模块](#ui模块)
- [API参考](#api参考)
- [示例插件](#示例插件)
- [最佳实践](#最佳实践)

## 快速开始

### 创建第一个插件

1. 在 `plugins/` 目录下创建插件目录：
   ```bash
   mkdir plugins/my_first_plugin
   ```

2. 创建 `plugin.toml` 配置文件：
   ```toml
   name = "my_first_plugin"
   version = "1.0.0"
   description = "我的第一个插件"
   author = "Your Name"
   hooks = ["before_request", "after_request"]
   ```

3. 创建 `init.py` 插件入口：
   ```python
   def register(api):
       @api.before_request
       def log_request():
           api.log_info("收到请求")

       @api.add_url_rule("/hello", "hello", lambda: "Hello from my plugin!")
   ```

4. 启动应用并启用插件：
   ```bash
   python el.py plugins enable my_first_plugin
   ```

### 管理插件

#### 通过 CLI 管理

```bash
# 列出所有插件
python el.py plugins list

# 查看插件详情
python el.py plugins info my_first_plugin

# 启用插件
python el.py plugins enable my_first_plugin

# 禁用插件
python el.py plugins disable my_first_plugin

# 查看插件状态
python el.py plugins status
```

#### 通过管理后台

1. 使用管理员账户登录
2. 点击导航栏的"插件"链接
3. 查看所有已发现的插件
4. 点击"启用"或"禁用"按钮控制插件状态

## 插件目录结构

```
plugins/
└── <插件名>/
    ├── plugin.toml          # 插件配置（必需）
    ├── init.py             # 插件入口（必需）
    ├── translations/       # 国际化文件
    │   ├── zh_CN/
    │   │   └── messages.json
    │   └── en_US/
    │       └── messages.json
    ├── templates/          # 自定义模板
    │   ├── base.html
    │   └── custom_page.html
    ├── static/            # 静态文件
    │   ├── style.css
    │   └── script.js
    └── config.py          # 插件配置（可选）
```

## 插件配置

### plugin.toml

插件的主配置文件，包含插件的基本信息和元数据：

```toml
name = "example_plugin"
version = "1.0.0"
description = "这是一个示例插件"
author = "Your Name"

# 启用的钩子
hooks = [
    "before_request",
    "after_request",
    "on_judge_complete",
    "on_submission_created",
    "on_problem_created",
    "on_user_registered"
]

# 插件依赖
dependencies = []

# 插件配置
[config]
custom_option = "value"
```

### 配置字段说明

| 字段 | 必填 | 说明 |
|------|------|------|
| `name` | 是 | 插件名称，唯一标识符 |
| `version` | 是 | 版本号，建议使用语义化版本 |
| `description` | 否 | 插件描述 |
| `author` | 否 | 作者名称 |
| `hooks` | 否 | 启用的钩子列表 |
| `dependencies` | 否 | 插件依赖列表 |
| `config` | 否 | 插件配置项 |

## 插件入口

### init.py

每个插件必须有一个 `init.py` 文件，其中包含 `register(api)` 函数：

```python
def register(api):
    """
    插件注册函数。

    Args:
        api: PluginAPI 实例，提供各种插件功能
    """
    # 注册钩子
    @api.before_request
    def before_request():
        api.log_info("收到请求")

    @api.after_request
    def after_request(response):
        return response

    # 注册路由
    @api.add_url_rule("/custom", "custom_page", custom_view)

    # 注册蓝图
    api.register_blueprint(my_blueprint)

    # 添加模板过滤器
    api.add_template_filter(my_filter)

    # 添加模板全局函数
    api.add_template_global(my_function)
```

## 钩子系统

插件可以通过钩子拦截和处理应用的生命周期事件。

### 可用的钩子

| 钩子名 | 说明 | 回调参数 |
|--------|------|----------|
| `before_request` | 请求处理前 | 无 |
| `after_request` | 请求处理后 | response |
| `on_judge_complete` | 评测完成时 | result |
| `on_submission_created` | 提交创建时 | submission |
| `on_problem_created` | 题目创建时 | problem |
| `on_user_registered` | 用户注册时 | user |

### 钩子示例

```python
def register(api):
    @api.before_request
    def log_requests():
        """记录每个请求"""
        from flask import request
        api.log_info(f"请求: {request.path}")

    @api.after_request
    def add_header(response):
        """添加响应头"""
        response.headers['X-Plugin'] = 'my_plugin'
        return response

    @api.on_judge_complete
    def on_judge(result):
        """评测完成后发送通知"""
        if result.status.value == "ACCEPTED":
            api.log_info(f"提交 {result.submission_id} 通过！")
```

## 多语言支持

插件可以提供多语言支持，支持多种语言提供者。

### 快速翻译

最简单的方式是直接注册翻译字典：

```python
def register(api):
    api.register_translations("my_plugin", "zh_CN", {
        "welcome": "欢迎使用",
        "hello": "你好",
        "submit": "提交"
    })

    api.register_translations("my_plugin", "en_US", {
        "welcome": "Welcome",
        "hello": "Hello",
        "submit": "Submit"
    })
```

在模板中使用：

```html
{{ "welcome"|plugin_translate("my_plugin") }}
```

### JSON 语言提供者

创建 JSON 翻译文件：

```
plugins/my_plugin/translations/zh_CN/messages.json
plugins/my_plugin/translations/en_US/messages.json
```

JSON 文件格式：

```json
{
    "welcome": "欢迎",
    "hello": "你好"
}
```

注册提供者：

```python
from everjudge.plugins.i18n import JSONLanguageProvider

def register(api):
    provider = JSONLanguageProvider(
        translations_dir="translations",
        domain="messages"
    )
    api.register_i18n_provider("my_plugin", provider)
```

### Python 语言提供者

创建 Python 翻译文件：

```
plugins/my_plugin/translations/zh_CN/messages.py
plugins/my_plugin/translations/en_US/messages.py
```

Python 文件格式：

```python
translations = {
    "welcome": "欢迎",
    "hello": "你好"
}
```

### GetText 语言提供者

GetText 适合需要处理复数的场景：

```python
from everjudge.plugins.i18n import GetTextLanguageProvider

def register(api):
    provider = GetTextLanguageProvider(
        translations_dir="translations",
        domain="messages"
    )
    api.register_i18n_provider("my_plugin", provider)
```

## 模板覆盖

插件可以覆盖默认模板或添加自定义模板。

### 注册模板目录

```python
def register(api):
    api.register_template_dir("my_plugin", "templates")
```

### 覆盖默认模板

在插件的 `templates/` 目录下创建与默认模板同名的文件即可覆盖：

```
plugins/my_plugin/templates/base.html
plugins/my_plugin/templates/problems/detail.html
```

### 自定义模板

```python
def register(api):
    @api.add_url_rule("/custom", "custom_page", custom_page)
```

```python
from flask import render_template

def custom_page():
    return render_template("custom_page.html", title="自定义页面")
```

## 评测机替换

插件可以提供自定义评测机实现，支持完全替换或扩展默认评测逻辑。

### 创建自定义评测机

```python
from everjudge.plugins.judge_provider import (
    BaseJudgeProvider,
    JudgeRequest,
    JudgeResult,
    JudgeStatus
)

class CustomJudgeProvider(BaseJudgeProvider):
    @property
    def provider_name(self):
        return "custom_judge"

    @property
    def priority(self):
        return 100  # 优先级高于默认评测机

    def is_language_supported(self, language):
        return language in ["custom_lang", "my_lang"]

    def judge(self, request):
        # 自定义评测逻辑
        return JudgeResult(
            status=JudgeStatus.ACCEPTED,
            score=100,
            execution_time=10,
            memory_used=1024
        )

    def compile(self, code, language):
        # 编译逻辑
        return (True, "", "")

    def run(self, executable, input_data, time_limit, memory_limit):
        # 运行逻辑
        return ("", 0, 0, "")
```

### 注册评测机

```python
def register(api):
    # 注册为默认评测机
    api.register_judge_provider(CustomJudgeProvider(), as_default=True)

    # 或注册为特定语言的评测机
    api.register_judge_provider(CustomJudgeProvider(), as_default=False)
```

### 评测请求和结果

```python
from everjudge.plugins.judge_provider import JudgeRequest

def register(api):
    @api.add_url_rule("/judge", "judge", judge_view)

def judge_view():
    request_data = {
        "submission_id": 1,
        "problem_id": 1,
        "code": "print('hello')",
        "language": "python_3",
        "time_limit": 1000,
        "memory_limit": 134217728
    }
    result = api.judge(request_data)
    return {"status": result.status.value, "score": result.score}
```

## UI模块

插件可以注册 UI 模块，在指定位置注入自定义 UI。

### 创建 UI 模块

```python
from everjudge.plugins.template_overrides import UIModule

def register(api):
    module = UIModule(
        name="custom_header",
        template="<div class='custom-header'>自定义头部</div>",
        script="assets/header.js",
        style="assets/header.css"
    )
    api.add_ui_module(module)

    # 添加到指定钩子点
    api.add_hook_ui("header", module)
```

### 内联模板

```python
def register(api):
    module = UIModule(
        name="welcome_message",
        template="""
        <div class="welcome-box">
            <h2>欢迎使用 EverJudge</h2>
            <p>{{ message }}</p>
        </div>
        """
    )
    api.add_ui_module(module)
```

## API参考

### PluginAPI 方法

#### 蓝图和路由

```python
# 注册蓝图
api.register_blueprint(blueprint, url_prefix=None)

# 添加 URL 规则
api.add_url_rule(rule, endpoint, view_func, **options)

# 添加 URL 值预处理器
api.add_url_value_preprocessor(f)

# 添加模板上下文处理器
api.add_template_context_processor(f)
```

#### 模板

```python
# 添加模板过滤器
api.add_template_filter(func, name=None)

# 添加模板全局函数
api.add_template_global(func, name=None)

# 渲染模板
api.render_template(template_name, **context)

# 注册模板目录
api.register_template_dir(plugin_name, templates_dir)
```

#### 钩子

```python
# 注册通用钩子
api.register_hook(hook_name, func)

# 请求钩子
@api.before_request
@api.after_request

# 事件钩子
@api.on_judge_complete
@api.on_submission_created
@api.on_problem_created
@api.on_user_registered
```

#### 国际化

```python
# 注册语言提供者
api.register_i18n_provider(plugin_name, provider)

# 直接注册翻译
api.register_translations(plugin_name, locale, translations)
```

#### 评测机

```python
# 注册评测机提供者
api.register_judge_provider(provider, as_default=False)

# 执行评测
api.judge(request) -> JudgeResult

# 检查语言支持
api.is_language_supported(language) -> bool
```

#### UI 模块

```python
# 注册 UI 模块
api.add_ui_module(module)

# 添加到钩子点
api.add_hook_ui(hook_name, module)
```

#### 配置和状态

```python
# 获取插件配置
api.get_plugin_config(plugin_name, key, default=None)

# 设置插件配置
api.set_plugin_config(plugin_name, key, value) -> bool

# 获取应用配置
api.config

# 获取数据库实例
api.get_db()
```

#### 实用工具

```python
# 显示 flash 消息
api.flash(message, category="message")

# 日志记录
api.log_info(message)
api.log_warning(message)
api.log_error(message)
api.log_debug(message)
```

### 钩子参数类型

#### JudgeResult

```python
result.status          # JudgeStatus 枚举
result.score           # int, 得分
result.execution_time  # int, 执行时间(ms)
result.memory_used     # int, 内存使用(bytes)
result.error_message   # str, 错误信息
result.to_dict()       # 转换为字典
```

#### Submission (简化)

```python
submission.id          # int, 提交 ID
submission.problem_id  # int, 题目 ID
submission.user_id     # int, 用户 ID
submission.code        # str, 代码
submission.language    # str, 语言
submission.status      # str, 状态
```

## 示例插件

EverJudge 提供了一个示例插件 `hello_world`，位于 `plugins/hello_world/` 目录。

### 插件代码

```python
"""
Hello World 插件 - 展示插件系统的基本功能。
"""

def register(api):
    api.log_info("Hello World 插件已加载")

    @api.before_request
    def hello_before_request():
        from flask import request
        api.log_debug(f"Hello World: 请求 {request.path}")

    @api.after_request
    def hello_after_request(response):
        api.log_debug(f"Hello World: 响应状态 {response.status_code}")
        return response

    api.add_url_rule(
        "/hello",
        "hello_index",
        lambda: "<h1>Hello from Plugin!</h1><p>这是一个示例插件。</p>"
    )

    api.add_url_rule(
        "/hello/json",
        "hello_json",
        lambda: {"message": "Hello from Plugin!", "plugin": "hello_world"}
    )

    api.log_info("Hello World 插件注册完成")
```

### 插件配置

```toml
name = "hello_world"
version = "1.0.0"
description = "一个简单的示例插件，展示插件系统的基本功能"
author = "EverJudge"
hooks = ["before_request", "after_request"]
```

## 最佳实践

### 1. 命名规范

- 插件目录名应与 `plugin.toml` 中的 `name` 一致
- 使用小写字母和下划线命名
- 避免与 EverJudge 内置功能冲突

```toml
# 好的命名
name = "my_awesome_plugin"
name = "problem_statistics"
name = "custom_theme"

# 避免的命名
name = "admin"      # 与内置冲突
name = "flask"     # 与依赖冲突
name = "PLUGIN"    # 不一致的大小写
```

### 2. 异常处理

在钩子函数中妥善处理异常，避免影响主应用：

```python
def register(api):
    @api.before_request
    def safe_before_request():
        try:
            # 可能出错的代码
            api.log_info("处理请求")
        except Exception as e:
            api.log_error(f"处理请求失败: {e}")
            # 不要抛出异常，否则会阻止请求处理
```

### 3. 资源清理

如果插件需要清理临时文件或注册的资源：

```python
def register(api):
    import tempfile
    temp_dir = tempfile.mkdtemp()

    @api.add_teardown
    def cleanup(exception):
        import shutil
        shutil.rmtree(temp_dir, ignore_errors=True)
```

### 4. 依赖管理

明确声明插件依赖：

```python
def register(api):
    # 检查依赖
    try:
        import some_library
    except ImportError:
        api.log_error("需要安装 some_library")
        return
```

### 5. 配置管理

使用 `config.toml` 或插件配置：

```python
def register(api):
    enabled = api.get_plugin_config("my_plugin", "enabled", True)
    if not enabled:
        api.log_info("插件已禁用")
        return

    api.set_plugin_config("my_plugin", "last_run", datetime.now())
```

### 6. 文档完善

为插件编写清晰的文档：

```python
def register(api):
    """
    My Plugin - 插件功能描述

    功能:
    - 功能1
    - 功能2

    配置项:
    - option1: 说明1
    - option2: 说明2
    """
    pass
```

### 7. 版本兼容性

注意与不同版本 EverJudge 的兼容性：

```python
def register(api):
    version = api.config.get("EVERJUDGE_VERSION", "1.0.0")
    # 检查版本兼容性
```

## 故障排查

### 插件不加载

1. 检查 `plugin.toml` 是否存在且格式正确
2. 检查 `init.py` 中是否有 `register` 函数
3. 查看应用日志中的错误信息
4. 确保插件目录名与 `name` 字段一致

### 钩子不执行

1. 检查插件是否已启用
2. 检查 `hooks` 字段是否包含对应钩子
3. 检查钩子函数是否有异常

### 模板覆盖不生效

1. 确保已调用 `register_template_dir`
2. 检查模板路径是否正确
3. 检查 Jinja2 模板语法

### 评测机不工作

1. 检查语言是否被支持
2. 查看评测机日志
3. 检查 `priority` 设置

## 相关文档

- [EverJudge README](README.md)
- [Flask 文档](https://flask.palletsprojects.com/)
- [SQLAlchemy 文档](https://docs.sqlalchemy.org/)
- [Jinja2 模板](https://jinja.palletsprojects.com/)
