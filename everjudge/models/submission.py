from sqlalchemy import Column, Integer, String, Text, ForeignKey, DateTime, Boolean, Float
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from everjudge.extensions import db


class Submission(db.Model):
    __tablename__ = 'submissions'

    id = Column(Integer, primary_key=True, index=True)
    problem_id = Column(Integer, ForeignKey('problems.id'), nullable=False)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    code = Column(Text, nullable=False)
    language = Column(String(50), nullable=False)
    status = Column(String(50), nullable=False, default='PENDING')  # PENDING, RUNNING, ACCEPTED, WRONG_ANSWER, TIME_LIMIT_EXCEEDED, MEMORY_LIMIT_EXCEEDED, RUNTIME_ERROR, COMPILATION_ERROR, SYSTEM_ERROR
    score = Column(Integer, nullable=False, default=0)
    execution_time = Column(Integer)  # 毫秒
    memory_used = Column(Integer)  # KB
    error_message = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    judge_id = Column(String(100))

    # 关联
    problem = relationship('Problem', back_populates='submissions')
    user = relationship('User', back_populates='submissions')

    def __repr__(self):
        return f'<Submission {self.id} for Problem {self.problem_id} by User {self.user_id}>'