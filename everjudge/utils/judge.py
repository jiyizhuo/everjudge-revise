import json
import socket
import time
from typing import Dict, Any, Optional

from ..extensions import db
from ..models import Submission


class JudgeClient:
    def __init__(self, host: str = '127.0.0.1', port: int = 3726):
        self.host = host
        self.port = port

    def submit_code(self, submission: Submission) -> Optional[str]:
        """
        提交代码到评测机
        :param submission: 提交记录
        :return: 评测任务ID
        """
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.connect((self.host, self.port))
                data = {
                    'action': 'submit',
                    'submission_id': submission.id,
                    'problem_id': submission.problem_id,
                    'code': submission.code,
                    'language': submission.language,
                    'time_limit': submission.problem.time_limit,
                    'memory_limit': submission.problem.memory_limit * 1024 * 1024  # 转换为字节
                }
                s.sendall(json.dumps(data).encode('utf-8') + b'\n')
                response = s.recv(1024).decode('utf-8')
                result = json.loads(response)
                if result.get('status') == 'ok':
                    return result.get('judge_id')
                return None
        except Exception as e:
            print(f"Error submitting to judge: {e}")
            return None

    def get_status(self, judge_id: str) -> Optional[Dict[str, Any]]:
        """
        获取评测状态
        :param judge_id: 评测任务ID
        :return: 评测结果
        """
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.connect((self.host, self.port))
                data = {
                    'action': 'status',
                    'judge_id': judge_id
                }
                s.sendall(json.dumps(data).encode('utf-8') + b'\n')
                response = s.recv(4096).decode('utf-8')
                result = json.loads(response)
                if result.get('status') == 'ok':
                    return result.get('data')
                return None
        except Exception as e:
            print(f"Error getting judge status: {e}")
            return None


def update_submission_status(submission_id: int):
    """
    更新提交记录的评测状态
    :param submission_id: 提交记录ID
    """
    submission = Submission.query.get(submission_id)
    if not submission or not submission.judge_id:
        return

    judge_client = JudgeClient()
    status = judge_client.get_status(submission.judge_id)
    if status:
        submission.status = status.get('status', 'SYSTEM_ERROR')
        submission.score = status.get('score', 0)
        submission.execution_time = status.get('execution_time')
        submission.memory_used = status.get('memory_used')
        submission.error_message = status.get('error_message')
        db.session.commit()


def judge_submission(submission_id: int):
    """
    评测提交记录
    :param submission_id: 提交记录ID
    """
    submission = Submission.query.get(submission_id)
    if not submission:
        return

    submission.status = 'RUNNING'
    db.session.commit()

    judge_client = JudgeClient()
    judge_id = judge_client.submit_code(submission)
    if judge_id:
        submission.judge_id = judge_id
        db.session.commit()
        
        # 轮询评测结果
        for _ in range(30):  # 最多轮询30次
            time.sleep(1)
            update_submission_status(submission_id)
            submission = Submission.query.get(submission_id)
            if submission.status not in ['PENDING', 'RUNNING']:
                break
    else:
        submission.status = 'SYSTEM_ERROR'
        submission.error_message = 'Failed to connect to judge server'
        db.session.commit()