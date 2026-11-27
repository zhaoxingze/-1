# 阶段 8 全系统验收报告

验收日期 2026-11-19。阶段 8 完成 Windows 课堂部署、安全加固、SQLite 在线备份及独立恢复、全系统回归与源码交付。沿用阶段 7 已实现的业务模块和权限范围。

## 8A Windows 部署

| 验收项 | 实际结果 |
| --- | --- |
| 复现环境 | Windows 11 家庭版，64 位 Python 3.12.10，SQLite 3.49.1。新虚拟环境关闭系统包继承，实际安装 requirements.txt 的 22 个依赖 |
| 应用和依赖 | 原环境和新环境 pip check 通过。7 个 Blueprint 正常，Flask 路由检查列出 73 个端点规则，首页、健康、Bootstrap、CSS、品牌 SVG 响应 200 |
| 独立空库 | db upgrade 两次通过，db check 无差异。首轮角色新增 3 个，第二轮 0 个。create-admin 创建成功且重复拒绝，seed-demo 先新增 10 条虚构业务记录，再次执行新增 0 条 |
| 课堂启动 | 通过新环境直接执行 run.py，实测监听 127.0.0.1:5069。即使以 FLASK_DEBUG=1 启动，日志仍显示 Debug mode off，控制台路径返回 404。真实 HTTP 登录保留 HttpOnly 与 SameSite=Lax |

开发入口保留原模式。课堂模式使用独立默认实例、随机密钥和可配置回环端口。HTTPS 正式部署配置使用 Secure Cookie，需独立 WSGI 及 HTTPS 环境。[安装日志](stage8_fresh_install.txt) · [实际命令](stage8_deployment_commands.txt) · [初始化证据](stage8_fresh_deployment.json) · [部署指南](../deployment/windows_setup.md)

## 8B 安全、数据库与备份

完成对象授权、会话、密码、CSRF、回跳、输入边界、日志及审计审查。修复课堂调试入口缺口、响应安全头缺失、请求体与 SQL 参数披露边界、未知动作类型和 CLI 长度校验。历史跨班、跨课程及学生奖惩权限继续沿用现有决策。[安全审查与修复证据](stage8_security_review.md)

对开局开发库做只读完整性检查和前后哈希核验。开发库继续为 **13 张领域表、94 个字段、20 个 RESTRICT 外键、7 个触发器**，Alembic 版本 fab16ef0dd6f。开发库与独立新库的 integrity_check 均为 ok，foreign_key_check 为 0 条。新库检查了唯一、CHECK 和主要家长部分唯一索引，应用连接的外键及递归触发器已启用。原开发库及迁移、模型保持原 SHA-256。[开发库验证](stage8_database_and_preservation.json) · [迁移核验](stage8_development_db_check.txt)

在课堂服务运行期间调用 SQLite Backup API 创建文件，随后恢复到另一个实例。备份和恢复文件各 **245,760 字节**，快照 SHA-256 一致。对比全部领域表数据，4 个账号、2 名学生、2 门课程、3 条选课、5 条考勤及 47 条审计等全部行相同。恢复实例在 127.0.0.1:5070 启动，三种角色登录、权限限制与关键记录读取通过。源课堂数据库哈希一致。[备份与恢复证据](stage8_backup_restore.json) · [操作手册](../deployment/backup_restore.md)

## 8C 实际系统验收

在 Edge 与本地 Flask 上运行 **63 条浏览器断言**，用 14 张真实截图记录桌面和 390 × 844 移动视口。流程涵盖账号与档案维护、角色重新绑定与启停、本人改密、审计、课程与两学期成绩、考勤和奖惩、家长联系与模拟短信及邮件。工作台使用真实数据库。实测总评分从 87.00 调整到 90.00，历史学期保持 47.00，四种考勤样本的出勤率为 66.67%。浏览器无未处理错误、CSP 问题或外部 HTTP 请求。宽表格在容器内滚动。[断言与数据库复核](stage8_browser.json)

