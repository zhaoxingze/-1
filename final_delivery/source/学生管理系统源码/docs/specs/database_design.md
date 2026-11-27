# 学生综合信息管理系统数据库设计

版本：0.2；更新日期：2026-11-16；状态：阶段 2 ORM 与初始迁移依据。

保留原 11 张核心表、73 个原始字段和 16 个原始 FK；按用户阶段 2 指令新增 3 个核心字段和两个各 9 字段的辅助表。最终为 **13 张领域表、94 字段、20 条 FK**，另有 Alembic 自带版本表，不算业务实体。原始逻辑类型保持；来源区分见每字段“来源”列。

关联：[阶段2决策](stage2_decisions.md)、[需求](requirements.md)、[架构](architecture.md)、[假设登记](assumptions.md)、[类图](../uml/class_diagram.puml)、[ER图](../uml/er_diagram.puml)。原始方案仍见 [Word](source/学生管理系统_前期设计方案与Codex分阶段提示词.docx)。

## 1 存储与完整性约定

- PK 为 INTEGER 非空主键；NN 非空；NULL 可空；UQ 唯一；FK 全部 ON DELETE RESTRICT。SQLite 每连接开启 PRAGMA foreign_keys=ON 及 recursive_triggers=ON，确保 INSERT OR REPLACE 不能绕过审计删除守卫。
- students.class_id 可空；users.role_id 和其余原案必需业务 FK 非空，原案明确可空的 FK 保持。User 两档案外键分别可空且非空值唯一，角色与档案互斥匹配必须通过服务检查，ORM flush 再检查。
- 日期时间为 UTC naive。UTCNaiveDateTime 将 aware 输入转换 UTC 再去时区；默认 utc_now 或数据库 CURRENT_TIMESTAMP。DATE 不转换。
- 所有业务父端使用普通关系，无 delete-orphan/删除级联；引用存在时阻止删除，包括操作 User 和家长。
- VARCHAR 长度声明沿用原案，SQLite 不自动保证其长度上限；后续表单/业务服务仍需长度及格式校验。gender、学期格式、节次字典与学分门槛仍不擅自限定。
- is_archived 默认 false；is_active 默认 true；is_primary 默认 false；新学籍默认 enrolled；通知默认 prepared，模拟服务明确写 simulated。这些默认值是阶段 2 工程选择，不代表原 Word 全部已定。

## 2 最终表清单

| 类 | 表 | 字段数 | 来源 |
| --- | --- | --- | --- |
| Role | roles | 3 | 核心表，保留原字段 |
| Teacher | teachers | 5 | 核心表，保留原字段 |
| SchoolClass | school_classes | 4 | 核心表，保留原字段 |
| Student | students | 11 | 核心表，保留原字段 |
| User | users | 8 | 核心表，保留原字段 |
| Course | courses | 6 | 核心表，保留原字段 |
| Enrollment | enrollments | 8 | 核心表，保留原字段 |
| AttendanceRecord | attendance_records | 7 | 核心表，保留原字段 |
| RewardRecord | reward_records | 7 | 核心表，保留原字段 |
| Parent | parents | 7 | 核心表，保留原字段 |
| ParentContactLog | parent_contact_logs | 10 | 核心表，保留原字段 |
| AuditLog | audit_logs | 9 | 阶段2辅助表 |
| NotificationLog | notification_logs | 9 | 阶段2辅助表 |

## 3 字段字典

### 3.1 roles

| 字段 | 类型 | 约束 | 来源 | 说明 |
| --- | --- | --- | --- | --- |
| role_id | INTEGER | PK | 原始字段 | 角色主键 |
| name | VARCHAR(30) | NN、UQ | 原始字段 | admin / teacher / student |
| description | VARCHAR(200) | NULL | 原始字段 | 角色说明 |

### 3.2 teachers

