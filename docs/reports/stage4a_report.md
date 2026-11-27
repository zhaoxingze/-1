# 阶段4A交付报告：管理员基础档案管理

开发开始：2026-11-18；收尾日期：2026-11-19。范围：用户阶段4A完整指令。未进入阶段4B或阶段5。

## 1 实现功能与边界

| 档案 | 实际实现 |
| --- | --- |
| 学生 | 列表、学号/姓名/班级搜索、班级和归档筛选、分页、新增、详情、编辑、生日年龄计算、五条已定学籍迁移、归档/恢复确认及已归档查询 |
| 教师 | 编号/姓名搜索分页、新增、编辑、详情及当前班主任班级/课程只读分页；不创建账号、不修改角色 |
| 班级 | 名称/年级搜索分页、新增、编辑、详情、真实教师任班主任/更换、当前学生查询与人数（含全部学籍/归档） |
| 家长 | 学生详情联系方式、全局或按学生搜索分页、新增、编辑、详情、设置/取消主要联系人；多位家长、最多一位主要、允许零位 |

所有管理入口仅管理员。教师与学生管理GET/POST均拒绝，原登录/改密/三角色工作台和本人最小资料保留。无物理删除接口；学生以归档保留历史，归档/恢复不改学籍或User.is_active。新建学生固定enrolled；常规迁移仅enrolled→suspended/graduated/withdrawn、suspended→enrolled/withdrawn，终态无回流。

原 `/students` 保持404以保留旧接口与测试；新增管理页面统一 `/admin/students`、`/admin/teachers`、`/admin/classes`、`/admin/parents`。家长操作使用 `/admin/students/<student_id>/parents/...`，家长与路径学生不符404，不能改所属学生。课程、成绩、考勤、奖惩、家长联系记录CRUD、统计、审计查询和用户管理仍未实现。

## 2 开始前检查与保护

已检查指定README、需求/架构/数据库/假设/阶段2与3设计、阶段3报告、模型、服务、认证/管理员/学生模块和旧测试。阶段3基线实跑 **251 passed in82.28s**，见[基线日志](stage4a_baseline_pytest.txt)。

项目无Git。开发前生成工作区外167文件完整备份，ZIP CRC及逐项SHA-256通过，含开发库，位置和摘要见[备份记录](stage4a_backup.json)。私人备份不进入源码包。原Word、初始迁移、模型、旧测试文件、历史报告及开发库通过阶段前清单比对；最终结果见[冻结核验](stage4a_final_validation.json)。

记录并最小调整两项历史差异：原建议/students路径改为/admin管理路径，原状态图“状态码待定”文案按阶段2已定枚举修正。没有修改数据库字段来迁就新业务。

## 3 新增与修改文件

| 文件 | 作用 |
| --- | --- |
| `app/services/student_service.py` | 学生白名单、校验、唯一性、列表过滤、年龄、状态迁移、独立归档及审计 |
| `app/services/teacher_service.py` | 教师编号唯一、档案读写与审计 |
| `app/services/class_service.py` | 真实班主任关联、班级管理及当前学生人数 |
| `app/services/parent_service.py` | 学生归属、多位家长、主要切换与两侧审计 |
| `app/services/archive_common.py` | 再授权、字段/日期/主键验证、分页、显式快照、SQLite写锁与目标刷新 |
| `app/services/archive_references.py` | 按页面所需实体读取选择器ID/标签、教师关联分页 |
| `app/admin/archive_forms.py`, `archive_views.py` | 表单、解析真值确认、页面错误、分页/实体ID解析、路由统一事务 |
| `app/admin/student_routes.py`, `teacher_routes.py`, `class_routes.py`, `parent_routes.py` | 四类管理员页面与实际操作路由 |
| `app/templates/admin/` | 共用列表/表单/分页及四类详情、校验与确认页面 |
| `app/admin/__init__.py`, `routes.py` | 注册管理路由，管理员工作台增加真实入口 |
| `layout.html`, `dashboard/index.html`, `dashboard/workbench.html`, `app/static/css/app.css` | 保留原页面结构，增加有权导航、已开放卡片及移动端表格/表单布局 |
| 六个指定新增测试文件、`tests/archive_support.py` | 84项新测试与虚构数据/真实CSRF辅助；旧测试不修改 |
| README、需求/架构/假设、stage4a_design、实施计划、相关UML | 同步当前完成范围和4B边界 |

