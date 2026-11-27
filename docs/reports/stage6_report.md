# 阶段 6 验收报告

验收日期 2026-11-19，使用项目虚拟环境 Python 3.12.10。新增考勤、奖惩、家长联系和模拟通知，沿用现有 Flask、SQLAlchemy、SQLite 和 Bootstrap。

## 已实现功能

| 模块 | 实际实现 |
| --- | --- |
| 考勤 | 依学生、当前班级和日期范围分页查询，登记、详情、编辑及统计。学生可查询和统计本人考勤 |
| 奖励与处分 | 新增、详情、编辑与分类查询，支持学生、类型、类别和日期筛选 |
| 家长联系 | 新建及编辑联系内容、结果、方式和时间。按学生、家长和日期过滤历史。创建时保存当时的联系人姓名和电话 |
| 模拟通知 | 显式创建模拟短信和邮件，查询历史及收件快照。页面显示“模拟通知，未实际发送” |

## 业务规则

- **A-03** 统计实际登记的出勤、迟到、缺勤、请假。出勤率为（出勤＋迟到）÷（出勤＋迟到＋缺勤）×100%，显示两位小数。请假单列，分母为零时显示“无可统计数据”。节次使用原字符串字段，非空且最长 30 字符。
- **A-04** 管理员全局，班主任限学生当前所属的本班。任课关系单独判断，只有任课关系的教师无法进入阶段 6 管理页面。学生仅可读取本人的考勤和统计。
- **A-12** 奖惩对学生默认拒绝。家长联系和模拟通知也属于管理员及班主任业务。
- **A-09** 显式操作复用 `create_simulated_notification()`，写入本地 `simulated` 状态、渠道和接收对象快照。普通联系保存独立。可选已有家长，或填写临时收件人和对应渠道的地址。

考勤编辑时登记人为当前操作者，奖惩与联系编辑保留初始创建人。联系编辑保留学生、家长关联和原联系快照。联系时间与通知时间以 UTC 展示，日期筛选包含起止日。[完整规则和权限矩阵](../specs/stage6_decisions.md)

## 主要代码和设计文件

| 路径 | 修改 |
| --- | --- |
| `app/attendance/` | 新建路由、登记及编辑表单、考勤统计页面入口 |
| `app/records/` | 新建奖惩、联系和通知路由与表单 |
| `app/services/attendance_service.py`、`reward_service.py`、`parent_contact_service.py` | 业务查询、校验、统计、写入、快照与模拟 |
| `app/services/student_record_service.py`、`permission_service.py` | 学生范围、写锁、日期过滤、审计及八项显式权限动作 |
| `app/record_views.py`、`app/templates/records/`、`app/templates/attendance/` | 通用分页和筛选、详情、统计模板，复用原表单组件 |
| `app/admin/`、`app/dashboard/`、`app/templates/layout.html` | 授权入口及阶段标记。共用严格表单字段检查供阶段 5 和 6 使用 |
| `tests/` | 八个测试模块及独立临时 SQLite 数据辅助 |
| `README.md`、`docs/specs/`、`docs/uml/` | 更新需求、架构、假设、角色入口及 UML |

## 测试、权限和事务

| 验收项 | 实际结果 |
| --- | --- |
| 阶段 5 基线 | 409 项通过，137.98 秒 |
| 阶段 6 全量 pytest | **463 项通过**，保留原有 409 项并新增 **54 项**，178.66 秒 |
| 越权拒绝 | 匿名访问跳转登录。教师跨班查询、统计及写入返回 403。仅任课教师无法获得本班权限。学生无法写考勤或读取其他学生考勤、奖惩、家长联系和模拟通知 |
| 请求数据验证 | 学生、家长、班级和记录 ID 由服务核验。伪造操作者、提交未允许字段或缺少 CSRF 均被拒绝。班级变更后，旧页面及 ORM 缓存无法维持原班主任授权 |
| 统计与分页 | 先施加 SQL 授权范围，再查询、统计或分页。请假单列，空记录和仅请假均显示无可统计数据 |
| 审计 | 八种写操作追加 AuditLog，记录真实操作者、对象 ID、操作、业务元数据前后值和 UTC 时间。备注、事由、联系正文、电话、邮箱和收件快照等保留在授权业务表 |
| 回滚 | 临时 SQLite 触发器拒绝审计插入时，考勤、奖惩、联系和通知的新增整体回滚，考勤编辑保留原值 |

