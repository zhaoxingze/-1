# UML源文件索引

版本0.7，更新2026-11-19。UTF-8 PlantUML源为维护依据，共七类源、二十六个图块；原Word图号和原需求编号保持可追踪。阶段0–3历史见各阶段报告，管理员档案范围见[阶段4A设计](../specs/stage4a_design.md)，教师范围见[阶段4B报告](../reports/stage4b_report.md)。

| 源 | 内容与对应实现 |
| --- | --- |
| [usecase.puml](usecase.puml) | 原图5-1；UC-01/11认证、UC-10账号管理、密码重置及审计查询、UC-09最小本人资料和管理员UC-02/03/12/13已实施；其余目标及教师4B范围明确标记 |
| [class_diagram.puml](class_diagram.puml) | 原图5-2及阶段2字段；13持久化类94字段20FK不变，UserMixin、认证及四档案服务/共用策略均无表，虚线仅代码依赖 |
| [sequence_diagram.puml](sequence_diagram.puml) | UC-02实际新增学生事务；第二块保留阶段3认证顺序 |
| [communication_diagram.puml](communication_diagram.puml) | 原图5-4对象通信；与UC-02顺序图参与者、主编号及A/E错误分支一致 |
| [state_diagram.puml](state_diagram.puml) | 原图5-5五条学籍迁移，代码值按阶段2；第二块为独立归档/恢复，不改变学籍/账号 |
| [activity_diagram.puml](activity_diagram.puml) | UC-02实际表单、校验、写锁、业务/审计与统一提交回滚；第二块保留认证活动 |
| [er_diagram.puml](er_diagram.puml) | 13表94字段20外键，全部RESTRICT；本阶段无结构变更，源文件保持 |

## 事务与权限对应

Controller为admin Blueprint及archive_views.editor，四个Service为实际Python模块；没有强制增加Repository层。新增学生服务先检查actor及SQLite写锁，校验字段/班级/唯一性，flush取得主键，add审计，然后路由统一commit；任何业务/审计/提交失败均立即转完整rollback。Service无commit。

写服务BEGIN IMMEDIATE并刷新目标，解决旧会话逆转终态或主要设置无效；主要切换同锁内先降旧并flush，再升新、审计两侧。字段与关系仍遵守[数据库设计](../specs/database_design.md)。无删除级联、无教师全校访问、无学生管理写权。阶段 6 已开放考勤统计、奖惩、家长联系及模拟通知。阶段 7 补齐账号管理、只读审计和三角色聚合。

## 验证与维护

本地PlantUML 1.2025.10执行七源语法检查、受影响图渲染，实际命令结果见[语法记录](../reports/stage4a_uml_syntax.txt)与[渲染记录](../reports/stage4a_uml_render.txt)。未上传在线渲染服务。业务状态或规则变化时同时修改需求、架构、假设、受影响图及测试，语法通过不能替代业务验收。

阶段 4B 更新用例图和类图，并在顺序图、通信图追加教师联系方式编辑流程。新增当前教师身份、班级与课程范围查询、名单投影和锁内再授权。详见[教师权限规则](../specs/stage4b_permissions.md)和[阶段4B报告](../reports/stage4b_report.md)。

阶段 5 更新用例图和类图，分别在顺序图、通信图补充 UC-05，并在活动图补充 UC-04 和 UC-05。新增重复选课、非法成绩、越权和回滚分支。ER 图保留阶段 2 的冻结快照。[阶段 5 验收报告](../reports/stage5_report.md)

阶段 6 用例图明确考勤、奖惩、联系和模拟通知的角色。类图增加 StudentRecordScope 与共用服务。新顺序图覆盖考勤和其他记录写入，通信图展示锁内授权及同事务审计，活动图展示考勤汇总、零分母、奖惩、联系与显式模拟分支。[阶段 6 UML 及验收证据](../reports/stage6_report.md)

阶段 7 新增账号和审计顺序图、统计通信图及两份活动图，覆盖会话版本、末位管理员、非法输入、脱敏与权限范围。类图增补服务依赖，持久化实体沿用。[阶段 7 报告](../reports/stage7_report.md)

阶段 8 对全部七份源文件重新检查并渲染，校准账号活动图中密码哈希与 SQLite 写锁的顺序。字段、关系和既有授权范围沿用。[语法记录](../reports/stage8_uml_syntax.txt) · [渲染记录](../reports/stage8_uml_render.txt)
