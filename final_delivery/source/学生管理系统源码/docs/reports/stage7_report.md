# 阶段 7 验收报告

验收日期 2026-11-19，使用项目虚拟环境 Python 3.12.10。阶段 7 按 7A、7B、7C 顺序开发与定向验收。

## 7A 管理员账号与审计

- 账号列表支持用户名、角色、启停筛选及分页。可创建三类账号，查看和编辑用户名、角色和档案绑定，确认启停，跳转既有密码重置。
- 账号仅使用固定的 admin、teacher、student 字典。教师和学生绑定真实且未被占用的对应档案，管理员保留空档案绑定。停用保留历史记录和档案绑定，账号状态与学籍及归档独立。
- SQLite 写事务锁内复核操作者与目标，保护管理员自身及最后一个可用管理员。账号变动与审计统一提交。启停使用 status_change，编辑角色和绑定使用 update，审计插入失败则回滚。
- 登录会话沿用凭据 HMAC，加入最近身份或状态变更的审计 ID。复测角色与绑定改回及重新启用后，原会话仍失效。现有密码修改和重置继续通过回归。
- 审计仅管理员只读查询，支持操作者、实体类型、实体 ID、操作类型及包含起止日的 UTC 日期筛选。详情依次使用现有快照清理与实体字段白名单，历史凭证、联系人资料、通知快照、正文及敏感成绩值均不展示。

[阶段 7 决策](../specs/stage7_decisions.md) · [7A 测试日志](stage7a_pytest.txt)

## 7B 三角色工作台

| 角色 | 实施口径 | 浏览器实测示例 |
| --- | --- | --- |
| 管理员 | 全部学生计入总数，在读限 enrolled 且未归档，已归档单计。教师、班级、课程为当前表总量，支持选成绩学期及考勤班级 | 学生总数 3，在读 1，归档 1。当前两门课平均 90.00、20.00，历史学期 42.00 及暂无数据 |
| 教师 | 按当前班主任关系汇总学生和考勤，按当前授课关系汇总课程及配置学期成绩 | 本班考勤 100.00%，本人授课课程 90.00。所授课程中的外班学生可计入成绩，范围外班级统计被拒绝 |
| 学生 | 本人摘要、配置学期选课数、完整成绩数及均分，本人近期考勤 | 本人选课 1，完整成绩课程 1，均分 84.00。查询他人或管理端被拒绝 |

最近 30 个 UTC 自然日包含当日及前 29 天。只汇总已有考勤，迟到计入出勤率分子，请假单列。分母为零显示“无可统计数据”。均分只纳入平时、考试和总评分均有值的选课，按学期分别计算。SQL 先限定权限范围再聚合。浏览器示例来自独立临时库。[7B 测试日志](stage7b_pytest.txt)

## 7C 界面与导航

三角色共用按权限生成的侧栏及工作台快捷入口。统一页头、面包屑、空状态与表单错误提示，移动端支持展开功能菜单及表格容器内横向滚动。沿用本地 Bootstrap、Jinja2、CSRF 及原有业务入口。[7C 测试日志](stage7c_pytest.txt)

## 主要代码变动

| 位置 | 职责 |
| --- | --- |
| app/admin/user_routes.py、user_forms.py、app/templates/admin/user_* | 管理员账号读写、创建、编辑、启停确认和详情 |
| app/services/user_management_service.py、app/auth/session.py、permission_service.py | 账号校验、写锁、并发保护和旧会话失效 |
| app/admin/audit_routes.py、app/services/audit_query_service.py、app/templates/admin/audit_* | 分页审计查询和安全展示 |
| app/services/dashboard_statistics_service.py、attendance_service.py | 三角色 SQL 统计与共用考勤率 |
| app/dashboard/、app/templates/layout.html、app/static/css/app.css | 统计页面、共用导航、响应式布局 |
| tests/test_stage7_*.py、tests/stage7_support.py | 六个新测试模块及临时数据库辅助 |
| README.md、docs/specs/、docs/uml/ | 业务规则、权限矩阵、入口和 UML |

## 测试与数据完整性

