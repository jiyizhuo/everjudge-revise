# EverJudge

基于 Python3 / Flask / SQLAlchemy / WTForms + HTML5 / jQuery / Tailwind 的 OJ 系统，评测机后端使用 Rust 实现。配置统一使用 TOML，部署使用 uWSGI，支持多数据库与 i18n。

## 功能模块（分步实现）

- **Phase 1** ✅ 项目结构、TOML 配置、Flask 骨架、多数据库支持
- **Phase 2** ✅ 账户系统（注册/登录/权限、WTForms、管理员 CLI）
- **Phase 3** ✅ 题面管理、测试数据、评测系统集成
- **Phase 4** ✅ Rust 评测机后端（支持 TOML 配置、多语言评测、多线程处理）
- **Phase 5** 插件系统
- **Phase 6** 博客与讨论区
- **Phase 7** 管理后台、i18n 完善、uWSGI 部署

## 技术栈

- **Web**: Python 3, Flask, SQLAlchemy, WTForms, Flask-Login, Flask-Babel, Flask-Migrate
- **前端**: HTML5, jQuery, Tailwind CSS
- **配置**: TOML（必要时 BSON）
- **数据库**: SQLite / MySQL / MariaDB / Oracle
- **评测机**: Rust（独立服务，Phase 4）
- **部署**: uWSGI
- **依赖管理**: **推荐使用 [uv](https://github.com/astral-sh/uv)** 管理虚拟环境与依赖（更快、锁版本一致）

## 快速开始

**推荐使用 uv**（需先安装 [uv](https://github.com/astral-sh/uv)）：

```bash
# 使用 uv 创建虚拟环境并安装依赖（推荐）
uv venv
.venv\Scripts\activate   # Windows
uv pip install -r requirements.txt

# 使用默认 config.toml（SQLite）
python run.py
# 或：flask --app everjudge run
```

或使用传统方式：

```bash
python -m venv .venv
.venv\Scripts\activate   # Windows
pip install -r requirements.txt
python run.py
```

访问 http://127.0.0.1:5000 。

## 配置说明

主配置为项目根目录下的 `config.toml`，可设置：

- `[server]`  host/port/debug
- `[database]` driver（sqlite/mysql/mariadb/oracle）及对应连接参数
- `[security]` secret_key、cookie、密码策略
- `[judge]` 评测机 RPC 地址
- `[i18n]` 默认与支持的语言
- `[storage]` 数据目录
- `[plugins]` 是否启用插件及插件目录
- **`[root]` 默认 root 用户**：`username`（默认 `root`）、`password`（留空则 root 无法密码登录）、`login_enabled`（是否允许 root 通过登录页登录）。首次启动会自动创建 root 账户，每次启动会按配置同步密码。
- **`[theme]` 前端主题**：仅 `primary`（主色调，十六进制，默认 `#39C5BB`）。深浅色由客户端决定：首次按系统 `prefers-color-scheme`，用户点击切换后写入本地存储。

环境变量可覆盖：`SECRET_KEY`、`EVERJUDGE_CONFIG`、`DATABASE_URI`。

**调试模式**：`config.toml` 中 `[server] debug = true` 或设置环境变量 `FLASK_DEBUG=1` 可开启调试模式；会启用更详细的 logging（含请求/响应、DEBUG 级别日志）。

## 账户系统（Phase 2）

- **默认 root 用户**：应用首次启动时会自动创建用户名为 `config.toml` 中 `[root]` 的 `username`（默认 `root`）的管理员。在 `[root]` 中设置 `password` 可修改 root 密码（每次启动会同步）；设置 `login_enabled = false` 可禁止 root 通过登录页登录（仅能通过其他管理员或 CLI 管理）。
- **注册 / 登录**：`/auth/register`、`/auth/login`，使用 WTForms 校验，密码由 config.toml 的 `[security]` 中 `password_min_length` 控制。用户名为 root 的账户不可被注册。
- **创建其他管理员**（可选）：
  ```bash
  flask create-admin --username admin --email admin@localhost
  # 按提示输入密码
  ```
- **权限**：`everjudge.utils.auth` 提供 `@login_required`、`@admin_required` 装饰器，供后续管理后台等使用。

## 数据库迁移

```bash
flask db init
flask db migrate -m "描述"
flask db upgrade
```

## 生产部署（uWSGI）

```bash
pip install uwsgi
mkdir -p logs
uwsgi --ini uwsgi.ini
```

## 项目结构

```
EverJudge/
├── config.toml          # 主配置
├── run.py               # 开发运行入口
├── wsgi.py              # uWSGI 入口
├── uwsgi.ini
├── babel.cfg            # i18n 提取配置
├── everjudge/           # Flask 应用包
│   ├── app.py           # 应用工厂
│   ├── config.py        # TOML 加载与多数据库 URL
│   ├── extensions.py    # db, login_manager, migrate
│   ├── blueprints/      # 路由蓝图
│   ├── models/          # SQLAlchemy 模型
│   └── plugins/         # 插件加载
├── templates/
├── translations/        # Babel 翻译
├── data/                # 数据目录（SQLite、题目、提交等）
└── judge-backend/       # Rust 评测机（Phase 4）
```

## 评测机后端（Phase 4）

### 功能特点

- **多语言支持**：支持 C、C++、Java、JavaScript (Node.js)、Python 2、Python 3、Pascal、Common Lisp、Plain Text、Brainfuck、R、Rust、Kotlin 共 13 种语言
- **两阶段评测**：编译阶段（编译型语言）和运行阶段（所有语言）
- **多线程处理**：使用 Rust 标准库的线程池，支持并发评测多个提交
- **时间与内存限制**：支持设置每个测试用例的时间限制和内存限制
- **测试用例评估**：基于测试用例的输入输出比对，计算得分
- **TCP 通信**：使用 TCP socket 与 EverJudge 主系统通信，支持 JSON 格式的请求和响应

### 多线程评测系统

#### 核心组件

- **ThreadPool**：线程池管理，包含工作线程、任务队列、关闭标志和活跃任务计数
- **工作线程**：每个工作线程从任务队列中获取任务并执行
- **任务队列**：使用 `mpsc::channel` 进行任务分发和结果返回
- **并发控制**：使用 `AtomicUsize` 进行原子操作来跟踪活跃任务数量

#### 工作流程

1. **任务提交**：客户端提交评测请求到服务器
2. **任务入队**：服务器将任务放入任务队列
3. **任务分发**：空闲的工作线程从队列中获取任务
4. **并发执行**：多个工作线程同时执行不同的评测任务
5. **结果返回**：工作线程将评测结果返回给调用者
6. **状态更新**：主线程更新任务状态为最终结果

#### 性能优化

- **线程池大小**：可通过配置文件调整线程池大小，默认为 4 个工作线程
- **任务队列**：使用无界队列，支持处理大量并发请求
- **原子操作**：使用 `AtomicUsize` 进行原子操作，避免锁竞争
- **超时机制**：工作线程使用 `recv_timeout` 避免无限等待

#### 状态监控

提供了 `stats` 请求来查询当前活跃任务数量：

```json
{
  "action": "stats"
}
```

响应示例：

```json
{
  "status": "ok",
  "judge_id": null,
  "data": {
    "status": "RUNNING",
    "score": 2,  // 当前活跃任务数量
    "execution_time": null,
    "memory_used": null,
    "error_message": null
  },
  "error": null
}
```

### 配置说明

评测机后端的配置通过 `judge-backend/judge.toml` 文件实现：

```toml
[server]
host = "127.0.0.1"
port = 3726
max_threads = 4

[languages]
enabled = true
supported = ["c", "cpp", "java", "python_3"]  # 只启用需要的语言
temp_dir = "temp"
test_cases_dir = "test_cases"
```

### 语言支持详情

| 语言 | 编译命令 | 运行命令 | 文件扩展名 | 是否需要编译 |
|------|----------|----------|------------|--------------|
| C | `gcc {file} -o output.exe` | `./output.exe` | `.c` | 是 |
| C++ | `g++ {file} -o output.exe` | `./output.exe` | `.cpp` | 是 |
| Java | `javac {file}` | `java Main` | `.java` | 是 |
| JavaScript | 无 | `node {file}` | `.js` | 否 |
| Python 2 | 无 | `python2 {file}` | `.py` | 否 |
| Python 3 | 无 | `python3 {file}` | `.py` | 否 |
| Pascal | `fpc {file}` | `./code` | `.pas` | 是 |
| Common Lisp | 无 | `sbcl --script {file}` | `.lisp` | 否 |
| Plain Text | 无 | `cat {file}` | `.txt` | 否 |
| Brainfuck | 无 | `bf {file}` | `.bf` | 否 |
| R | 无 | `Rscript {file}` | `.r` | 否 |
| Rust | `rustc {file} -o output.exe` | `./output.exe` | `.rs` | 是 |
| Kotlin | `kotlinc {file} -include-runtime -d output.jar` | `java -jar output.jar` | `.kt` | 是 |

### 构建与运行

#### 前置要求

- **Rust 工具链**：需要安装 Rust 编译器和 Cargo 包管理器
- **系统依赖**：
  - 编译型语言：需要安装对应语言的编译器（如 gcc、g++、javac、rustc 等）
  - 解释型语言：需要安装对应语言的解释器（如 node、python2、python3、sbcl 等）

#### 构建步骤

```bash
# 进入评测机后端目录
cd judge-backend

# 构建项目
cargo build

# 运行评测机后端
cargo run
```

评测机后端会启动指定数量的工作线程（默认 4 个），并在 `127.0.0.1:3726` 端口监听连接请求。

### 与 EverJudge 主系统集成

1. **配置主系统**：在 `config.toml` 文件中设置评测机的 RPC 地址：

```toml
[judge]
rpc_url = "127.0.0.1:3726"
```

2. **启动顺序**：
   - 先启动 Rust 评测机后端：`cd judge-backend && cargo run`
   - 再启动 EverJudge 主系统：`python run.py`

3. **测试集成**：在 EverJudge 主系统中提交代码进行评测，观察评测机后端的日志输出，确认评测过程是否正常。

### 通信协议

评测机后端与 EverJudge 主系统之间使用 JSON 格式的消息进行通信：

#### 提交评测请求

```json
{
  "action": "submit",
  "submission_id": 1,
  "problem_id": 1,
  "code": "print('Hello, World!')",
  "language": "python 3",
  "time_limit": 1000,
  "memory_limit": 134217728
}
```

#### 提交评测响应

```json
{
  "status": "ok",
  "judge_id": "5f8a1b9c",
  "data": null,
  "error": null
}
```

#### 查询评测状态请求

```json
{
  "action": "status",
  "judge_id": "5f8a1b9c"
}
```

#### 查询评测状态响应

```json
{
  "status": "ok",
  "judge_id": null,
  "data": {
    "status": "ACCEPTED",
    "score": 100,
    "execution_time": 10,
    "memory_used": 2048,
    "error_message": null
  },
  "error": null
}
```

### 目录结构

```
judge-backend/
├── Cargo.toml          # Rust 项目配置
├── judge.toml          # 评测机配置
├── src/
│   ├── main.rs         # 入口文件
│   ├── server.rs       # TCP 服务器和通信协议
│   ├── judge.rs        # 评测池和任务管理
│   ├── languages.rs    # 语言处理和评测逻辑
│   ├── config.rs       # 配置加载
│   └── types.rs        # 评测相关的数据结构
└── target/             # 编译输出
```

### 故障排查

1. **端口占用**：如果评测机后端无法启动，可能是端口 `3726` 被占用。可以修改 `judge.toml` 文件中的端口配置。

2. **编译器/解释器缺失**：如果评测某些语言时失败，可能是缺少对应的编译器或解释器。请确保所有需要的编译器和解释器都已安装并添加到系统 PATH 中。

3. **权限问题**：评测机后端需要有创建临时文件和执行编译后的程序的权限。请确保运行评测机后端的用户有足够的权限。

4. **日志输出**：评测机后端会在控制台输出详细的日志信息，可以通过观察日志来排查问题。

5. **线程池配置**：如果评测性能不佳，可以调整 `judge.toml` 文件中的 `max_threads` 参数，根据服务器的 CPU 核心数设置合适的线程数。