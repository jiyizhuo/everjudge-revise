"""
用户模型：账户系统基础。支持角色与权限扩展。
"""
from datetime import datetime
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy.orm import relationship

from ..extensions import db


class User(UserMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    username = db.Column(db.String(64), unique=True, nullable=False, index=True)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    nickname = db.Column(db.String(64), default="")
    # 角色: admin, user, banned 等
    role = db.Column(db.String(32), default="user", nullable=False)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_login_at = db.Column(db.DateTime, nullable=True)

    def __repr__(self):
        return f"<User {self.username}>"

    def set_password(self, password: str) -> None:
        self.password_hash = generate_password_hash(password, method="scrypt")

    def check_password(self, password: str) -> bool:
        return bool(self.password_hash and check_password_hash(self.password_hash, password))

    @property
    def is_guest(self) -> bool:
        return self.role == "guest"

    @property
    def is_unauthorized(self) -> bool:
        return self.role == "unauthorized"

    @property
    def is_user(self) -> bool:
        return self.role == "user"

    @property
    def is_admin(self) -> bool:
        return self.role == "admin"

    @property
    def is_root(self) -> bool:
        return self.role == "root"

    @property
    def is_banned(self) -> bool:
        return self.role == "banned"

    def has_permission(self, required_role: str) -> bool:
        """
        检查用户是否有足够的权限
        权限等级：guest < unauthorized < user < admin < root
        """
        role_levels = {
            "guest": 0,
            "unauthorized": 1,
            "user": 2,
            "admin": 3,
            "root": 4
        }
        user_level = role_levels.get(self.role, 0)
        required_level = role_levels.get(required_role, 0)
        return user_level >= required_level

    # 关联
    submissions = relationship('Submission', back_populates='user')