完整文件树见[项目树](stage4a_project_tree.txt)。requirements固定版本无变更，原认证及密码业务代码保持。

## 4 数据库、权限与输入校验

数据库仍为 **13领域表、94字段、20个RESTRICT外键、7个保护触发器**，初始revision `fab16ef0dd6f`，无新迁移。未清空、覆盖、重建或向默认开发库写入演示数据。[迁移检查](stage4a_migration_check.txt)无新升级操作，[pip check](stage4a_pip_check.txt)无依赖冲突。

每个管理路由role_required(admin)，读写Service再require_admin(actor)。学生管理还复用require_student_access；学生原最小读取入口不扩大到管理详情。所有状态变更请求有CSRF，GET确认页无副作用。普通学生编辑只提取原资料字段，不接受status/is_archived、role_id、User启停或审计操作人；身份始终来自服务器会话。

服务端检查必填/非空、原VARCHAR长度、真实日历日期、已有枚举和真实关联；学号/教师编号精确唯一。班级/班主任可空，非空须存在。性别自由文本，电话不强加全国格式，邮箱基础检查；未决定的年龄、未来日期与标识归一政策不擅自冻结。年龄仅计算，缺生日/未来生日显示“—”。LIKE搜索按字面转义，分页默认20/上限100；非法参数400、越界404，实体ID按SQLite正整数范围单独解析。

## 5 审计、事务与并发修复

新建/编辑四类档案、学籍、归档/恢复、主要联系人变更均复用audit_service；操作人取当前User，快照显式列领域字段，不包含密码/Token/密钥。Service仅flush/add，外层editor统一commit/rollback。业务成功但审计失败时全部回滚。

主要切换先旧主要false并flush，后新主要true并flush，两侧分别update审计；允许取消主要后零位。SQLite部分唯一索引不改。为防旧Session对象覆盖新状态，写服务在可变业务读取前BEGIN IMMEDIATE，复用已存在写事务并刷新目标；旧主要查询也刷新。锁由外层提交或回滚释放，不把SQLite方案宣称为其它数据库平台的锁实现。

真实故障注入用临时SQLite触发器阻止业务或审计INSERT，验证新增回滚；四类既有档案编辑的审计失败验证原字段/审计行数不变；主要切换失败验证原主要恢复。两个独立Session验证先毕业后旧会话休学被拒绝、主要联系人重新指定实际生效。

## 6 实际测试与失败记录

| 阶段 | 真实结果 | 证据 |
| --- | --- | --- |
| 原阶段3基线 | 251 passed in82.28s | [基线](stage4a_baseline_pytest.txt) |
| 初始缺功能 | 2 failed：管理表单404、Service缺失 | [红测](stage4a_red.txt) |
| 服务专项 | 13 passed | [服务记录](stage4a_services.txt) |
| 首批新增测试 | 71 passed，有19条WTForms弃用警告 | [首批](stage4a_first.txt) |
| 处理警告 | 警告提升为错误先复现，再采用已安装库SelectChoice | [复现](stage4a_warning_red.txt) |
| 首次完整集成 | 328 passed in109.17s，无警告 | [集成](stage4a_integration.txt) |
| 审查问题复现 | 6 failed、1 passed | [修复前](stage4a_review_red.txt) |
| 修复后受影响专项 | 76 passed in27.11s | [专项](stage4a_review_green.txt) |
| 修复后完整回归 | **335 passed in106.89s**，旧251+新增84，无删除/跳过/降低旧断言 | [全量](stage4a_pytest.txt) |

[独立初审](stage4a_independent_review.md)发现1项Critical、3项Important、3项Minor：旧会话逆转学籍终态、主要设置未生效、false确认被接受、家长搜索丢失学生范围、选择器三表全量加载、空班级筛选异常、实体ID误用分页上限。均已处理：写锁/刷新、确认真值、保留选择器、按实体读标签列、空值归一、分开ID解析。复现测试先失败后通过；初审报告保留当时发现，未冒称审查者已给出修复后独立结论。具体修复依据为上述专项/全量和浏览器结果。