实现前的五项定向测试确认入口及统计服务尚未实现。初次定向复测 49 项通过、1 项失败。考勤结果已按班级过滤，但管理员的学生下拉范围仍为全校。修复时将下拉选项与已选班级对齐，并使用 WTForms 的 SelectChoice 处理选项弃用警告。随后全量 463 项通过。[基线](stage6_baseline_pytest.txt) · [初次定向测试](stage6_targeted_initial.txt) · [全量 pytest](stage6_pytest.txt)

## 数据库检查

- `pip check` 无依赖冲突。Flask 临时库按原迁移启动，开发库 `flask --app run db check` 无新迁移操作。[依赖检查](stage6_pip_check.txt) · [迁移检查](stage6_migration_check.txt)
- 开发库为 **13 张领域表、94 个字段、20 个 RESTRICT 外键、7 个触发器**，Alembic 版本 `fab16ef0dd6f`。考勤三元组唯一约束存在，`integrity_check` 为 `ok`，`foreign_key_check` 为 0 条。
- 核对阶段 5 清单和本地数据库共 305 项，286 项字节一致，19 个文件是预期更新。原 40 个测试及辅助文件、ORM 模型、迁移和开发库 SHA-256 均一致。[数据库及文件校验](stage6_database_and_preservation.json)

## 浏览器和移动端

以 Edge 连接本机 Flask 和独立临时 SQLite，使用虚构数据执行 33 条断言。实际登记并编辑考勤，按班级与日期得到 66.67%，验证奖惩及联系编辑、两种模拟通知和三个角色的越权拒绝。另以仅任课的教师账号验证页面入口和直接路由均受限制。复核临时库中 11 条浏览器业务审计。390 × 844 像素视口下登记表单可见、可操作，页面无横向溢出。[浏览器结果](stage6_browser.json)

| 操作 | 截图 |
| --- | --- |
| 管理员登记及重复校验 | [考勤详情](../../output/playwright/stage6-admin-attendance-detail.png) · [重复提示](../../output/playwright/stage6-attendance-duplicate.png) |
| 教师统计及筛选奖惩 | [考勤统计 66.67%](../../output/playwright/stage6-teacher-attendance-statistics.png) · [奖惩列表](../../output/playwright/stage6-teacher-rewards.png) |
| 家长联系及模拟通知 | [联系详情](../../output/playwright/stage6-teacher-contact-detail.png) · [模拟邮件详情](../../output/playwright/stage6-teacher-simulated-email.png) · [通知历史](../../output/playwright/stage6-teacher-notification-history.png) |
| 学生本人查询和拒绝 | [本人考勤](../../output/playwright/stage6-student-attendance.png) · [越权拒绝](../../output/playwright/stage6-student-forbidden.png) |
| 移动端 | [390 像素登记表单](../../output/playwright/stage6-attendance-mobile.png) |

## UML 与衔接

用例图明确本班授权、学生本人考勤及独立模拟用例。类图增加 StudentRecordScope 和服务模块。顺序图与通信图覆盖锁内授权、考勤登记、奖惩、联系、模拟通知与回滚。活动图记录考勤四状态汇总、零分母和记录类型分支。7 份 PlantUML 源文件通过语法检查，21 个图块已渲染。[UML 索引](../uml/README.md) · [语法检查](stage6_uml_syntax.txt) · [渲染清单](stage6_uml_render.txt)

阶段 6 已满足进入阶段 7 的工程条件。阶段 7 的首页聚合需确认 A-15 的“近期”窗口、统计对象和范围口径。学生奖惩可见性及跨班历史授权继续待决。完整源码 ZIP 包含代码、迁移、依赖、测试、文档和截图，附文件清单、校验记录和解包测试。阶段 7 留待单独指令。
