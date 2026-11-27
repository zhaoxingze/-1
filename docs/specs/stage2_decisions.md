# 阶段 2 数据库实施决策

日期：2026-11-16。来源：用户本次《阶段 2 学生综合信息管理系统数据库与 ORM 完整实现》指令。本文件是新增实施决策，不能据此声称全部规则都已包含在最初 Word 中。

## 已确认的 18 项决策

1. 保留 11 张核心表、73 个原始字段及 16 个原始外键；原始逻辑类型及既有唯一性保持。
2. students 新增 is_archived BOOLEAN NOT NULL，默认 false。
3. 学籍状态与档案归档状态独立。
4. users.is_active 独立；学生归档不自动改变账号启用状态。
5. 新增 audit_logs，追加记录操作审计。
6. 新增 notification_logs，只存储模拟通知。
7. parent_contact_logs 新增 contact_person_name VARCHAR(50) NULL、contact_person_phone VARCHAR(30) NULL。长度是本阶段工程选择，非原始字段。
8. students.class_id 允许 NULL，支持未分班学生。
9. users.role_id 非空。
10. 原案其他业务必需外键非空；原案明确可空的班主任、授课教师、账号档案及家长关联保持可空。
11. parent_contact_logs.parent_id 可空。
12. parent_id 非空时必须属于同一 student_id；联系与通知均适用。
13. 联系记录 parent_id 为空时 contact_person_name 去空白后须有内容。
14. 每生最多一位主要家长，允许零位；用 SQLite 部分唯一索引落实。
15. 全部业务外键 ON DELETE RESTRICT，无 delete-orphan 或历史删除级联。
16. 仅保存当前班级与当前课程教师；不增加转班或任教历史表。历史数据仍按现阶段关系关联，不宣称具备历史班级快照。
17. 数据库时间统一 UTC naive datetime；输入 aware 时间需转换为 UTC 后去时区，业务展示时再按所需时区转换。DATE 字段不作时区转换。
18. 成绩权重变更、缺分提交策略、教师授权范围等继续待决；本阶段只做单分值的类型、有限性和 0–100 校验，不计算总分。

## 本阶段物理约定

学生 status：enrolled/suspended/graduated/withdrawn；家长关系：father/mother/guardian/other；联系方法：phone/in_person/sms/email/other；考勤及奖惩沿用原案英文值。角色代码固定三种但不固定主键。

审计表 9 字段：audit_id INTEGER PK、actor_user_id INTEGER NULL FK、entity_type VARCHAR(80) NN、entity_id INTEGER NN、action VARCHAR(30) NN、before_data JSON NULL、after_data JSON NULL、created_at DATETIME NN、request_id VARCHAR(100) NULL。action 允许 create/update/archive/restore/status_change/delete。索引覆盖 actor_user_id、entity_type、entity_id、created_at。快照递归移除凭证键；ORM 与 SQLite 更新/删除保护使审计不可改写。entity_id 是多态对象标识，不伪造到某一张业务表的外键。

通知表 9 字段：notification_id INTEGER PK、student_id INTEGER NN FK、parent_id INTEGER NULL FK、channel VARCHAR(20) NN、recipient_snapshot JSON NN、content TEXT NN、status VARCHAR(20) NN、created_by INTEGER NN FK、created_at DATETIME NN。channel=sms/email，status=prepared/simulated/cancelled；模拟服务只生成 simulated。学生、家长、创建时间建索引。快照是独立 JSON，不随家长字段变化重算。

最终为 **13 张领域表、94 字段、20 个外键**；Alembic 自带版本表另计。辅助表长度、命名约束、默认值、SQLite 触发器及下述服务接口是实施补全，不是另行扩展业务模块。

跨家长归属及用户档案角色匹配通过 Service 校验；ORM 写入也在 flush 前执行相关校验。SQLite 对联系/通知家长错配提供触发器兜底；原始外键仍保留，不用额外组合 FK 改变 16 条原始关系。

审查补全：每连接除 foreign_keys=ON 外同时启用 recursive_triggers=ON，防止 SQLite INSERT OR REPLACE 的隐式删除绕过审计保护；metadata 建库与实际迁移库均有覆盖原审计失败的回归测试。此项不增加新业务状态或表。

## 稳定服务接口

验证服务（失败抛 ValueError，允许传 session，默认 db.session）：

- validate_user_profile_binding(user, *, session=None) -> None，按 Role.name 及真实档案检查。
- validate_parent_student_binding(student_id, parent_id, *, session=None) -> Parent | None，验证学生存在、家长存在且属于学生；无家长只验证学生，联系姓名由联系模型约束处理。
- validate_score_value(value, *, allow_none=True) -> float | None，拒绝 bool、字符串、NaN、无穷与越界值；None 允许仅表示单字段可空，不代表确认部分成绩可提交。

审计四函数 record_create/record_update/record_archive/record_status_change 共用接口 `(entity_type, entity_id, *, actor_user_id=None, before_data=None, after_data=None, request_id=None, session=None) -> AuditLog`。只 add、不 commit，不承担实际归档或状态变更；调用者在同一事务中执行真实操作。通用 record_audit 可记录 restore/delete。

通知接口：validate_notification_target(student_id, parent_id=None, *, session=None) -> Parent | None；create_simulated_notification(student_id, channel, content, *, created_by, parent_id=None, recipient_snapshot=None, session=None) -> NotificationLog。有家长时默认生成姓名/电话/邮箱快照，无家长时必须明确提供非空接收对象快照。只 add、不 commit，无外部发送。

## 初始化、迁移与测试边界

应用工厂加载全部模型但不建表，不在 import 时连接数据库。新增 Flask-Migrate；以迁移升级创建结构。种子角色与演示数据幂等；create-admin 隐藏密码及确认，拒绝重复名，无默认密码；演示数据不创建账号且要求已有管理员。

原有 19 个测试全部保留。两项阶段 1 结构断言在本阶段作必要适配：不再要求 metadata 为空，改为工厂执行后实际数据库尚无表；开发测试使用独立临时 instance 路径，防止正式开发库迁移后影响测试。测试不删除或覆盖开发数据库。

## 原假设登记影响

A-07 归档、A-08 审计存储、A-09 模拟通知存储、A-11 空联系人、A-13 外键空值、A-17 RESTRICT、A-19 主要联系人及 A-10/A-21 当前关系简化在本阶段按用户决定落实。A-14 只确定用户此次给出的枚举，gender/period/credit 等仍未限定。A-18 只确定 UTC 时间存储；其他密码政策等待后续。A-02/A-03/A-04/A-05/A-06/A-12/A-15/A-16/A-20/A-22 的未确认部分继续待决。
