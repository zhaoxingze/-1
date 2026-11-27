# 学生综合信息管理系统阶段 2 完成报告

日期：2026-11-16。范围：数据库、ORM、辅助服务、迁移、CLI 与自动化测试。保留阶段 1 骨架和全部 19 个原测试，不实施登录、完整 RBAC、业务 CRUD 或真实通知。

## 1 本阶段实施内容

用户本次明确的 [18 项数据库决策](../specs/stage2_decisions.md) 是阶段 2 扩展，不全部来自原案。原 11 表、73 原字段、16 原 FK 保留；增加 Student.is_archived、联系姓名和电话三个核心字段，增加 AuditLog、NotificationLog 两辅助实体，最终 **13 张领域表、94 字段、20 个 RESTRICT FK**。Alembic 版本表单独计数，物理库共有 14 表。

模型按 13 个实体文件组织，使用 SQLAlchemy 2 的 Mapped/mapped_column/relationship。统一导出完整 metadata；UTC 类型、快照脱敏和完整性守卫为共用模块。所有父端无 delete-orphan/删除级联。

## 2 最终表清单与字段数

| 表 | 字段数 | 变化 |
| --- | --- | --- |
| roles | 3 | 原始 |
| teachers | 5 | 原始 |
| school_classes | 4 | 原始 |
| students | 11 | 原10字段 + is_archived |
| users | 8 | 原始 |
| courses | 6 | 原始 |
| enrollments | 8 | 原始 |
| attendance_records | 7 | 原始 |
| reward_records | 7 | 原始 |
| parents | 7 | 原始 |
| parent_contact_logs | 10 | 原8字段 + 联系姓名/电话 |
| audit_logs | 9 | 阶段2新增 |
| notification_logs | 9 | 阶段2新增 |
| 合计领域表 | 94 | 13表；原73字段类型保持 |

完整字段、CHECK、索引和关系见 [数据库字典](../specs/database_design.md) 及 [机器可读结构](stage2_schema.json)。[开发库实查记录](stage2_database_inspection.json) 来自迁移后实际 SQLite。

## 3 完整性和辅助表理由

全部 9 组原唯一性落实；主要家长另有 student_id WHERE is_primary=1 部分唯一索引，允许没有主要联系人。分数 NULL 或 0–100，并在应用层拒绝 bool、字符串及非有限数。学籍、考勤、奖惩、家长关系和联系方法按用户指定枚举 CHECK。全部20 FK开启 RESTRICT，每连接 PRAGMA foreign_keys=1。

用户角色档案匹配通过验证服务，并在 ORM flush 复核，角色由名字确定，不假设 ID。联系/通知要求家长属于学生；联系无家长时姓名必填。SQLite 7 个触发器覆盖审计改删、联系/通知插入更新归属和家长重新绑定历史冲突。直接 SQL/bulk 改删审计同样被阻止。

audit_logs 解决原案“操作人和时间、前后状态”缺少存储的问题；系统操作 actor 可空，快照递归移除密码哈希、密钥、Token等凭证并验证有限 JSON；只追加，不提供用户查询路由，未来仅管理员授权查询。通知表独立保存渠道、状态和接收快照，避免混用联系结果或被家长资料变化重写历史；仅模拟，无真实网络发送。

三个 Service 的函数均有测试。审计辅助函数只记录，不代办归档或学籍变更；审计和通知服务只 add，不 commit，由调用方同事务提交或回滚。成绩公式、缺分提交、教师授权范围均未擅自实现。时间默认当前 UTC，aware 输入转换后以 UTC naive 存储。

