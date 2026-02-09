"""
Hello World 插件 - 展示插件系统的基本功能。
"""


def register(api):
    """
    插件注册函数。

    Args:
        api: PluginAPI 实例，提供各种插件功能
    """
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