新增六文件覆盖用户列出的25类验收事项：创建/重复/必填/日期/关联、编辑、状态、归档历史/账号、班主任、家长唯一主要、角色/IDOR/CSRF、服务再授权、事务/审计回滚与原认证回归。工作区外解压源码、新建独立虚拟环境并重新安装固定依赖后，全量实际为 **335 passed in202.51s**，pip check通过；运行源文件未变。详细结果见[解压验证](stage4a_extracted_validation.json)和[解压测试日志](stage4a_extracted_pytest.txt)。

## 7 实际运行与截图

项目.venv实际启动Flask，临时库执行原迁移，三角色账号使用临时随机密码，仅存在工作区外验证库；默认开发库不参与交互。Playwright真实填写和提交教师/班级/学生/家长表单，验证新增编辑、必填与重复失败、班主任、班级学生、合法迁移、归档/恢复、已归档搜索、主要切换、学生筛选保留及分页；教师/学生管理403、学生本人最小200/他人403、匿名管理302与health200。浏览器page errors/非预期console errors/服务端500均为空。

[浏览器结果](stage4a_browser.json)、[脱敏交互](stage4a_browser.txt)。12张真实截图已保存，重点如下；移动端390宽列表内部横向滚动、页面无横向溢出，主要表单可操作。

- [管理员入口](../../output/playwright/stage4a-admin-dashboard.png)
- [学生列表](../../output/playwright/stage4a-students-list.png)、[学生详情与家长](../../output/playwright/stage4a-student-detail.png)
- [教师关联](../../output/playwright/stage4a-teacher-detail.png)、[班级学生](../../output/playwright/stage4a-class-detail.png)
- [家长列表](../../output/playwright/stage4a-parents-list.png)、[主要联系人](../../output/playwright/stage4a-parent-detail.png)
- [必填错误](../../output/playwright/stage4a-student-form-error.png)、[重复学号](../../output/playwright/stage4a-duplicate-student-error.png)、[归档确认](../../output/playwright/stage4a-archive-confirmation.png)
- [移动列表](../../output/playwright/stage4a-mobile-students.png)、[移动表单](../../output/playwright/stage4a-mobile-student-form.png)

临时浏览器/服务器验收后关闭，不作为持续运行服务。用户在原项目或解压源码新环境按README创建自己的管理员并运行。

## 8 UML与实现对应

七类源共十个图块，[语法验证](stage4a_uml_syntax.txt)与[渲染验证](stage4a_uml_render.txt)退出码0。UC-02顺序/通信/活动同步为实际表单→Service写锁/校验→Student flush→audit add→路由一次提交/回滚，编号一致。类图保留13持久化类94字段20FK，新增无表的四档案模块与公共策略依赖；用例图标注管理员已实现与教师4B目标。学籍五边不变，补独立归档图；ER无结构变化。阶段3认证图保留，不把课程成绩等未来用例标为完成。

## 9 源码交付与完整性

源码包保留app、依赖、迁移、全部测试、设计文档/原Word/UML、报告和截图；仅保留instance/.gitkeep，不含开发数据库、私人备份、.venv、缓存、.env、密钥、临时账号凭据、旧ZIP或真实业务个人数据。测试中的固定字符串只供临时数据库，不是可登录的交付账号。

解压源码在工作区外用新虚拟环境安装固定依赖并执行完整pytest；最终运行源文件SHA与被测解压文件一致。包内manifest与外部SHA、CRC、解压逐项摘要、文件排除规则及本地Markdown链接核验见[打包核验](stage4a_package_validation.json)。

## 10 阶段4B待决与停止点

- A-04/A-05：负责学生集合、教师各字段读写与跨班/跨课程权限；目前管理默认拒绝。
- A-10/A-21/A-22：换班/换教师后的历史访问、教师新增选课范围；当前模型仍只有当前关系。
- A-20：历史状态初始导入、毕业/退学纠错等例外，不能借“恢复档案”实现学籍回流。
- A-16及A-02/A-06/A-03/A-15：标识归一/日期业务范围、成绩权重和缺分、统计口径仍待后续阶段。

本阶段不新增删除、账号创建/停用联动、真实通知或用户CRUD。SQLite写锁可在锁竞争时返回受控失败并回滚；没有宣称完成生产多实例部署或中心会话撤销。阶段1已登记的同进程logger级别共享仍为非阻断限制。

完成4A后停止。后续仅在用户指令下先确认教师范围，再进入4B；不自动进入阶段5。