| 字段 | 类型 | 约束 | 来源 | 说明 |
| --- | --- | --- | --- | --- |
| teacher_id | INTEGER | PK | 原始字段 | 教师主键 |
| teacher_no | VARCHAR(30) | NN、UQ | 原始字段 | 教师编号 |
| name | VARCHAR(50) | NN | 原始字段 | 姓名 |
| phone | VARCHAR(30) | NULL | 原始字段 | 电话 |
| email | VARCHAR(100) | NULL | 原始字段 | 邮箱 |

### 3.3 school_classes

| 字段 | 类型 | 约束 | 来源 | 说明 |
| --- | --- | --- | --- | --- |
| class_id | INTEGER | PK | 原始字段 | 班级主键 |
| class_name | VARCHAR(50) | NN | 原始字段 | 班级名称；原案未规定名称或年级名称组合唯一 |
| grade | VARCHAR(30) | NN | 原始字段 | 年级 |
| homeroom_teacher_id | INTEGER | NULL、FK → teachers.teacher_id | 原始字段 | 班主任，可暂未指定 |

### 3.4 students

| 字段 | 类型 | 约束 | 来源 | 说明 |
| --- | --- | --- | --- | --- |
| student_id | INTEGER | PK | 原始字段 | 学生主键 |
| student_no | VARCHAR(30) | NN、UQ | 原始字段 | 学号 |
| name | VARCHAR(50) | NN | 原始字段 | 学生姓名 |
| gender | VARCHAR(10) | NN | 原始字段 | 性别，具体值域未指定 A-14 |
| birth_date | DATE | NULL | 原始字段 | 出生日期；年龄计算展示，不存 age |
| phone | VARCHAR(30) | NULL | 原始字段 | 学生电话 |
| address | VARCHAR(255) | NULL | 原始字段 | 家庭住址 |
| class_id | INTEGER | NULL、FK → school_classes.class_id | 原始字段 | 可空，允许未分班 |
| enrollment_date | DATE | NN | 原始字段 | 入学日期 |
| status | VARCHAR(20) | NN | 原始字段 | enrolled/suspended/graduated/withdrawn；学籍独立于归档 |
| is_archived | BOOLEAN | NN | 阶段2新增 | 独立归档标记；默认 false，不改变学籍或账号启停 |

### 3.5 users

| 字段 | 类型 | 约束 | 来源 | 说明 |
| --- | --- | --- | --- | --- |
| user_id | INTEGER | PK | 原始字段 | 账号主键 |
| username | VARCHAR(50) | NN、UQ | 原始字段 | 登录名 |
| password_hash | VARCHAR(255) | NN | 原始字段 | 密码哈希 |
| role_id | INTEGER | NN、FK → roles.role_id | 原始字段 | 必需角色；角色档案匹配由 Service 与 ORM 检验 |
| student_id | INTEGER | NULL、UQ、FK → students.student_id | 原始字段 | 学生账号关联档案 |
| teacher_id | INTEGER | NULL、UQ、FK → teachers.teacher_id | 原始字段 | 教师账号关联档案 |
| is_active | BOOLEAN | NN | 原始字段 | 账号启停，不等于学籍状态 |
| created_at | DATETIME | NN | 原始字段 | 账号创建时间；时区见 A-18；UTC naive |

### 3.6 courses

| 字段 | 类型 | 约束 | 来源 | 说明 |
| --- | --- | --- | --- | --- |
| course_id | INTEGER | PK | 原始字段 | 课程主键 |
| course_code | VARCHAR(30) | NN、UQ | 原始字段 | 课程编号 |
| course_name | VARCHAR(100) | NN | 原始字段 | 课程名称 |
| credit | FLOAT | NN | 原始字段 | 学分；最小值和步长待定 A-14 |
| teacher_id | INTEGER | NULL、FK → teachers.teacher_id | 原始字段 | 当前授课教师，单教师模型 |
| description | TEXT | NULL | 原始字段 | 课程说明 |

### 3.7 enrollments

