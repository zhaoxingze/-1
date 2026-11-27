# 阶段 1 Flask 项目骨架实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** 在 Python 3.12.10 独立虚拟环境中交付可启动、可测试、含真实首页截图的 Flask 空骨架。

**Architecture:** 保留阶段 0 的 create_app、Blueprint、Service 和 ORM 分层。只注册业务模块边界，首页及 /health 由 dashboard 提供，认证、数据库表和 CRUD 不实现。

**Tech Stack:** Python 3.12.10、Flask、Flask-SQLAlchemy、Flask-Login、Flask-WTF、pytest、Jinja2、Bootstrap 5。

**Spec:** 当前用户阶段 1 指令，以及 [需求](../../specs/requirements.md)、[架构](../../specs/architecture.md)、[数据库](../../specs/database_design.md)、[假设](../../specs/assumptions.md)、[阶段 0 报告](../../specs/design_review_report.md)。用户已明确授权执行此阶段。

## Global Constraints

- 使用 `py -3.12 -m venv .venv`，实际 Python 必须为 3.12.10；所有应用安装、测试和启动均用 .venv。
- Word 移至 docs/specs/source/，迁移前后 SHA-256 一致；阶段 0 文档只改路径及迁移说明，不改业务设计。
- 不创建 11 张表、不写登录、不建演示账号、不实现业务 CRUD、不替用户解决 A-01 至 A-22。
- 当前不是 Git 仓库；按用户指定当前目录实施，不执行 git init、分支或提交。Git 专用任务脚本不适用，进度记录在本计划与阶段 1 报告。

## Review Focus

- 多次调用应用工厂：测试配置和扩展不可污染开发数据库；测试 app 使用内存 SQLite，检查创建和首页访问不落地业务数据库。
- 认证扩展初始化但没有 User 模型：首页和错误页不能因缺少 user_loader 而报错；暂不注册登录上下文处理器，不提供伪造 loader。
- 调用不支持的配置名：明确拒绝，不静默选择开发配置。
- CSRF 已启用：通过仅测试内存在的 POST 端点验证无 token 请求拒绝、有 token 请求通过；生产不加调试测试路由。
- 错误处理：403/404/500 保留 HTTP 状态和通用页面，不向用户显示内部异常；测试内注入异常端点，生产不暴露异常入口。

## Task 1 文档迁移与隔离环境

**Files:** 更新三个 Markdown 的原案链接及架构目录示意；新增 requirements.txt 与文档迁移证据。

**Interfaces:** 输出固定版本的五个直接依赖及传递依赖；后续任务只用 `.venv/Scripts/python.exe`。

- [x] 记录阶段 0 文件摘要；检查目标目录及文件，安全移动 Word 后复核 SHA-256，再清理空错拼目录。
- [x] 更新相对链接与迁移说明，保留审查报告原有历史结论。
- [x] 创建 3.12.10 venv，安装指定五依赖，运行 pip check、版本及解释器隔离检查；固定实际版本。

## Task 2 应用工厂与基础页面

**Files:** config.py、run.py、app/__init__.py、extensions.py、logging_config.py、errors.py；七模块包、models/services 包；layout、首页、三错误页、本地样式；tests/conftest.py、test_app.py。

**Interfaces:** `create_app(config_name="development", test_config=None) -> Flask`；development 使用 instance/student_management.db 的 URI，testing 使用 sqlite:///:memory:；GET / 返回 HTML，GET /health 返回 `{ "status": "ok", "service": "student-management-system" }`。

- [x] 先写测试，覆盖工厂、重复工厂隔离、七 Blueprint、两个正常入口、静态资源、403/404/500、CSRF 和不创建表或库文件；运行并记录缺少实现的失败。
- [x] 实现 Config、DevelopmentConfig、TestingConfig、工厂与未绑定扩展、基础控制台日志；不调用 create_all 或连接业务库。
- [x] 注册空业务 Blueprint；实现 dashboard 首页、健康接口和通用错误处理；测试路由只存在于 tests。
- [x] 使用本地 Bootstrap CSS 和自定义样式，首页只展示实际骨架状态及模块规划，无登录按钮或虚构统计数据。
- [x] 运行完整 pytest，修复至全部通过；再验证 pip check。

## Task 3 真实启动与交付

**Files:** README.md、.gitignore、instance/.gitkeep、docs/reports/stage1_report.md、docs/reports/stage1_*.json/txt、output/playwright/homepage.png。

**Interfaces:** PowerShell 启动命令 `.venv/Scripts/python.exe run.py`，默认仅监听 127.0.0.1:5000；浏览器访问真实运行服务器。

- [x] 启动应用，实际 GET 首页和健康接口；浏览器检查桌面及窄屏，生成首页截图。
- [x] 记录完整项目文件树（第三方环境目录只列根节点）、核心文件职责、安装启动命令、实际 pytest 结果和遗留项。
- [x] 最终独立代码审查，按严重性处理必要修复；跑最终受影响检查，不引入阶段 2 功能。
- [x] 复核 Word 哈希、Markdown 链接、阶段 0 数据库/UML未改及 instance 无业务数据库；停止本次临时开发服务器，等待阶段 2。

## 执行记录

预检：任务 2 消费任务 1 的隔离解释器；任务 3 消费任务 2 的 create_app 和路由；接口无冲突。阶段 0 文档中 Flask-WTF 为候选，当前用户明确指定其作为阶段 1 CSRF 扩展，属于技术集成选择，不改变业务待决项。

Task 1: complete — Word 迁移前后 SHA-256 相同；.venv 为 3.12.10，无系统 site-packages；19 项依赖固定，pip check 通过。

Task 2: complete — 先观察工厂测试失败，工厂实现后通过；补齐页面前全套失败已记录，页面实现后 19/19 通过。测试端点同名问题在测试代码中修正，未放宽 CSRF 或删除测试。

Task 3: complete — 真实 HTTP 200，桌面及窄屏截图完成，独立代码审查 19/19，通过文件保护与链接检查。无 Critical/Important；保留同进程 app.logger 级别共享这一 Minor 限制，详见阶段 1 报告。

Ruling: 非 Git 目录直接执行用户授权的当前项目任务，使用本计划和报告记录进度，不初始化 Git 或调用依赖提交历史的任务脚本；代价是本阶段没有 Git 提交历史，但原设计摘要已独立保全并核验。
