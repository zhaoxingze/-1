# Phase4A Archives Implementation Plan

> **For agentic workers:** Use superpowers:executing-plans; TDD per task and one independent final review.

**Goal:** 管理员学生、教师、班级、家长档案的完整指定功能。
**Architecture:** 复用admin Blueprint、四个领域Service、统一验证/分页/审计、Jinja模板；路由一次提交。
**Tech Stack:** 已固定Python3.12.10/Flask/SQLAlchemy2/SQLite/pytest，无新依赖。
**Spec:** [阶段4A设计](../../specs/stage4a_design.md)及用户完整阶段4A任务。

## Global Constraints

- 13表94字段20RESTRICT外键与7触发器/原迁移不变；不修改开发库。
- 旧251测试不删除、不跳过、不降低断言；stage3个人与认证界面保留。
- 仅管理员档案管理；教师范围留4B；不做课程成绩/考勤/奖惩/家长联系CRUD。
- 所有变更与审计同事务；CSRF；无物理删除、无自动账号创建/停用、无真实通知。

## Review Focus

- 同时修改两位主要联系人不能违反部分唯一索引，任何后续审计失败必须恢复两人。
- 状态/归档及账号参数不可通过普通编辑表单注入；已毕业/退学无回流。
- 关联详情、筛选、分页与嵌套家长ID均执行后端角色/归属检查。
- 旧公共接口、认证工厂及原251不被新增管理路由破坏。
- 不泄露DB异常、凭据或范围外个人信息，打包后能在独立环境运行。

## Task 1: Domain services

Files: services/archive_common.py、student_service.py、teacher_service.py、class_service.py、parent_service.py；tests六个指定文件。
Interfaces: 见设计末节，读写均显式actor；Service只flush/add。

- [x] 阅读基线、备份并实跑251项。
- [x] 写服务规则、审计/回滚与主要联系人测试并观察红测。
- [x] 实现四服务和共用验证/分页/审计；专项绿测。

## Task 2: Forms, routes, UI

Files: admin/archive_forms.py、archive_views.py、student_routes.py、teacher_routes.py、class_routes.py、parent_routes.py；templates/admin/*、导航和管理员入口。
Interfaces: canonical /admin/students|teachers|classes|parents；原stage3路由不改行为；路由一次事务。

- [x] 管理路由/权限/CSRF/输入/分页测试先红。
- [x] 实现表单、路由及实际可用页面；成功/失败反馈与归档确认。
- [x] 新增专项及完整pytest通过。

## Task 3: Validation and delivery

- [x] 独立审查与必要修复；真实浏览器操作和移动端截图。
- [x] 同步需求/架构/假设/UML/README及stage4a_report。
- [x] pip check、db check、原文件/开发库SHA和结构核验。
- [x] 源码ZIP、清单和解压后完整回归；报告并停止4A。

## Ledger / Rulings

- 2026-11-18: 无Git，按用户指定目录直接实施；工作区外完整备份167文件并校验CRC/SHA，清单在临时任务目录，位置见stage4a_backup.json。
- 基线251 passed in82.28s。原/学生前缀404测试通过，新增/admin管理路径解决建议接口与保留测试的冲突。
- 用户已明确授权完整4A和最小实现；不增加重复设计审批。日期/字典/教师业务范围不补成未经确认硬规则。
- Task1→2接口与事务统一；服务显式actor，表单白名单不能更改学籍/归档/账号；无共享接口冲突。

- Task1服务13passed，管理路由/服务缺失2failed红测后实施；Task2首批71passed含WTForms弃用警告，用-W error实际复现后改SelectChoice；完整集成328passed。
- 独立初审1Critical/3Important/3Minor：终态逆转、主要设置未生效、false确认、家长筛选丢失、引用三表全量读取、空班级筛选、ID上限。复现6failed/1passed，修复后专项76passed，完整335passed in106.89s。所有发现已处理，未宣称独立复审已给出新结论。
- Ruling: SQLite BEGIN IMMEDIATE在写业务读取前取得，已有事务复用、目标刷新；外层commit/rollback释放锁。该栈支持SQLite，未扩展其它数据库并发保证；锁竞争以受控失败回滚。
- 用户业务未决范围不扩张；DataRequired验证确认真值，保留家长学生选择器，分页与实体ID分开，引用按实体只查标签列。
- 浏览器23检查通过，12实际截图；最终详情截图已刷新。UML七源十图语法/受影响图渲染exit0。
- 2026-11-19解压运行源，新虚拟环境安装requirements并pip check通过，全量335passed in202.51s。最终ZIP需包含与此相同的运行源SHA，不以文档更新冒充代码变化验证。
- Review Declined rulings: 教师范围/学籍例外/其它业务CRUD继续待决且默认拒绝；当前输入约定均记录为技术最小校验，不添业务字典。主执行者承担浏览器/UML/冻结及ZIP核验并保留实际证据。

- Delivery: 源码ZIP CRC/解压逐项摘要/链接/排除规则检查通过，运行源与新环境335项被测源码完全一致；完整性与SHA见打包核验及旁置.sha256。停止4A。