| 字段 | 类型 | 约束 | 来源 | 说明 |
| --- | --- | --- | --- | --- |
| enrollment_id | INTEGER | PK | 原始字段 | 选课与成绩记录主键 |
| student_id | INTEGER | NN、FK → students.student_id | 原始字段 | 选课学生 |
| course_id | INTEGER | NN、FK → courses.course_id | 原始字段 | 课程 |
| semester | VARCHAR(30) | NN | 原始字段 | 学期；2026-Fall 只是示例，不是既定正则 |
| usual_score | FLOAT | NULL | 原始字段 | 平时成绩，存在时为 0–100 |
| exam_score | FLOAT | NULL | 原始字段 | 考试成绩，存在时为 0–100 |
| total_score | FLOAT | NULL | 原始字段 | 由服务计算的总分，存在时为 0–100 |
| created_at | DATETIME | NN | 原始字段 | 选课记录创建时间，不是最近成绩修改时间；UTC naive |

### 3.8 attendance_records

| 字段 | 类型 | 约束 | 来源 | 说明 |
| --- | --- | --- | --- | --- |
| attendance_id | INTEGER | PK | 原始字段 | 考勤主键 |
| student_id | INTEGER | NN、FK → students.student_id | 原始字段 | 学生 |
| attendance_date | DATE | NN | 原始字段 | 考勤日期；统一使用此名，不用图中的 date 简写 |
| period | VARCHAR(30) | NN | 原始字段 | 节次或时段；值域待 A-14 |
| status | VARCHAR(20) | NN | 原始字段 | present / late / absent / leave |
| note | VARCHAR(255) | NULL | 原始字段 | 备注或请假原因；未规定请假原因必填 |
| recorded_by | INTEGER | NN、FK → users.user_id | 原始字段 | 登记 User，不是 Teacher；由会话确定 |

### 3.9 reward_records

| 字段 | 类型 | 约束 | 来源 | 说明 |
| --- | --- | --- | --- | --- |
| record_id | INTEGER | PK | 原始字段 | 奖惩主键，不改成 reward_id |
| student_id | INTEGER | NN、FK → students.student_id | 原始字段 | 学生 |
| record_type | VARCHAR(20) | NN | 原始字段 | reward / punishment |
| category | VARCHAR(50) | NN | 原始字段 | 奖励或处分类别，未给出封闭字典 |
| description | TEXT | NN | 原始字段 | 事由 |
| occurred_on | DATE | NN | 原始字段 | 发生日期，不是记录创建时间 |
| created_by | INTEGER | NN、FK → users.user_id | 原始字段 | 记录 User |

### 3.10 parents

| 字段 | 类型 | 约束 | 来源 | 说明 |
| --- | --- | --- | --- | --- |
| parent_id | INTEGER | PK | 原始字段 | 家长联系档案主键 |
| student_id | INTEGER | NN、FK → students.student_id | 原始字段 | 所属学生 |
| name | VARCHAR(50) | NN | 原始字段 | 家长姓名 |
| relationship | VARCHAR(20) | NN | 原始字段 | father/mother/guardian/other |
| phone | VARCHAR(30) | NN | 原始字段 | 联系电话，不要求全局唯一 |
| email | VARCHAR(100) | NULL | 原始字段 | 邮箱 |
| is_primary | BOOLEAN | NN | 原始字段 | 每生最多一位 true，允许零位 |

### 3.11 parent_contact_logs

