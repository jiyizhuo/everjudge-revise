"""
插件数据模型。
"""
from datetime import datetime
from ..extensions import db


class Plugin(db.Model):
    __tablename__ = "plugins"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False, index=True)
    version = db.Column(db.String(50))
    description = db.Column(db.Text)
    author = db.Column(db.String(200))
    enabled = db.Column(db.Boolean, default=False, nullable=False)
    installed_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_updated = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    hooks = db.Column(db.Text)
    config = db.Column(db.Text)

    def __repr__(self):
        return f"<Plugin {self.name} v{self.version}>"

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "version": self.version,
            "description": self.description,
            "author": self.author,
            "enabled": self.enabled,
            "installed_at": self.installed_at.isoformat() if self.installed_at else None,
            "last_updated": self.last_updated.isoformat() if self.last_updated else None,
            "hooks": self.hooks.split(",") if self.hooks else [],
        }

    @property
    def hooks_list(self):
        if self.hooks:
            return [h.strip() for h in self.hooks.split(",")]
        return []

    @hooks_list.setter
    def hooks_list(self, value):
        if isinstance(value, list):
            self.hooks = ",".join(value)
        else:
            self.hooks = str(value)
