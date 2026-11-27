# 阶段 8 测试矩阵

测试使用独立临时 SQLite。浏览器用已初始化的课堂实例及虚构数据，部署与恢复证据均由实际命令生成。

| 编号 | 验收场景 | 自动化和实测证据 | 结果 |
| --- | --- | --- | --- |
| DEP-01 | Windows 11、Python 3.12.10 新环境安装、pip check、Flask 导入 | [安装](stage8_fresh_install.txt)、[依赖](stage8_fresh_pip_check.txt)、[路由](stage8_routes.txt) | 通过 |
| DEP-02 | 空库迁移及重跑、角色初始化、管理员重复拒绝、演示数据幂等 | [部署命令](stage8_deployment_commands.txt)、[迁移结构](stage8_fresh_deployment.json)、test_stage8_deployment.py | 通过 |
| DEP-03 | 回环监听、端口校验、关闭调试器、随机密钥、本地静态资源 | [运行证据](stage8_backup_restore.json)、test_stage8_configuration.py | 通过 |
| SEC-01 | 登录失败、改密、密码重置与会话版本、退出、过期 | test_auth_login.py、test_auth_passwords.py、test_auth_logout.py、test_auth_session.py、test_stage7_account_security.py、[浏览器](stage8_browser.json) | 通过 |
| SEC-02 | 管理员接口、学生本人、教师本班和任课、A-10、篡改对象及操作者 | test_rbac.py、test_object_permissions.py、test_stage4b_permissions.py、test_stage5_permissions.py、test_stage6_permissions.py、test_stage7_dashboard_permissions.py | 通过 |
| SEC-03 | CSRF、Cookie、回跳、HTML 转义、参数化查询、长度及分页、响应安全头 | test_csrf.py、test_auth_security.py、test_stage8_security.py、[安全审查](stage8_security_review.md) | 通过 |
| SEC-04 | 审计脱敏、追加保护、业务写与审计回滚 | test_stage7_audit_query.py、test_audit_append_only_replace.py、test_stage4_audit.py 至 test_stage7_user_management.py | 通过 |
| DB-01 | 13 表、94 字段、20 RESTRICT 外键、7 触发器、CHECK 和部分唯一索引 | [全新库结构](stage8_fresh_deployment.json)、[开发库核验](stage8_database_and_preservation.json) | 通过 |
| DB-02 | 有 WAL 的在线备份、拒绝覆盖、外键异常清理 | test_stage8_backup_restore.py、[恢复证据](stage8_backup_restore.json) | 通过 |
| DB-03 | 独立恢复、逐表行相等、恢复后启动与三角色业务读取 | [恢复证据](stage8_backup_restore.json) | 通过 |
| SYS-01 | 账号创建绑定、变更角色、启停、本人改密、查询审计 | [浏览器断言](stage8_browser.json) | 通过 |
| SYS-02 | 学生新增、编辑、归档恢复、搜索、真实分页，教师班级家长档案 | [浏览器断言](stage8_browser.json) | 通过 |
| SYS-03 | 建课、选课及重复拒绝、当前和历史成绩隔离、成绩读写 | test_stage8_end_to_end.py、[浏览器断言](stage8_browser.json) | 通过 |
| SYS-04 | 四种考勤、编辑、重复拒绝、日期范围及空数据 | test_stage8_end_to_end.py、[浏览器断言](stage8_browser.json) | 通过 |
| SYS-05 | 奖惩新增、编辑、历史查询及拒绝 | [浏览器断言](stage8_browser.json) | 通过 |
| SYS-06 | 家长联系新增与编辑、错误归属、历史查看、两种模拟通知 | test_parent_contact_service.py、test_stage6_notifications.py、[浏览器断言](stage8_browser.json) | 通过 |
| SYS-07 | 三角色统计、学期筛选、日期窗口、分母为零、手机端、无外部请求 | test_stage7_dashboard_statistics.py、[浏览器断言](stage8_browser.json) | 通过 |
| QA-01 | 原测试保留、全量 pytest、语法、路由、迁移及 UML | [全量](stage8_pytest.txt)、[源码核验](stage8_database_and_preservation.json)、[语法](stage8_compileall.txt)、[UML](stage8_uml_syntax.txt) | 通过 |

浏览器逐条结果、运行截图和各项数值见[阶段 8 报告](stage8_report.md)。