| 字段 | 类型 | 约束 | 来源 | 说明 |
| --- | --- | --- | --- | --- |
| contact_id | INTEGER | PK | 原始字段 | 联系记录主键 |
| student_id | INTEGER | NN、FK → students.student_id | 原始字段 | 关联学生 |
| parent_id | INTEGER | NULL、FK → parents.parent_id | 原始字段 | 可空；非空时必须属于同一学生 |
| method | VARCHAR(20) | NN | 原始字段 | phone/in_person/sms/email/other |
| content | TEXT | NN | 原始字段 | 联系内容 |
| result | TEXT | NULL | 原始字段 | 沟通结果，不等于结构化通知发送状态 |
| contacted_at | DATETIME | NN | 原始字段 | 业务联系时间，不一定是录入时间；UTC naive |
| created_by | INTEGER | NN、FK → users.user_id | 原始字段 | 记录 User |
| contact_person_name | VARCHAR(50) | NULL | 阶段2新增 | 无 parent_id 时去空白姓名必填 |
| contact_person_phone | VARCHAR(30) | NULL | 阶段2新增 | 未关联家长时可保存的联系对象电话 |

### 3.12 audit_logs

| 字段 | 类型 | 约束 | 来源 | 说明 |
| --- | --- | --- | --- | --- |
| audit_id | INTEGER | PK | 阶段2新增 | 审计主键 |
| actor_user_id | INTEGER | NULL、FK → users.user_id | 阶段2新增 | 操作用户；系统操作可空 |
| entity_type | VARCHAR(80) | NN | 阶段2新增 | 多态被操作对象类型 |
| entity_id | INTEGER | NN | 阶段2新增 | 多态对象 ID，无伪造单表外键 |
| action | VARCHAR(30) | NN | 阶段2新增 | create/update/archive/restore/status_change/delete |
| before_data | JSON | NULL | 阶段2新增 | 修改前 JSON；递归移除凭证 |
| after_data | JSON | NULL | 阶段2新增 | 修改后 JSON；递归移除凭证 |
| created_at | DATETIME | NN | 阶段2新增 | UTC naive；默认当前 UTC；UTC naive |
| request_id | VARCHAR(100) | NULL | 阶段2新增 | 可空请求追踪标识 |

### 3.13 notification_logs

| 字段 | 类型 | 约束 | 来源 | 说明 |
| --- | --- | --- | --- | --- |
| notification_id | INTEGER | PK | 阶段2新增 | 模拟通知主键 |
| student_id | INTEGER | NN、FK → students.student_id | 阶段2新增 | 目标学生 |
| parent_id | INTEGER | NULL、FK → parents.parent_id | 阶段2新增 | 可空家长；非空须属于目标学生 |
| channel | VARCHAR(20) | NN | 阶段2新增 | sms/email |
| recipient_snapshot | JSON | NN | 阶段2新增 | 独立 JSON 接收对象快照 |
| content | TEXT | NN | 阶段2新增 | 模拟通知内容，无真实发送 |
| status | VARCHAR(20) | NN | 阶段2新增 | prepared/simulated/cancelled；模拟服务只生成 simulated |
| created_by | INTEGER | NN、FK → users.user_id | 阶段2新增 | 创建 User |
| created_at | DATETIME | NN | 阶段2新增 | UTC naive；默认当前 UTC；UTC naive |

## 4 外键与关系

| 子表字段 | 引用 | 每条子记录的父对象数 | 父到子 |
| --- | --- | --- | --- |
| school_classes.homeroom_teacher_id | teachers.teacher_id | 0..1 | 0..* |
| students.class_id | school_classes.class_id | 0..1 | 0..* |
| users.role_id | roles.role_id | 1 | 0..* |
| users.student_id | students.student_id | 0..1 | 0..1 |
| users.teacher_id | teachers.teacher_id | 0..1 | 0..1 |
| courses.teacher_id | teachers.teacher_id | 0..1 | 0..* |
| enrollments.student_id | students.student_id | 1 | 0..* |
| enrollments.course_id | courses.course_id | 1 | 0..* |
| attendance_records.student_id | students.student_id | 1 | 0..* |
| attendance_records.recorded_by | users.user_id | 1 | 0..* |
| reward_records.student_id | students.student_id | 1 | 0..* |
| reward_records.created_by | users.user_id | 1 | 0..* |
| parents.student_id | students.student_id | 1 | 0..* |
| parent_contact_logs.student_id | students.student_id | 1 | 0..* |
| parent_contact_logs.parent_id | parents.parent_id | 0..1 | 0..* |
| parent_contact_logs.created_by | users.user_id | 1 | 0..* |
| audit_logs.actor_user_id | users.user_id | 0..1 | 0..* |
| notification_logs.student_id | students.student_id | 1 | 0..* |
| notification_logs.parent_id | parents.parent_id | 0..1 | 0..* |
| notification_logs.created_by | users.user_id | 1 | 0..* |

