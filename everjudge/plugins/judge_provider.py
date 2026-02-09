"""
插件评测机替换系统
允许插件提供自定义评测机实现
"""
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass
from enum import Enum
import json


class JudgeStatus(Enum):
    """评测状态"""
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    ACCEPTED = "ACCEPTED"
    WRONG_ANSWER = "WRONG_ANSWER"
    TIME_LIMIT_EXCEEDED = "TIME_LIMIT_EXCEEDED"
    MEMORY_LIMIT_EXCEEDED = "MEMORY_LIMIT_EXCEEDED"
    RUNTIME_ERROR = "RUNTIME_ERROR"
    COMPILATION_ERROR = "COMPILATION_ERROR"
    SYSTEM_ERROR = "SYSTEM_ERROR"


@dataclass
class JudgeResult:
    """评测结果"""
    status: JudgeStatus
    score: int
    execution_time: int
    memory_used: int
    error_message: Optional[str] = None
    test_case_results: Optional[List['TestCaseResult']] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "status": self.status.value,
            "score": self.score,
            "execution_time": self.execution_time,
            "memory_used": self.memory_used,
            "error_message": self.error_message,
            "test_case_results": [
                r.to_dict() for r in (self.test_case_results or [])
            ] if self.test_case_results else None
        }


@dataclass
class TestCaseResult:
    """单个测试用例结果"""
    case_id: int
    status: JudgeStatus
    execution_time: int
    memory_used: int
    score: int
    error_message: Optional[str] = None
    input: Optional[str] = None
    expected_output: Optional[str] = None
    actual_output: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "case_id": self.case_id,
            "status": self.status.value,
            "execution_time": self.execution_time,
            "memory_used": self.memory_used,
            "score": self.score,
            "error_message": self.error_message,
        }


@dataclass
class JudgeRequest:
    """评测请求"""
    submission_id: int
    problem_id: int
    code: str
    language: str
    time_limit: int
    memory_limit: int
    test_cases: List[Dict[str, str]]

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'JudgeRequest':
        return cls(
            submission_id=data["submission_id"],
            problem_id=data["problem_id"],
            code=data["code"],
            language=data["language"],
            time_limit=data.get("time_limit", 1000),
            memory_limit=data.get("memory_limit", 134217728),
            test_cases=data.get("test_cases", [])
        )


class BaseJudgeProvider(ABC):
    """评测机提供者基类"""

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """提供者名称"""
        pass

    @property
    @abstractmethod
    def priority(self) -> int:
        """优先级，数值越大优先级越高"""
        return 0

    @abstractmethod
    def is_language_supported(self, language: str) -> bool:
        """检查是否支持指定语言"""
        pass

    @abstractmethod
    def judge(self, request: JudgeRequest) -> JudgeResult:
        """执行评测"""
        pass

    @abstractmethod
    def compile(self, code: str, language: str) -> tuple:
        """
        编译代码
        Returns: (success: bool, output_file: str, error_message: str)
        """
        pass

    @abstractmethod
    def run(
        self,
        executable: str,
        input_data: str,
        time_limit: int,
        memory_limit: int
    ) -> tuple:
        """
        运行程序
        Returns: (success: bool, output: str, execution_time: int, memory_used: int, error: str)
        """
        pass

    def before_judge(self, request: JudgeRequest) -> None:
        """评测前钩子"""
        pass

    def after_judge(self, request: JudgeRequest, result: JudgeResult) -> None:
        """评测后钩子"""
        pass


class DefaultJudgeProvider(BaseJudgeProvider):
    """默认评测机提供者（基于Rust后端）"""

    @property
    def provider_name(self) -> str:
        return "default"

    @property
    def priority(self) -> int:
        return 0

    def is_language_supported(self, language: str) -> bool:
        supported = [
            "c", "cpp", "java", "python_3", "python2",
            "javascript", "pascal", "common_lisp", "rust",
            "kotlin", "r", "brainfuck"
        ]
        return language.lower() in supported

    def judge(self, request: JudgeRequest) -> JudgeResult:
        """通过RPC调用Rust后端"""
        import socket
        import json as json_module

        config = self._get_judge_config()
        host = config.get("host", "127.0.0.1")
        port = config.get("port", 3726)

        request_data = {
            "action": "submit",
            "submission_id": request.submission_id,
            "problem_id": request.problem_id,
            "code": request.code,
            "language": request.language,
            "time_limit": request.time_limit,
            "memory_limit": request.memory_limit
        }

        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.connect((host, port))
            sock.send(json_module.dumps(request_data).encode())

            response = b""
            while True:
                chunk = sock.recv(4096)
                if not chunk:
                    break
                response += chunk

            sock.close()

            response_data = json_module.loads(response.decode())
            judge_id = response_data.get("judge_id")

            return self._wait_for_result(host, port, judge_id)

        except Exception as e:
            return JudgeResult(
                status=JudgeStatus.SYSTEM_ERROR,
                score=0,
                execution_time=0,
                memory_used=0,
                error_message=str(e)
            )

    def _wait_for_result(self, host: str, port: str, judge_id: str) -> JudgeResult:
        """等待评测结果"""
        import socket
        import json as json_module
        import time

        max_retries = 100
        retry_interval = 0.1

        for _ in range(max_retries):
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.connect((host, port))
                sock.settimeout(1)

                request = {
                    "action": "status",
                    "judge_id": judge_id
                }
                sock.send(json_module.dumps(request).encode())

                response = b""
                while True:
                    try:
                        chunk = sock.recv(4096)
                        if not chunk:
                            break
                        response += chunk
                    except socket.timeout:
                        break

                sock.close()

                if response:
                    response_data = json_module.loads(response.decode())
                    data = response_data.get("data", {})

                    status = data.get("status", "SYSTEM_ERROR")
                    try:
                        status = JudgeStatus(status)
                    except ValueError:
                        status = JudgeStatus.SYSTEM_ERROR

                    return JudgeResult(
                        status=status,
                        score=data.get("score", 0),
                        execution_time=data.get("execution_time", 0),
                        memory_used=data.get("memory_used", 0),
                        error_message=data.get("error_message")
                    )

                time.sleep(retry_interval)

            except Exception:
                time.sleep(retry_interval)

        return JudgeResult(
            status=JudgeStatus.SYSTEM_ERROR,
            score=0,
            execution_time=0,
            memory_used=0,
            error_message="Timeout waiting for judge result"
        )

    def compile(self, code: str, language: str) -> tuple:
        """默认不编译，由Rust后端处理"""
        return (True, "", "")

    def run(
        self,
        executable: str,
        input_data: str,
        time_limit: int,
        memory_limit: int
    ) -> tuple:
        """默认不运行，由Rust后端处理"""
        return ("", 0, 0, "")

    def _get_judge_config(self) -> Dict[str, Any]:
        """获取评测机配置"""
        import os

        config_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            "judge-backend",
            "judge.toml"
        )

        if os.path.exists(config_path):
            import toml
            with open(config_path, 'r') as f:
                return toml.load(f).get("server", {})

        return {"host": "127.0.0.1", "port": 3726}


