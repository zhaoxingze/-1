# 阶段 2 数据库与 ORM 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** 实现 13 张领域表、完整迁移与初始化 CLI，保留阶段 1 的 19 项回归测试。

**Architecture:** 模型用 Mapped/mapped_column/relationship，Service 提供无内部提交的验证、审计和通知辅助。迁移管理结构，工厂只加载模型和扩展。

**Tech Stack:** 现有 Python 3.12.10 venv、Flask/SQLAlchemy 2.x/SQLite/Flask-Migrate/Alembic/pytest。

**Spec:** [阶段 2 决策与接口](../../specs/stage2_decisions.md)，以及用户本次完整阶段 2 指令。现阶段非 Git 仓库，不初始化 Git，不删除既有数据库；仅在确认无文件时升级默认开发库。

## Global Constraints

- 保留 11 表 73 原字段 16 原 FK；只加用户确认的 3 核心字段和两个 9 字段辅助表。
- 全部 FK RESTRICT，SQLite 每连接启用外键，审计不可改写，无业务路由、登录、RBAC 或真实通知。
- 所有测试使用临时 SQLite；回归测试保留，旧结构断言按本阶段授权的模型存在作必要适配。
- 新功能测试先写失败用例；实施任务按文件边界并行，审查与集成顺序执行。

## Review Focus

- ORM 与原始字段类型、所有空值、关系和唯一性一致；通过实际元数据及迁移后结构对照测试。
- 原始 SQL、ORM bulk 更新或对象关联不能绕过家长归属和审计不可变；触发器及失败回滚测试。
- 时间的 aware 输入、凭证嵌套快照、非法/非有限分数均有边界测试。
- CLI 无默认密码，重复执行不重复数据；部分种子缺失不能留下半个业务事务。
- 工厂和 import 不建表，默认开发库与所有测试分离；迁移历史可升级空库且不覆盖现有库。

## Task 1 模型与约束

Files: app/models/*；tests/test_models.py、test_database_constraints.py。只写这些范围。

- [x] 根据 stage2_decisions 定义 13 模型，全部字段/类型/relationship、命名约束与索引；时间帮助器 utc_now()/UTCNaiveDateTime。
- [x] ORM before_flush 执行用户档案及家长关联验证；成绩属性验证调用验证服务；审计追加保护及敏感快照清洗。
- [x] SQLite DDL 触发器放入 app/models/integrity.py 的 SQLITE_TRIGGERS 字典，metadata after_create 用于测试；正式迁移复制稳定 SQL。
- [x] 在临时库运行关系、字段、唯一性、CHECK、删除和 FK/触发器测试。

## Task 2 验证、审计与通知服务

Files: app/services/data_validation_service.py、audit_service.py、notification_service.py；tests/test_data_validation_service.py、test_audit_service.py、test_notification_service.py。

- [x] 遵守决策中的稳定接口。模型导出 Role/User/Teacher/SchoolClass/Student/Course/Enrollment/AttendanceRecord/RewardRecord/Parent/ParentContactLog/AuditLog/NotificationLog。
- [x] 测试全部函数、嵌套凭证、系统 actor、只 add 不 commit、事务回滚、通知快照与跨学生拒绝。
- [x] 不做成绩公式、归档业务、教师范围或管理员查询路由；只交付本阶段辅助能力。

## Task 3 集成、迁移与 CLI

Files: app/extensions.py、app/__init__.py、app/cli.py、config.py、tests/conftest.py、两项阶段 1 配置测试；新增 tests/test_database_cli.py、test_database_migrations.py；migrations/*。

- [x] 安装 Flask-Migrate；SQLite Engine connect listener 开启 PRAGMA foreign_keys=ON。
- [x] 工厂支持可选 instance_path，加载全部模型及迁移，注册 CLI；不 create_all。
- [x] seed-roles 幂等、create-admin 安全交互及哈希、seed-demo 幂等且要求管理员；事务中记录审计，无默认账号。
- [x] 生成初始迁移、加入不可变和归属触发器，临时空库实际升级并检查 drift；确认默认库不存在后升级并创建角色，演示仅在临时库测试。
- [x] 全套回归、pip check，按实际安装更新 requirements.txt。

## Task 4 设计同步与验收

- [x] 同步四份规格与数据库字典、类图/ER/索引，原始与阶段 2 新增清楚区分。
- [x] 真实启动、截图、检查 13 领域表及 Alembic 版本表、FK 完整性；保留旧报告历史记录。
- [x] 独立审查并修复重要问题；生成 stage2_report.md，记录命令、实际数量和遗留事项，停止等待阶段 3。

## 进度

前置：原 19 项测试 19 passed in 0.57s；instance 只有 .gitkeep，无数据库。模型与服务共享稳定接口，文件不重叠；CLI 消费两者，待集成后执行测试。非 Git 下保留本计划作进度账本，不调用依赖提交历史的技能脚本。

Task 1 complete：13实体94字段20FK，原73字段/16FK保持；模型与约束64项定向通过，7触发器。

Task 2 complete：三个服务63项定向通过，快照JSON非法/非有限值先red再修复；无commit、无网络发送。

Task 3 complete：初始revision fab16ef0dd6f，空库迁移与db check通过；CLI角色/管理员/演示幂等实测。默认新开发库仅3角色+3系统审计，无默认账号。原19项保留并回归通过。

Task 4 complete：文档/类图ER同步，原业务图仅更新已定说明，7源语法通过，类图ER渲染查看；真实HTTP200和截图。审计REPLACE漏洞2failed→2passed；独立完成审查无Critical/Important，48专项通过；全量156passed，pip check通过。

Ruling：旧metadata为空的阶段1结构断言按本阶段已加载13模型适配为“不自动建库”，并使用临时instance；保留全部原测试函数。当前非Git目录无提交历史，通过测试名、原字典与Word摘要独立核验。原成绩/权限业务待决继续保留。