| 功能 | 截图 |
| --- | --- |
| 管理员统计、账号及审计 | [管理员工作台](../screenshots/stage8-admin-dashboard.png) · [账号详情](../screenshots/stage8-account-detail.png) · [实体审计历史](../screenshots/stage8-audit-history.png) |
| 档案查询 | [学生搜索](../screenshots/stage8-students-search.png) |
| 教师统计及教务 | [教师工作台](../screenshots/stage8-teacher-dashboard.png) · [当前学期成绩](../screenshots/stage8-teacher-grades.png) · [出勤统计](../screenshots/stage8-teacher-attendance.png) |
| 奖惩及家校沟通 | [奖惩](../screenshots/stage8-teacher-rewards.png) · [联系历史](../screenshots/stage8-teacher-contacts.png) · [模拟邮件](../screenshots/stage8-teacher-notification.png) |
| 学生范围及移动端 | [学生工作台](../screenshots/stage8-student-dashboard.png) · [越权拒绝](../screenshots/stage8-permission-denied.png) · [移动端表单](../screenshots/stage8-mobile-form.png) · [移动端成绩表](../screenshots/stage8-mobile-student-grades.png) |

## 实际测试结果

| 执行 | 结果 |
| --- | --- |
| 阶段 7 全量基线 | 507 项通过，386.87 秒 |
| 阶段 8 新增定向测试 | 27 项通过，9.11 秒 |
| 阶段 8 新环境全量 | **534 项通过**，227.14 秒，含原 507 项和新 27 项 |
| 语法、路由和图 | compileall 通过，73 个路由规则，七份 PlantUML 源文件语法通过并渲染 26 个图块 |

实施前的预期失败覆盖缺少课堂配置、备份工具及响应头。修复后 27 个定向用例全部通过。一次全量任务在会话中断时只完成部分用例，重新用相同新虚拟环境执行，以上 534 为完整结果。初次失败日志仅归一化本机临时路径，可追溯原诊断。[阶段 7 基线](stage8_baseline_pytest.txt) · [实现前证据](stage8_red.txt) · [中断记录](stage8_pytest_interrupted.txt) · [最终 pytest](stage8_pytest.txt) · [编译检查](stage8_compileall.txt) · [UML](stage8_uml_syntax.txt) · [渲染](stage8_uml_render.txt)

## 新增和修改

- `config.py`、`run.py`、`app/__init__.py` 增加独立课堂模式与本机运行入口。
- `app/auth/session.py`、`app/services/permission_service.py`、`app/cli.py` 增加安全头、动作类型及 CLI 校验。联系详情的内联样式已迁至本地 CSS。
- `scripts/sqlite_snapshot.py` 提供在线备份、恢复及校验命令。五个阶段 8 测试模块覆盖部署、配置、备份、安全和跨模块流程。
- 更新 README、需求、架构、数据库及假设。校正 UML 账号活动图中的密码哈希和写锁顺序，已有实体、关系及迁移沿用。
- 工作目录无 Git 元数据。对 399 项起始文件进行 SHA-256 核验，384 项保持一致，另 15 项是预期编辑。原 56 个测试及辅助文件均完整保留。

## 遗留风险与阶段 9

课堂部署、安全与恢复达到阶段 9 课程设计交付的工程条件。正式 HTTPS 的证书及反向代理、登录限流、集中会话撤销和敏感备份保管需结合部署环境处理。历史任教、转班与学生奖惩查阅规则保持待决。

源码 ZIP 含代码、依赖、迁移、测试、脚本、设计与部署文档、报告和真实截图。另附交付文件清单和哈希验证证据，排除虚拟环境、缓存、密钥、私有数据库与真实个人数据。阶段 9 留待单独指令。[验收矩阵](stage8_test_matrix.md) · [验收清单](stage8_acceptance_checklist.md)
