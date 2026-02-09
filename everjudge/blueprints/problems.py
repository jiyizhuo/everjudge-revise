"""
题目蓝图：题单、题目详情、提交（Phase 3 完善）。
"""
import os
import shutil
import zipfile
from flask import Blueprint, render_template, redirect, url_for, request, flash, jsonify, current_app
from flask_login import current_user, login_required
from werkzeug.utils import secure_filename

from ..extensions import db
from ..models import Problem, TestCase, Submission
from ..forms import ProblemForm, SubmissionForm, TestCaseForm
from ..utils import admin_required, judge_submission
# 不再使用get_config函数


bp = Blueprint("problems", __name__)


@bp.route("/")
def index():
    page = request.args.get('page', 1, type=int)
    per_page = 20
    
    # 构建查询
    if current_user.is_authenticated and current_user.is_root:
        # root用户可以看到所有题目
        query = Problem.query
    elif current_user.is_authenticated:
        # 已登录用户可以看到：可见的非私有题目 + 自己的私有题目
        query = Problem.query.filter(
            ((Problem.visible == True) & (Problem.library != 'private')) |
            ((Problem.library == 'private') & (Problem.author == current_user.username))
        )
    else:
        # 未登录用户只能看到可见的非私有题目
        query = Problem.query.filter_by(visible=True).filter(Problem.library != 'private')
    
    # 根据题库筛选
    library = request.args.get('library')
    if library:
        if current_user.is_authenticated and current_user.is_root:
            # root用户可以看到指定题库的所有题目
            query = Problem.query.filter_by(library=library)
        elif current_user.is_authenticated:
            # 已登录用户可以看到：指定题库的可见题目 + 自己的私有题目（如果筛选的是私有题库）
            if library == 'private':
                query = Problem.query.filter(
                    (Problem.library == 'private') &
                    (Problem.author == current_user.username)
                )
            else:
                query = Problem.query.filter_by(visible=True, library=library)
        else:
            # 未登录用户只能看到指定题库的可见题目
            query = Problem.query.filter_by(visible=True, library=library)
    
    problems = query.paginate(page=page, per_page=per_page, error_out=False)
    return render_template("problems/index.html", problems=problems)


@bp.route("/create", methods=["GET", "POST"])
@login_required
def create():
    form = ProblemForm()
    
    # 根据用户权限限制可选择的题库
    if not (current_user.is_admin or current_user.is_root):
        # 正常用户只能选择私有题库
        form.library.choices = [('private', '私有题库')]
        form.library.default = 'private'
        form.library.data = 'private'
    
    if form.validate_on_submit():
        # 确保正常用户只能创建私有题库的题目
        if not (current_user.is_admin or current_user.is_root):
            form.library.data = 'private'
        
        problem = Problem(
            title=form.title.data,
            description=form.description.data,
            time_limit=form.time_limit.data,
            memory_limit=form.memory_limit.data,
            difficulty=form.difficulty.data,
            author=current_user.username,
            visible=form.visible.data,
            library=form.library.data
        )
        db.session.add(problem)
        db.session.commit()
        
        # 创建题目目录
        problem_dir = os.path.join(current_app.config['PROBLEMS_DIR'], str(problem.id))
        os.makedirs(problem_dir, exist_ok=True)
        os.makedirs(os.path.join(problem_dir, 'testcases'), exist_ok=True)
        
        flash("题目创建成功", "success")
        return redirect(url_for("problems.edit", id=problem.id))
    testcase_form = TestCaseForm()
    return render_template("problems/edit.html", form=form, testcase_form=testcase_form, problem=None)


@bp.route("/<int:id>")
def detail(id):
    problem = Problem.query.get_or_404(id)
    
    # 检查可见性
    if not problem.visible:
        if not (current_user.is_authenticated and current_user.is_admin):
            flash("题目不存在或不可见", "danger")
            return redirect(url_for("problems.index"))
    
    # 私有题库的题目可以通过直接链接访问
    # 这里可以添加更复杂的权限检查，比如检查用户是否有访问权
    
    sample_test_cases = TestCase.query.filter_by(problem_id=id, is_sample=True).order_by(TestCase.case_number).all()
    form = SubmissionForm()
    
    # 查询用户的最近提交记录
    recent_submissions = []
    if current_user.is_authenticated:
        from ..models import Submission
        recent_submissions = Submission.query.filter_by(
            user_id=current_user.id,
            problem_id=id
        ).order_by(Submission.created_at.desc()).limit(5).all()
    
    return render_template("problems/detail.html", problem=problem, sample_test_cases=sample_test_cases, form=form, recent_submissions=recent_submissions)


