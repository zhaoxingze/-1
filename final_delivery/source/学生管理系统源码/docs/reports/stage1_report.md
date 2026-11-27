# 学生综合信息管理系统阶段 1 完成报告

日期：2026-11-16。范围：原件安全迁移、Python 3.12.10 隔离环境、Flask 骨架及真实运行验收。业务模型、账号、认证业务和 CRUD 未进入本阶段。

## 1 已完成的功能与证据

| 项目 | 实际结果 | 证据 |
| --- | --- | --- |
| Word 安全迁移 | 已移至 docs/specs/source/，前后 SHA-256 相同；原空目录已清理 | [迁移记录](stage1_source_migration.json) |
| 独立 Python 环境 | Python 3.12.10；sys.prefix 指向项目 .venv，禁用系统 site-packages；五个直接依赖均从 .venv 导入 | [环境记录](stage1_environment.json) |
| 依赖版本 | 5 个直接依赖及传递依赖共 19 项固定到实际版本 | [requirements.txt](../../requirements.txt)、[pip check](stage1_pip_check.txt) |
| 应用工厂和模块 | create_app、7 Blueprint、3 扩展、开发与测试配置、控制台日志 | [入口与职责](../../README.md) |
| 首页及 /health | 真实服务器两接口均 HTTP 200；健康响应 status=ok | [HTTP 记录](stage1_http_smoke.json) |
| 统一错误处理 | 403/404/500 均经 test_client 验证状态及内容；500 不暴露内部异常 | [pytest 记录](stage1_pytest.txt) |
| CSRF | 无 token 的测试写请求返回 400，有有效 token 的同类请求通过 | 同上；测试路由不注册到实际应用 |
| 配置隔离及范围 | 测试用内存 SQLite；开发库文件未创建；无业务表和业务路由 | 同上及 HTTP 记录 |
| 页面截图 | 实际启动服务后以 Chrome 检查并截图 | [桌面首页](../../output/playwright/homepage.png)、[窄屏首页](../../output/playwright/homepage-mobile.png) |

## 2 原件及设计资料保护

Word 原路径：`docs/sepecs/学生管理系统_前期设计方案与Codex分阶段提示词.docx`。

新路径：[docs/specs/source/学生管理系统_前期设计方案与Codex分阶段提示词.docx](../specs/source/学生管理系统_前期设计方案与Codex分阶段提示词.docx)。迁移前后 SHA-256 均为：

```text
D4520374DAC8021CD2D7CDBF098C17C7C48BCCB76616A2C82EF587BD0C033C58
```

先核实绝对源路径、目标不存在和源摘要，再移动原文件；复核摘要后，仅删除已确认空的错拼目录。阶段 0 的 requirements、assumptions、architecture、design_review_report 只更新来源链接、目录示意和迁移说明，保留历史结论；database_design 和全部 UML 源文件不改。22 项业务假设没有被本阶段代码确定。具体摘要和链接检查以最终验收记录为准。

## 3 安装与运行命令

完整命令和核心文件职责见 [README](../../README.md)。所有 Python 命令明确使用项目虚拟环境：

```powershell
Set-Location 'F:\StudentManagementSystem'
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe run.py
```

本次最初在新建 venv 中安装 Flask、Flask-SQLAlchemy、Flask-Login、Flask-WTF 和 pytest；通过导入、pip check 及 19 个测试后生成固定版本 requirements.txt。Python 解释器版本 3.12.10，不是机器全局 python 的 3.13.9。

## 4 测试经过及实际结果

先写工厂契约测试，得到预期的 `1 failed`（无 app 包），见 [初始失败记录](stage1_pytest_red.txt)。工厂实现后单测通过；页面和资源完成前全套为 `11 failed, 8 passed`，见 [页面实现前记录](stage1_pytest_before_pages.txt)。其中一项失败来自测试自身两个匿名 view 使用同一默认 endpoint，已给测试端点显式命名，不修改生产路由、不删除测试。其余失败由尚未编写的页面和资源引起。

