# 工具与装饰器
from .auth import login_required, admin_required
from .judge import JudgeClient, update_submission_status, judge_submission

__all__ = ["login_required", "admin_required", "JudgeClient", "update_submission_status", "judge_submission"]
