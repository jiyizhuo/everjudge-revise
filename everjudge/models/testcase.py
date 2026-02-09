from sqlalchemy import Column, Integer, String, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from everjudge.extensions import db


class TestCase(db.Model):
    __tablename__ = 'test_cases'

    id = Column(Integer, primary_key=True, index=True)
    problem_id = Column(Integer, ForeignKey('problems.id'), nullable=False)
    case_number = Column(Integer, nullable=False)
    input_path = Column(String(255), nullable=False)
    output_path = Column(String(255), nullable=False)
    score = Column(Integer, nullable=False, default=10)
    is_sample = Column(Boolean, default=False)
    time_limit = Column(Integer, nullable=True)  # 单个测试用例的时间限制（毫秒）
    memory_limit = Column(Integer, nullable=True)  # 单个测试用例的内存限制（MB）

    # 关联
    problem = relationship('Problem', back_populates='test_cases')

    def __repr__(self):
        return f'<TestCase {self.id} for Problem {self.problem_id}, Case {self.case_number}>'