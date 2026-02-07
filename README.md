# EverJudge

基于 Python3 / Flask / SQLAlchemy / WTForms + HTML5 / jQuery / Tailwind 的 OJ 系统，评测机后端使用 Rust 实现。配置统一使用 TOML，部署使用 uWSGI，支持多数据库与 i18n。

## 功能模块（分步实现）

- **Phase 1** ✅ 项目结构、TOML 配置、Flask 骨架、多数据库支持
- **Phase 2** ✅ 账户系统（注册/登录/权限、WTForms、管理员 CLI）
- **Phase 3** ✅ 题面管理、测试数据、评测系统集成
- **Phase 4** Rust 评测机后端
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
└── judge/               # Rust 评测机（Phase 4）
```