@bp.route("/<int:id>/edit", methods=["GET", "POST"])
@login_required
def edit(id):
    problem = Problem.query.get_or_404(id)
    
    # 检查权限
    # 主题库只有root用户与admin用户可以修改
    # 私有题库可以赋予他人修改权（这里简化处理，只允许创建者和管理员修改）
    if problem.library == 'public':
        if not (current_user.is_admin or current_user.is_root):
            flash("权限不足，只有管理员可以修改主题库的题目", "danger")
            return redirect(url_for("problems.detail", id=id))
    else:
        # 私有题库和远程题库的权限检查
        if not (current_user.is_admin or current_user.is_root or problem.author == current_user.username):
            flash("权限不足，只有创建者和管理员可以修改该题目", "danger")
            return redirect(url_for("problems.detail", id=id))
    form = ProblemForm(obj=problem)
    if form.validate_on_submit():
        form.populate_obj(problem)
        db.session.commit()
        flash("题目更新成功", "success")
        return redirect(url_for("problems.edit", id=id))
    
    test_cases = TestCase.query.filter_by(problem_id=id).order_by(TestCase.case_number).all()
    testcase_form = TestCaseForm()
    return render_template("problems/edit.html", form=form, testcase_form=testcase_form, problem=problem, test_cases=test_cases)


@bp.route("/<int:id>/delete", methods=["POST"])
def delete(id):
    if not current_user.is_authenticated or not current_user.is_admin:
        flash("权限不足", "danger")
        return redirect(url_for("problems.index"))
    
    problem = Problem.query.get_or_404(id)
    
    # 删除题目目录
    problem_dir = os.path.join(current_app.config['PROBLEMS_DIR'], str(id))
    if os.path.exists(problem_dir):
        shutil.rmtree(problem_dir)
    
    db.session.delete(problem)
    db.session.commit()
    flash("题目删除成功", "success")
    return redirect(url_for("problems.index"))


@bp.route("/<int:id>/submit", methods=["POST"])
@login_required
def submit(id):
    problem = Problem.query.get_or_404(id)
    if not problem.visible and not current_user.is_admin:
        flash("题目不存在或不可见", "danger")
        return redirect(url_for("problems.index"))
    
    form = SubmissionForm()
    if form.validate_on_submit():
        submission = Submission(
            problem_id=id,
            user_id=current_user.id,
            code=form.code.data,
            language=form.language.data,
            status="PENDING",
            score=0
        )
        db.session.add(submission)
        db.session.commit()
        
        # 异步评测
        import threading
        thread = threading.Thread(target=judge_submission, args=(submission.id,))
        thread.daemon = True
        thread.start()
        
        flash("代码提交成功，正在评测中", "success")
        return redirect(url_for("problems.submission", id=submission.id))
    
    sample_test_cases = TestCase.query.filter_by(problem_id=id, is_sample=True).order_by(TestCase.case_number).all()
    return render_template("problems/detail.html", problem=problem, sample_test_cases=sample_test_cases, form=form)


@bp.route("/submission/<int:id>")
def submission(id):
    submission = Submission.query.get_or_404(id)
    if not (current_user.is_authenticated and (current_user.id == submission.user_id or current_user.is_admin)):
        flash("无权限查看该提交", "danger")
        return redirect(url_for("problems.index"))
    return render_template("problems/submission.html", submission=submission)


@bp.route("/submissions")
@login_required
def submissions():
    page = request.args.get('page', 1, type=int)
    per_page = 20
    query = Submission.query.filter_by(user_id=current_user.id)
    
    # 如果是管理员，可以查看所有提交
    if current_user.is_admin:
        problem_id = request.args.get('problem_id', type=int)
        if problem_id:
            query = query.filter_by(problem_id=problem_id)
    
    submissions = query.order_by(Submission.created_at.desc()).paginate(page=page, per_page=per_page, error_out=False)
    return render_template("problems/submissions.html", submissions=submissions)


@bp.route("/<int:id>/testcases/add", methods=["POST"])
@login_required
@admin_required
def add_testcase(id):
    problem = Problem.query.get_or_404(id)
    form = TestCaseForm()
    if form.validate_on_submit():
        # 保存测试用例文件
        testcases_dir = os.path.join(current_app.config['PROBLEMS_DIR'], str(id), 'testcases')
        
        input_file = request.files.get('input_file')
        output_file = request.files.get('output_file')
        
        if not input_file or not output_file:
            flash("请上传输入和输出文件", "danger")
            return redirect(url_for("problems.edit", id=id))
        
        input_filename = secure_filename(f"{form.case_number.data}.in")
        output_filename = secure_filename(f"{form.case_number.data}.out")
        
        input_path = os.path.join(testcases_dir, input_filename)
        output_path = os.path.join(testcases_dir, output_filename)
        
        input_file.save(input_path)
        output_file.save(output_path)
        
        # 创建测试用例记录
        testcase = TestCase(
            problem_id=id,
            case_number=form.case_number.data,
            input_path=os.path.join('testcases', input_filename),
            output_path=os.path.join('testcases', output_filename),
            score=form.score.data,
            time_limit=form.time_limit.data,
            memory_limit=form.memory_limit.data,
            is_sample=form.is_sample.data
        )
        db.session.add(testcase)
        db.session.commit()
        
        flash("测试用例添加成功", "success")
    return redirect(url_for("problems.edit", id=id))