| 验收 | 实际结果 |
| --- | --- |
| 阶段 6 全量基线 | 463 项通过，328.64 秒 |
| 7A 独立定向及密码会话回归 | 68 项通过，56.21 秒 |
| 7B 独立定向及统计权限回归 | 26 项通过，22.45 秒 |
| 7C 独立定向及路由回归 | 56 项通过，31.20 秒 |
| 阶段 7 全量 pytest | **507 项通过**，含原有 463 项和新增 **44 项**，368.84 秒 |
| 账号安全 | 非管理员、伪造角色 ID、CSRF 缺失、重名、错绑、重复绑定及自身停用均被拒绝。并发停用后仍有一名可用管理员 |
| 审计 | 业务与审计同事务。触发模拟审计失败后，账号修改整体回滚。历史审计详情经过清理及白名单过滤 |
| 统计准确性 | 核对日期边界、请假排除、完整成绩、学期隔离、授权范围及空数据 |
| 依赖及迁移 | pip check 无冲突。开发库 Flask-Migrate 检查无新操作，临时演示库从原迁移建立 |

开发数据库保持 **13 张领域表、94 个字段、20 个 RESTRICT 外键、7 个触发器**，Alembic 版本 fab16ef0dd6f。SQLite integrity_check 为 ok，foreign_key_check 为 0 条结果。核对阶段 6 清单及数据库共 351 项，328 项一致，23 项为预期更新。原 49 个测试与辅助文件、模型、迁移及开发库 SHA-256 一致。[基线](stage7_baseline_pytest.txt) · [全量结果](stage7_pytest.txt) · [数据库核验](stage7_database_and_preservation.json) · [依赖](stage7_pip_check.txt) · [迁移](stage7_migration_check.txt)

各子阶段先记录功能尚未接入时的预期失败，再实施并复测。[7A 实现前](stage7a_red.txt) · [7B 实现前](stage7b_red.txt) · [7C 实现前](stage7c_red.txt)

## 浏览器与移动端

使用 Edge 连接本机 Flask 和独立临时 SQLite，27 条浏览器断言通过。实际创建了教师账号，改为学生并绑定档案，执行停用及启用，验证两次会话失效、筛选和安全审计。临时库实查四条审计记录、目标账号状态和 Werkzeug 哈希。390 × 844 像素视口下功能菜单可展开，宽表格在容器内滚动，学生工作台无页面横向溢出。[浏览器诊断与断言](stage7_browser.json)

| 功能 | 实际截图 |
| --- | --- |
| 管理员统计 | [默认统计](../../output/playwright/stage7-admin-dashboard.png) · [学期及班级筛选](../../output/playwright/stage7-admin-filters.png) |
| 账号管理 | [账号详情](../../output/playwright/stage7-admin-account-detail.png) · [账号筛选](../../output/playwright/stage7-admin-user-list.png) · [重名提示](../../output/playwright/stage7-admin-duplicate.png) |
| 审计 | [查询列表](../../output/playwright/stage7-admin-audit-list.png) · [脱敏详情](../../output/playwright/stage7-admin-audit-detail.png) |
| 教师与学生 | [教师工作台](../../output/playwright/stage7-teacher-dashboard.png) · [学生工作台](../../output/playwright/stage7-student-dashboard.png) |
| 移动端 | [折叠菜单](../../output/playwright/stage7-mobile-navigation.png) · [账号列表](../../output/playwright/stage7-mobile-users.png) · [学生工作台](../../output/playwright/stage7-mobile-student.png) |

## UML 与阶段 8

用例图补充账号、审计及三角色统计，类图增加用户管理、审计查询与统计服务。顺序图覆盖用户写入与脱敏审计，通信图说明 SQL 范围及聚合，活动图记录账号事务、会话失效、统计及错误分支。7 份 PlantUML 源文件通过检查并渲染 26 个图块。ER 图和持久化字段沿用原设计。[UML 索引](../uml/README.md) · [语法](stage7_uml_syntax.txt) · [渲染](stage7_uml_render.txt)

阶段 7 满足阶段 8 的工程前置条件。全新环境安装、部署参数、备份恢复和验收演示由阶段 8 执行。历史任教与转班授权、对学生开放奖惩的规则留待明确。全源码 ZIP 包含代码、依赖、迁移、测试、文档与截图，附文件清单、哈希和解包测试结果。阶段 8 留待单独指令。