学生与课程只经 Enrollment 形成按学期多对多；Parent 是某学生的联系档案，不新增共享家长多对多表。课程教师和学生班级是当前关系，没有历史班级或任教快照。

## 5 唯一性、CHECK 与索引

下列与模型/迁移一一对应。部分唯一索引只限制 true 家长，不要求每生至少一位。

### roles
- UNIQUE(name)
- CHECK `ck_roles_name`：`name IN ('admin','teacher','student')`

### teachers
- UNIQUE(teacher_no)

### school_classes
- 索引 `ix_school_classes_homeroom_teacher_id` (homeroom_teacher_id)

### students
- UNIQUE(student_no)
- CHECK `ck_students_is_archived`：`students.is_archived IN (0, 1)`
- CHECK `ck_students_status`：`status IN ('enrolled','suspended','graduated','withdrawn')`
- 索引 `ix_students_class_id` (class_id)
- 索引 `ix_students_status` (status)

### users
- UNIQUE(teacher_id)
- UNIQUE(student_id)
- UNIQUE(username)
- CHECK `ck_users_is_active`：`users.is_active IN (0, 1)`
- 索引 `ix_users_role_id` (role_id)

### courses
- UNIQUE(course_code)
- 索引 `ix_courses_teacher_id` (teacher_id)

### enrollments
- UNIQUE(student_id, course_id, semester)
- CHECK `ck_enrollments_exam_score`：`exam_score IS NULL OR (exam_score >= 0 AND exam_score <= 100)`
- CHECK `ck_enrollments_usual_score`：`usual_score IS NULL OR (usual_score >= 0 AND usual_score <= 100)`
- CHECK `ck_enrollments_total_score`：`total_score IS NULL OR (total_score >= 0 AND total_score <= 100)`
- 索引 `ix_enrollments_course_id` (course_id)
- 索引 `ix_enrollments_semester` (semester)
- 索引 `ix_enrollments_student_id` (student_id)

### attendance_records
- UNIQUE(student_id, attendance_date, period)
- CHECK `ck_attendance_status`：`status IN ('present','late','absent','leave')`
- 索引 `ix_attendance_records_attendance_date` (attendance_date)
- 索引 `ix_attendance_records_recorded_by` (recorded_by)
- 索引 `ix_attendance_records_student_id` (student_id)

### reward_records
- CHECK `ck_reward_record_type`：`record_type IN ('reward','punishment')`
- 索引 `ix_reward_records_created_by` (created_by)
- 索引 `ix_reward_records_occurred_on` (occurred_on)
- 索引 `ix_reward_records_student_id` (student_id)

### parents
- CHECK `ck_parents_is_primary`：`parents.is_primary IN (0, 1)`
- CHECK `ck_parents_relationship`：`relationship IN ('father','mother','guardian','other')`
- 索引 `ix_parents_student_id` (student_id)
- 部分唯一索引 `uq_parents_primary_per_student` (student_id) WHERE `is_primary = 1`

### parent_contact_logs
- CHECK `ck_parent_contacts_method`：`method IN ('phone','in_person','sms','email','other')`
- CHECK `ck_parent_contacts_explicit_name`：`parent_id IS NOT NULL OR (contact_person_name IS NOT NULL AND length(trim(contact_person_name, char(9)||char(10)||char(11)||char(12)||char(13)||' ')) > 0)`
- 索引 `ix_parent_contact_logs_contacted_at` (contacted_at)
- 索引 `ix_parent_contact_logs_created_by` (created_by)
- 索引 `ix_parent_contact_logs_parent_id` (parent_id)
- 索引 `ix_parent_contact_logs_student_id` (student_id)

