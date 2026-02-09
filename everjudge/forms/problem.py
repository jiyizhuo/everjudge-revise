from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, IntegerField, BooleanField, SelectField, SubmitField
from wtforms.validators import DataRequired, Length, NumberRange, Optional


class ProblemForm(FlaskForm):
    title = StringField('题目名称', validators=[DataRequired(), Length(min=1, max=255)])
    description = TextAreaField('题目描述', validators=[DataRequired()])
    time_limit = IntegerField('时间限制 (毫秒)', validators=[DataRequired(), NumberRange(min=1, max=10000)])
    memory_limit = IntegerField('内存限制 (MB)', validators=[DataRequired(), NumberRange(min=1, max=1024)])
    difficulty = IntegerField('难度等级 (0-7)', validators=[NumberRange(min=0, max=7)])
    library = SelectField('题库', validators=[DataRequired()], choices=[
        ('public', '主题库'),
        ('private', '私有题库'),
        ('remote', '远程题库')
    ], default='public')
    visible = BooleanField('是否可见', default=True)
    submit = SubmitField('保存')
    
    def validate_difficulty(self, field):
        """自定义验证函数，确保difficulty字段可以接受0作为有效值"""
        if field.data is None:
            raise DataRequired('该字段是必填字段。')
        if not (0 <= field.data <= 7):
            raise NumberRange('难度等级必须在0-7之间。')


class SubmissionForm(FlaskForm):
    code = TextAreaField('代码', validators=[DataRequired()])
    language = SelectField('编程语言', validators=[DataRequired()])
    submit = SubmitField('提交')
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from flask import current_app
        # 从app.config中获取支持的语言列表
        self.language.choices = current_app.config.get('SUPPORTED_LANGUAGES', [
            ('python3', 'Python 3'),
            ('c', 'C'),
            ('cpp', 'C++'),
            ('java', 'Java'),
            ('rust', 'Rust')
        ])


class TestCaseForm(FlaskForm):
    case_number = IntegerField('测试用例编号', validators=[DataRequired()])
    score = IntegerField('分值', validators=[DataRequired(), NumberRange(min=1, max=100)])
    time_limit = IntegerField('时间限制 (毫秒)', validators=[Optional(), NumberRange(min=1, max=10000)])
    memory_limit = IntegerField('内存限制 (MB)', validators=[Optional(), NumberRange(min=1, max=1024)])
    is_sample = BooleanField('是否为样例', default=False)
    submit = SubmitField('保存')