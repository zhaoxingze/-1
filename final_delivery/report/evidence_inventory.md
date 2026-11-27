# 阶段 9 证据清单

核对日期 2026-11-19。依据实际源码、阶段 0–8 原始记录和本次导出材料。阶段 8 的测试和截图为隔离环境实际结果。

| 报告主题 | 设计与源码 | 运行和验收 |
| --- | --- | --- |
| 背景、边界与需求 | [原案](../source/学生管理系统源码/docs/specs/source/学生管理系统_前期设计方案与Codex分阶段提示词.docx)、[需求与权限矩阵](../source/学生管理系统源码/docs/specs/requirements.md)、[假设](../source/学生管理系统源码/docs/specs/assumptions.md) | [阶段 0 审查](../source/学生管理系统源码/docs/specs/design_review_report.md) |
| B/S 分层、Blueprint 与数据库 | [架构](../source/学生管理系统源码/docs/specs/architecture.md)、[数据库字段字典](../source/学生管理系统源码/docs/specs/database_design.md)、[应用工厂](../source/学生管理系统源码/app/__init__.py)、[迁移](../source/学生管理系统源码/migrations) | [新库迁移](../testing/stage8_fresh_deployment.json)、[开发库结构](../testing/stage8_database_and_preservation.json) |
| 认证、三角色与范围 | [身份会话](../source/学生管理系统源码/app/auth/session.py)、[授权](../source/学生管理系统源码/app/services/permission_service.py)、[阶段 3 决策](../source/学生管理系统源码/docs/specs/stage3_auth_rbac_design.md)、[阶段 4B 决策](../source/学生管理系统源码/docs/specs/stage4b_permissions.md) | [学生越权拒绝](../screenshots/stage8-permission-denied.png)、[测试矩阵](../testing/stage8_test_matrix.md) |
| 基础档案与学籍 | [阶段 4A 设计](../source/学生管理系统源码/docs/specs/stage4a_design.md)、[学生服务](../source/学生管理系统源码/app/services/student_service.py)、[档案路由](../source/学生管理系统源码/app/admin) | [学生搜索](../screenshots/stage8-students-search.png)、[断言](../testing/stage8_browser.json) |
| 教务与成绩 30/70 | [阶段 5 决策](../source/学生管理系统源码/docs/specs/stage5_decisions.md)、[教务路由](../source/学生管理系统源码/app/academics)、[成绩服务](../source/学生管理系统源码/app/services/grade_service.py) | [教师成绩](../screenshots/stage8-teacher-grades.png)、[手机端学生成绩](../screenshots/stage8-mobile-student-grades.png)、[阶段 8 实测值](../testing/stage8_report.md) |
| 考勤与出勤率 | [阶段 6 决策](../source/学生管理系统源码/docs/specs/stage6_decisions.md)、[考勤服务](../source/学生管理系统源码/app/services/attendance_service.py) | [考勤统计](../screenshots/stage8-teacher-attendance.png)、[手机登记](../screenshots/stage8-mobile-form.png) |
| 奖惩、联系与模拟通知 | [成长记录路由](../source/学生管理系统源码/app/records)、[联系服务](../source/学生管理系统源码/app/services/parent_contact_service.py)、[通知服务](../source/学生管理系统源码/app/services/notification_service.py) | [奖惩](../screenshots/stage8-teacher-rewards.png)、[联系](../screenshots/stage8-teacher-contacts.png)、[模拟邮件](../screenshots/stage8-teacher-notification.png) |
| 账号、审计与角色工作台 | [阶段 7 决策](../source/学生管理系统源码/docs/specs/stage7_decisions.md)、[账号服务](../source/学生管理系统源码/app/services/user_management_service.py)、[审计查询](../source/学生管理系统源码/app/services/audit_query_service.py)、[统计服务](../source/学生管理系统源码/app/services/dashboard_statistics_service.py) | [账号详情](../screenshots/stage8-account-detail.png)、[审计历史](../screenshots/stage8-audit-history.png)、[管理员](../screenshots/stage8-admin-dashboard.png)、[教师](../screenshots/stage8-teacher-dashboard.png)、[学生](../screenshots/stage8-student-dashboard.png) |
| 534 项自动化、63 项浏览器、14 张阶段 8 截图 | [全部测试](../source/学生管理系统源码/tests) | [pytest 日志](../testing/stage8_pytest.txt)、[浏览器布尔断言](../testing/stage8_browser.json)、[阶段 8 报告和截图索引](../testing/stage8_report.md) |
| Windows 课堂启动、备份及安全 | [启动入口](../source/学生管理系统源码/run.py)、[部署](../deployment/windows_setup.md)、[快照脚本](../source/学生管理系统源码/scripts/sqlite_snapshot.py)、[恢复指南](../deployment/backup_restore.md) | [依赖安装](../testing/stage8_fresh_install.txt)、[迁移命令](../testing/stage8_deployment_commands.txt)、[独立恢复](../testing/stage8_backup_restore.json)、[安全审查](../testing/stage8_security_review.md) |
| 七份 UML、26 图块 | [UML 目录与源文件](../source/学生管理系统源码/docs/uml/README.md) | [阶段 8 原始检验](../testing/stage8_uml_syntax.txt)及阶段 9 重新导出 |

## 一致性校准

- A-05 登记行保留了教师只读的早期待决说明。阶段 4B 的教师端与权限服务已经开放班主任对本人在管班级学生的电话、住址限字段编辑，按现行权限更新登记行。
- A-07 登记行仍写归档和学籍办理未实现。阶段 4A 已完成两者。归档、学籍与账号停用相互独立，登记行改为现行描述。
- 用例图中 UC-08 与 UC-15 的教师连线容易让任课教师和班主任范围混淆。图中补明当前班主任限制。学籍图中历时性的“留 4B”校准为仍按 A-20 待决。原验收日志保留，Flask 业务源码沿用。
