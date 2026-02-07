# 表单包：WTForms 定义
from .auth import RegisterForm, LoginForm, ForgotPasswordForm, ResetPasswordForm
from .problem import ProblemForm, SubmissionForm, TestCaseForm
from .user import UserForm

__all__ = ["RegisterForm", "LoginForm", "ForgotPasswordForm", "ResetPasswordForm", "ProblemForm", "SubmissionForm", "TestCaseForm", "UserForm"]