### audit_logs
- CHECK `ck_audit_logs_action`：`action IN ('create','update','archive','restore','status_change','delete')`
- 索引 `ix_audit_logs_actor_user_id` (actor_user_id)
- 索引 `ix_audit_logs_created_at` (created_at)
- 索引 `ix_audit_logs_entity_id` (entity_id)
- 索引 `ix_audit_logs_entity_type` (entity_type)

### notification_logs
- CHECK `ck_notification_status`：`status IN ('prepared','simulated','cancelled')`
- CHECK `ck_notification_channel`：`channel IN ('sms','email')`
- 索引 `ix_notification_logs_created_at` (created_at)
- 索引 `ix_notification_logs_created_by` (created_by)
- 索引 `ix_notification_logs_parent_id` (parent_id)
- 索引 `ix_notification_logs_student_id` (student_id)

## 6 Service 与 SQLite 兜底

validate_score_value 拒绝 bool、字符串、NaN、Infinity、越界，NULL 只表示单字段可空，不决定缺分提交或公式。User 角色依据 roles.name 检查，无固定 role_id。家长归属在 Service/ORM 校验，数据库触发器还阻止原始 SQL 跨学生绑定及改变已被历史记录引用的家长归属。

联系无 parent_id 时必须有去空白姓名；联系业务时间和 created_at 审计时间分别保留。NotificationLog.parent_id 非空时同样校验归属；接收对象使用独立 JSON 快照，家长后续联系方式变动不改旧通知。channel/status CHECK 不允许真实发送状态；模拟辅助只生成 simulated，无外部 API。

AuditLog 是多态追加日志；actor_user_id 可空用于系统初始化，entity_id 不是对单张业务表的 FK。JSON 快照递归移除密码哈希、密钥、token 等凭证，验证 JSON 与有限数值。ORM/触发器阻止修改删除既有审计。record_create/update/archive/status_change 只 add，无 commit；归档及状态函数只记日志，不执行实际业务变更。未来业务必须与审计同事务提交，阶段 7 增加管理员专用审计列表及脱敏详情。

SQLite 触发器清单：
- audit_logs_no_update
- audit_logs_no_delete
- parent_contacts_parent_insert
- parent_contacts_parent_update
- notifications_parent_insert
- notifications_parent_update
- parents_preserve_history_owner

## 7 初始化与迁移

工厂加载全部 metadata，绝不 create_all 或自动种子。显式执行 `flask --app run db upgrade`，初始 revision `fab16ef0dd6f`。迁移将时间类型写成标准 DATETIME，触发器 SQL 冻结在 revision 内，不从未来应用版本动态取定义。metadata after_create 同步安装触发器，仅供模型单测/明确建库调用。

`seed-roles` 幂等且按名字定位角色；`create-admin` 交互隐藏密码并确认，Werkzeug 哈希，无默认密码；`seed-demo` 需既有管理员，只用 DEMO 命名空间和虚构联系方式，不创建账号或真实通知。三命令由调用方事务一次提交，出错回滚，不覆盖已有业务数据。

[阶段2报告](../reports/stage2_report.md) 记录实际升级、测试和结构核对；业务页面/权限/成绩算法仍在后续阶段。

## 8 阶段 8 备份与恢复

13 张领域表、94 字段、20 个 RESTRICT 外键和 7 个触发器沿用原迁移。备份与恢复用 SQLite backup API，生成独立文件并检查 PRAGMA integrity_check、PRAGMA foreign_key_check、UTC 时间和 SHA-256。部署与快照命令见[备份与恢复](../deployment/backup_restore.md)。
