from sqlalchemy import Column, Integer, String, Text, Boolean, ForeignKey, DateTime, Float
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from everjudge.extensions import db


class Problem(db.Model):
    __tablename__ = 'problems'

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False, index=True)
    description = Column(Text, nullable=False)
    time_limit = Column(Integer, nullable=False, default=1000)  # 毫秒
    memory_limit = Column(Integer, nullable=False, default=256)  # MB
    difficulty = Column(Integer, nullable=False, default=0)  # 0-7
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    author = Column(String(100), nullable=False)
    visible = Column(Boolean, default=True)
    library = Column(String(50), nullable=False, default="public")  # public, private, personal

    # 关联
    test_cases = relationship('TestCase', back_populates='problem', cascade='all, delete-orphan')
    submissions = relationship('Submission', back_populates='problem')

    def __repr__(self):
        return f'<Problem {self.id}: {self.title}>'