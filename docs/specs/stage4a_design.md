# 阶段4A 基础档案实施设计

日期2026-11-18。依据本次完整任务、阶段2冻结决策、阶段3认证及现有状态图。采用既有Flask/Jinja/Bootstrap/ORM结构；无数据库迁移。由实现者在用户授权范围内确定以下接口与技术细节。

## 基线与差异

开始前pytest为251 passed in82.28s。项目无Git；阶段前167文件完整ZIP及逐文件SHA保存在工作区外，位置见stage4a_backup.json，包含私人开发库的备份绝不进入源码交付。旧测试文件、模型、初始迁移、原Word、历史报告和开发库冻结比对。

旧测试要求 `/students` 保持404，原架构路径只是建议。新增管理页面使用 `/admin/students`、`/admin/teachers`、`/admin/classes`、`/admin/parents`，全部管理员专用；原 `/students/<id>/profile`及三角色页面保持。学生/教师无管理读写权限。原状态图“英文码未定”说明已落后于阶段2，修正文案，不改变迁移。

## 数据与业务边界

学生创建默认enrolled、未归档；普通编辑不接受status/is_archived/User字段。学籍专用操作仅enrolled→suspended/graduated/withdrawn、suspended→enrolled/withdrawn，毕业/退学无常规后继。历史状态初始导入、例外纠错留4B。归档/恢复独立专用确认表单，无删除或账号联动；不因归档新增状态限制。

Teacher、SchoolClass、Parent沿用原字段。教师创建不建账号。班主任可空且非空须真实教师；学生班级可空。班级人数统计当前关联学生（包含归档及所有学籍），明确标注，不宣称历史统计。教师详情只读列出当前班主任班级和课程，不提供课程维护。四类均无物理删除接口；本次明列功能中的学生归档替代删除，其他对象的删除不在本次清单。

家长列表可全局按学生/姓名/电话搜索分页，并在学生详情查看。新增/编辑/详情/主要联系人切换使用学生嵌套路径；既有Parent不能改所属学生，路径两ID不匹配404。每生最多一主要联系人，允许零位。切换先将原主要设false并flush，再设新主要true；两侧变更分别审计，外层一次commit，失败全部回滚；不重设计部分唯一索引。取消主要可通过编辑取消勾选。

服务端必填去空白检查、类型及原VARCHAR长度、真实日历日期和关联存在性；gender保持自由文本，电话不强加全国格式，邮箱只作无空白且单@的基础检查。学号/教师编号按现有大小写及原字符串精确唯一，不擅自统一大小写或修剪标识；空白标识拒绝。日期未来值及业务年龄门槛仍未定，年龄根据生日按当日计算，缺失或未来生日显示“—”，不存age。

列表q按字面子串匹配（LIKE通配符转义），学生另有班级、归档筛选；默认未归档，可切换已归档/全部。教师/班级/家长同样搜索与分页，默认20、上限100、非法参数400、越界页404（空结果第一页正常）。固定主键排序，保留筛选参数。管理详情、关联列表分页，表格移动端横向滚动。

## 服务与事务

新增archive_common.py及student_service/teacher_service/class_service/parent_service.py。读写服务均重新require_admin(actor)，写服务使用字段白名单、关联校验、ORM与现有审计；只flush/add不commit。共用get_record拒绝非法/超大主键。audit快照为显式领域字段，不序列化User或认证凭据。

接口：create_*(actor,data)、update_*(actor,id,data)；学生change_student_status(actor,id,target)、set_student_archived(actor,id,archived)；家长create_parent(actor,student_id,data)、update_parent(actor,student_id,parent_id,data)、set_primary_parent(actor,student_id,parent_id)。list_*(actor,...)返回分页对象；get_*均管理员检查；所有对象查询和修改以服务器认证actor为依据。

路由模块位于app/admin/，复用role_required，路由统一commit/rollback。校验错误回显表单字段、重复标识显示友好冲突，数据库/审计失败回滚并用固定日志码记录，不向页面或日志泄露SQL参数。状态变更、归档、恢复和主要联系人均GET展示确认、POST+CSRF执行，普通GET无副作用。

## 验证与交付

新增六个指定测试文件，真实CSRF与隔离SQLite，覆盖合法/非法状态、历史保留、账号独立、多家长/主要切换、路径IDOR、服务再次授权、数据库/审计失败回滚、搜索/分页/输入与旧251回归。更新实际受影响UML及设计；独立审查、真实浏览器管理员成功/失败和教师/学生拒绝、移动端、pip/db check。源码ZIP显式排除环境/缓存/本地库/凭据/旧ZIP，解压后实际安装依赖并运行全套，证明可复现。完成后停在4A。

## 审查后技术补全（2026-11-19）

所有档案写服务经archive_write先取得SQLite BEGIN IMMEDIATE写锁，复用已有写事务，目标刷新populate_existing；主要联系人查询也刷新旧主要。解决独立双Session复现的终态逆转和主要设置未生效，锁由外层提交/回滚释放。服务仍不commit、数据库结构不改。分页上限与实体主键上限分别解析；空班级筛选表示全部。reference_options按实体只选ID/标签列，嵌套家长列表无多余选择器查询。

ConfirmForm用DataRequired验证解析后的bool真值，confirm=false及缺少确认均不能归档/恢复/切换主要。全局家长查询始终保留学生选择器及选中值；嵌套URL的学生归属保持固定。具体红绿证据与335项回归见最终报告。