页面和资源补齐后，完整命令 `.venv/Scripts/python.exe -m pytest -q` 最终实际结果为 **19 passed in 0.66s**。这 19 个测试只验收阶段 1；原案业务 TC-01 至 TC-12 仍为待执行。

开发 URI 指向 instance/student_management.db，但没有创建此文件。测试对内存 SQLite 检查空表集合，无任何 11 表模型定义，也没有 create_all、演示数据或初始化账号命令。

## 5 技术选择及遗留边界

- 当前用户已指定 Python 3.12.10 和 Flask-WTF；本阶段落实解释器及 CSRF 扩展集成，不改变业务待决项。
- Flask-Login 暂不安装 current_user 模板上下文处理器，无 User 模型、user_loader 或登录路由。后续真实认证实现时再接入加载器和上下文。
- 开发 SECRET_KEY 来自环境；缺失时生成临时随机值。测试密钥独立。未决定密码复杂度、重置会话政策等 A-18 业务项。
- 日志输出到控制台，含时间、级别、应用名；500 原始异常留在服务端日志，页面只返回通用提示。未增加持久审计方案，不视为已解决 A-08。
- /health 是进程响应检查，不查询数据库，不声称数据库或业务就绪。
- 首页六模块是说明卡片，没有假登录、假统计、无效业务按钮，也没有公开用来触发 403/500 的调试接口。
- 当前不是 Git 仓库；按用户要求在当前目录工作，没有 git init、提交或工作树。项目已提供 .gitignore。
- 下一阶段模型实现前仍需按假设登记处理归档、审计、通知、非空约束、历史关系等问题；本阶段不自动进入阶段 2。

## 6 浏览器及最终审查

实际 Chrome 桌面视口 1440×1000、窄屏视口 390×844 检查首页；两种视口的文档宽度均等于视口宽度，无横向溢出，控制台均为 0 errors、0 warnings，见 [浏览器检查日志](stage1_browser.txt)。桌面截图 1440×1000，手机整页截图 390×1712，均已实际查看。

独立代码审查复跑测试得到 `19 passed in 0.73s`，未发现 Critical 或 Important 问题，结论为阶段 1 可交付。发现一项非阻断限制：同进程创建多个 Flask 应用时使用同名 app.logger，后创建的 testing 应用会把已有 development logger 的有效级别从 INFO 改为 WARNING；不影响数据库隔离、ERROR 日志或本次独立运行服务器，后续明确统一进程日志配置或按应用实例隔离。目前保留该 Minor 限制，不扩大阶段 1 的日志架构。

审查不对后续业务模型、认证/RBAC、CRUD、演示账号、A-01 至 A-22 决策或生产部署作验收；这些分别属于用户明确禁止的后续范围或当前本机开发服务之外。DEBUG 调试器及第三方 Bootstrap 内部实现不视为本次自有业务缺陷。原件保护、截图和停机由主代理另行验证。

[最终文件核验记录](stage1_final_validation.json) 对 14 个阶段 0 文件逐一检查：Word、数据库设计及全部 UML 文件共 10 项摘要不变；其余 4 个 Markdown 通过反向还原本次授权的路径和迁移文字后，与原摘要完全一致。最终文档链接和 instance 内容同样由该记录给出。

## 7 项目文件树

完整项目自有文件清单见 [stage1_project_tree.txt](stage1_project_tree.txt)。该树列出全部源码、设计文件、报告和截图；.venv 只列目录根，自动生成的 __pycache__、.pytest_cache 和浏览器会话缓存不展开，避免将第三方依赖数千个文件误作项目源码。

## 8 阶段结论

阶段 1 的功能验收已实际通过：19 个 pytest 测试、pip check、真实 HTTP 运行及桌面/窄屏页面检查。依赖、命令、完整文件树、核心文件职责和截图均已交付；上文日志级别共享为已记录的非阻断限制，业务待决事项保持原状态。验收后关闭本次浏览器会话并停止临时开发服务器，用户可按 README 命令重新启动。交付后停止，等待阶段 2 指令。