@bp.route("/<int:id>/testcases/<int:case_id>/delete", methods=["POST"])
@login_required
@admin_required
def delete_testcase(id, case_id):
    testcase = TestCase.query.get_or_404(case_id)
    if testcase.problem_id != id:
        flash("测试用例不存在", "danger")
        return redirect(url_for("problems.edit", id=id))
    
    # 删除测试用例文件
    problem_dir = os.path.join(current_app.config['PROBLEMS_DIR'], str(id))
    input_file = os.path.join(problem_dir, testcase.input_path)
    output_file = os.path.join(problem_dir, testcase.output_path)
    
    if os.path.exists(input_file):
        os.remove(input_file)
    if os.path.exists(output_file):
        os.remove(output_file)
    
    db.session.delete(testcase)
    db.session.commit()
    flash("测试用例删除成功", "success")
    return redirect(url_for("problems.edit", id=id))


@bp.route("/<int:id>/testcases/upload", methods=["POST"])
@login_required
@admin_required
def upload_testcases_zip(id):
    """
    上传包含测试用例的zip文件
    """
    problem = Problem.query.get_or_404(id)
    
    # 检查权限
    if problem.library == 'public':
        if not (current_user.is_admin or current_user.is_root):
            flash("权限不足，只有管理员可以修改主题库的题目", "danger")
            return redirect(url_for("problems.detail", id=id))
    else:
        if not (current_user.is_admin or current_user.is_root or problem.author == current_user.username):
            flash("权限不足，只有创建者和管理员可以修改该题目", "danger")
            return redirect(url_for("problems.detail", id=id))
    
    zip_file = request.files.get('zip_file')
    if not zip_file:
        flash("请上传zip文件", "danger")
        return redirect(url_for("problems.edit", id=id))
    
    # 检查文件类型
    if not zip_file.filename.endswith('.zip'):
        flash("请上传zip格式的文件", "danger")
        return redirect(url_for("problems.edit", id=id))
    
    # 创建临时目录
    temp_dir = os.path.join(current_app.config['PROBLEMS_DIR'], 'temp')
    os.makedirs(temp_dir, exist_ok=True)
    
    # 保存zip文件
    zip_filename = secure_filename(f"testcases_{id}_{zip_file.filename}")
    zip_path = os.path.join(temp_dir, zip_filename)
    zip_file.save(zip_path)
    
    try:
        # 解压zip文件
        testcases_dir = os.path.join(current_app.config['PROBLEMS_DIR'], str(id), 'testcases')
        
        # 清空现有测试用例
        for testcase in TestCase.query.filter_by(problem_id=id).all():
            db.session.delete(testcase)
        db.session.commit()
        
        # 删除现有测试用例文件
        if os.path.exists(testcases_dir):
            shutil.rmtree(testcases_dir)
        os.makedirs(testcases_dir, exist_ok=True)
        
        # 解压zip文件
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(testcases_dir)
        
        # 创建测试用例记录
        case_number = 1
        for filename in sorted(os.listdir(testcases_dir)):
            if filename.endswith('.in'):
                input_filename = filename
                output_filename = filename.replace('.in', '.out')
                output_path = os.path.join(testcases_dir, output_filename)
                
                # 检查输出文件是否存在
                if os.path.exists(output_path):
                    testcase = TestCase(
                        problem_id=id,
                        case_number=case_number,
                        input_path=os.path.join('testcases', input_filename),
                        output_path=os.path.join('testcases', output_filename),
                        score=10,  # 默认分数
                        time_limit=problem.time_limit,  # 从题目级别继承时间限制
                        memory_limit=problem.memory_limit,  # 从题目级别继承内存限制
                        is_sample=False
                    )
                    db.session.add(testcase)
                    case_number += 1
        
        db.session.commit()
        flash(f"成功上传{case_number - 1}个测试用例", "success")
        
    except Exception as e:
        flash(f"上传测试用例失败: {str(e)}", "danger")
    finally:
        # 清理临时文件
        if os.path.exists(zip_path):
            os.remove(zip_path)
    
    return redirect(url_for("problems.edit", id=id))


@bp.route("/submission/<int:id>/status")
def submission_status(id):
    submission = Submission.query.get_or_404(id)
    if not (current_user.is_authenticated and (current_user.id == submission.user_id or current_user.is_admin)):
        return jsonify({"error": "无权限查看该提交"}), 403
    
    return jsonify({
        "status": submission.status,
        "score": submission.score,
        "execution_time": submission.execution_time,
        "memory_used": submission.memory_used
    })