## 4 初始化与迁移

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m flask --app run db upgrade
.\.venv\Scripts\python.exe -m flask --app run seed-roles
.\.venv\Scripts\python.exe -m flask --app run create-admin
# 可选：管理员存在后生成虚构业务数据，不创建账号
.\.venv\Scripts\python.exe -m flask --app run seed-demo
.\.venv\Scripts\python.exe -m flask --app run db check
.\.venv\Scripts\python.exe -m pytest -q
```

实际生成初始 revision `fab16ef0dd6f` 并执行升级，见 [升级日志](stage2_upgrade.txt)、[结构无漂移检查](stage2_migration_check.txt)。新部署使用现有迁移脚本直接 upgrade，无须再次 db init。工厂及 import 不建表或种子。

阶段 2 开始时 instance 只有 .gitkeep，原开发库不存在；本次显式迁移后只初始化三个角色及相应系统审计，角色重复执行新增数为 3、0。未给开发库创建默认管理员或演示账号；管理员交互与演示幂等性在独立临时库实际验证。create-admin 隐藏密码并确认，Werkzeug 哈希，拒绝重名，无硬编码默认密码。

seed-demo 使用 DEMO 标识、虚构姓名、000 格式电话与 example.invalid 邮箱；已有管理员作操作人，重复执行不重复数据，不修改已存在记录。全部种子为单事务，无部分提交。不删除或替换任何原数据库。

## 5 自动化测试与修复证据

开始时原19项实际 `19 passed in 0.57s`。两项配置测试保留名称/断言意图，改为独立临时 instance，metadata 注册13实体后仍验证工厂/公共页不创建数据库；没有删除原测试。原业务 TC-01 至 TC-12 的界面流程仍不在此阶段声称通过。

首轮集成154项通过；审计REPLACE修复增加2项后，最终全套实际 **156 passed in 60.22s**，见 [测试日志](stage2_pytest.txt)。[旧测试单独回归](stage2_stage1_regression.txt) 为19 passed。覆盖字段与关系、唯一性、所有枚举/成绩边界、FK开启、RESTRICT、主要家长、跨学生归属、追加审计、JSON去凭证、UTC、调用方事务、仅模拟通知、CLI哈希/重复初始化、空库实际迁移及重复upgrade、metadata无漂移和旧19回归。

实现中实际观察并修复：自定义 UTC 类型的 Alembic 自动生成表达未自带 import，改用稳定 sa.DateTime；冻结触发器 SQL 进入 migration；Alembic 默认 fileConfig 禁用了既有 Flask logger，导致迁移后500日志旧测试失败，改为 disable_existing_loggers=False；快照非法对象/非有限数在 add 前拒绝。失败记录与修复后测试如实保留，不删除失败用例。

## 6 变更文件与设计同步

新增13模型及types/security/integrity、三个辅助服务、CLI、迁移目录、6个指定测试文件及验证服务测试。修改工厂、extensions、测试fixture和两项旧测试的阶段适配。requirements固定新增Flask-Migrate/Alembic及依赖实际版本。

需求、架构、数据库、假设、阶段2决策及类图/ER/索引同步。原始73字段名称和类型经脚本对照旧字典核验；其他阶段0 UML作为后续业务流程设计保留，原Word未更改。阶段0/1报告保留为历史记录。

## 7 运行截图与最终审查

真实启动本机 Flask 服务后，首页与 /health 均返回200，页面显示阶段2数据层，控制台0 errors/0 warnings。见 [HTTP实测](stage2_http_smoke.json) 与 [运行截图](../../output/playwright/stage2-homepage.png)。截图已实际查看，没有登录或CRUD界面。

七类UML源均通过PlantUML语法检查，更新的类图和ER图已实际渲染并查看。原用例/流程主体保留，仅把班级可空性和通知持久化说明同步为阶段2已决定；不会把数据库模型完成冒充业务用例完成。

独立审查发现SQLite默认设置下INSERT OR REPLACE可绕过审计DELETE触发器，已先实际复现metadata及migration两库2 failed，再为每连接开启recursive_triggers=ON，回归2 passed，原审计记录保持不变。见 [失败证据](stage2_audit_replace_red.txt)。该修复不更改现有表结构或迁移数据。

后续独立完成审查结论为可交付，未发现Critical/Important；其迁移与约束专项实跑48 passed。文档中Boolean CHECK的内部POSTCOMPILE表达已修正为实际IN (0,1)，实际模型/迁移本来正确。最终主代理全量156项通过，pip check无冲突，db check无新升级操作。

[最终结构与文档核验](stage2_final_validation.json) 确认13表94字段20FK、原73字段类型和16原FK保留、旧测试函数名称保留、Word摘要不变、外键与递归触发器均为1，PRAGMA foreign_key_check为空。类图/ER全字段与实际metadata相符；全部本地Markdown链接可解析。

验收结束关闭本次浏览器与临时服务器，不提供持续运行服务；用户按README命令重新启动。当前无阻断问题，未进入阶段3。

## 8 遗留事项与下一阶段

成绩权重变更/缺分提交、统计口径、教师和学生数据权限、历史记录访问及状态例外继续待决，详见 [假设登记](../specs/assumptions.md)。只保存当前班级/当前教师关系，没有历史快照。SQLite VARCHAR 长度需后续业务输入校验；审计仅提供记录能力，未来业务写服务须同事务调用，授权查询待RBAC。

阶段1记录的同进程 app.logger 级别共享仍是非阻断限制，不影响独立服务器或数据库隔离；本阶段只修复迁移意外禁用日志的问题。下一阶段按用户指令实施认证/RBAC，在开放教师范围前确认对应未决规则；本阶段完成后停止，不自行开始阶段3。