class JudgeProviderRegistry:
    """评测机提供者注册表"""

    def __init__(self):
        self._providers: Dict[str, BaseJudgeProvider] = {}
        self._default_provider: Optional[BaseJudgeProvider] = None

    def register(self, provider: BaseJudgeProvider, as_default: bool = False):
        """注册评测机提供者"""
        self._providers[provider.provider_name] = provider

        if as_default or self._default_provider is None:
            if self._default_provider is None or provider.priority > self._default_provider.priority:
                self._default_provider = provider

    def get_provider(self, name: str) -> Optional[BaseJudgeProvider]:
        """获取指定提供者"""
        return self._providers.get(name)

    def get_default_provider(self) -> BaseJudgeProvider:
        """获取默认提供者"""
        if self._default_provider is None:
            self._default_provider = DefaultJudgeProvider()
            self.register(self._default_provider)
        return self._default_provider

    def get_provider_for_language(self, language: str) -> BaseJudgeProvider:
        """获取支持指定语言的提供者"""
        for name, provider in self._providers.items():
            if provider.is_language_supported(language):
                if self._default_provider is None or \
                   provider.priority >= self._default_provider.priority:
                    return provider

        return self.get_default_provider()

    def list_providers(self) -> List[Dict[str, Any]]:
        """列出所有提供者"""
        return [
            {
                "name": p.provider_name,
                "priority": p.priority,
                "default": p is self._default_provider
            }
            for p in self._providers.values()
        ]


class PluginJudgeManager:
    """插件评测机管理器"""

    def __init__(self):
        self.registry = JudgeProviderRegistry()
        self._setup_default_provider()

    def _setup_default_provider(self):
        """设置默认提供者"""
        default = DefaultJudgeProvider()
        self.registry.register(default, as_default=True)

    def register_provider(
        self,
        provider: BaseJudgeProvider,
        as_default: bool = False
    ):
        """注册插件提供的评测机"""
        self.registry.register(provider, as_default)

    def judge(
        self,
        request: JudgeRequest,
        provider_name: str = None
    ) -> JudgeResult:
        """执行评测"""
        if provider_name:
            provider = self.registry.get_provider(provider_name)
            if provider is None:
                provider = self.registry.get_provider_for_language(request.language)
        else:
            provider = self.registry.get_provider_for_language(request.language)

        provider.before_judge(request)
        result = provider.judge(request)
        provider.after_judge(request, result)

        return result

    def is_language_supported(
        self,
        language: str,
        provider_name: str = None
    ) -> bool:
        """检查语言是否被支持"""
        if provider_name:
            provider = self.registry.get_provider(provider_name)
            return provider.is_language_supported(language) if provider else False

        provider = self.registry.get_provider_for_language(language)
        return provider.is_language_supported(language)

    def get_supported_languages(self, provider_name: str = None) -> List[str]:
        """获取支持的语言列表"""
        if provider_name:
            provider = self.registry.get_provider(provider_name)
            if provider:
                return self._get_all_supported_languages(provider)
            return []

        languages = set()
        for provider in self._providers.values():
            languages.update(self._get_all_supported_languages(provider))
        return sorted(languages)

    def _get_all_supported_languages(self, provider: BaseJudgeProvider) -> List[str]:
        """获取提供者的所有支持语言"""
        if hasattr(provider, 'supported_languages'):
            return provider.supported_languages
        return [provider.provider_name]


def get_judge_manager() -> PluginJudgeManager:
    """获取评测机管理器单例"""
    from flask import current_app

    if hasattr(current_app, '_judge_manager'):
        return current_app._judge_manager

    from everjudge.app import create_app
    app = create_app()
    with app.app_context():
        manager = PluginJudgeManager()
        current_app._judge_manager = manager
        return manager
