# Phase 3 Authentication and RBAC Implementation Plan

> **For agentic workers:** Use superpowers:executing-plans to implement task by task with TDD and one final independent review. Steps use checkbox syntax.

**Goal:** 完成可运行的三角色认证、最小对象权限和原案密码管理。
**Architecture:** 沿用现有工厂、七 Blueprint、Flask-Login 和签名 Cookie；统一权限服务默认拒绝，密码服务与现有审计同事务。
**Tech Stack:** Python 3.12.10 / existing pinned Flask stack / pytest / SQLite。
**Spec:** [认证设计](../../specs/stage3_auth_rbac_design.md)；用户阶段3附件为最终范围依据。

## Global Constraints

- 保留 13 表 / 94 字段 / 20 RESTRICT 外键 / 7 触发器 / revision fab16ef0dd6f。
- 原 156 项测试不删、不跳过、不降低断言；默认开发库不改；所有新测试与浏览器使用临时库。
- 无默认账号；无业务 CRUD、成绩计算、真实通知；教师未决范围默认拒绝。
- 原 Word、阶段 1/2 报告保留；最终交付 ZIP 不含数据库、环境、凭据。

## Review Focus

1. 百分号编码、反斜杠和控制字符不能把 next 变为外部地址。
2. Cookie 不能保存哈希/密码，旧会话不能在停用、改密或变更角色后继续使用。
3. Flask 扩展全局对象不能让多工厂、CSRF 或未初始化库的公共页面回归。
4. 学生 ID URL 与前端角色参数不能放大权限；教师“负责”不能自动扩成全校。
5. 改密/重置失败必须回滚同事务审计，错误页及普通日志不能泄露凭据。

## Task 1: Authentication

Files: app/auth/{forms,routes,session}.py, app/models/user.py, app/__init__.py, config.py; tests/test_auth_{login,logout,session,security}.py；tests/conftest.py 仅新增 fixture。
Interfaces: User.get_id()；configure_auth(app) 注册 loader/未登录行为；GET/POST /login、POST /logout；会话 HMAC 版本和 30 分钟绝对期限。

- [x] 阅读原案、代码、现有测试；pip install / db check / pytest 基线。
- [x] 新增隔离账号 fixtures 与认证测试，观察真实缺功能失败并保存日志。
- [x] 实现 UserMixin、表单、登录/退出与 loader；不新增表或依赖。
- [x] 认证专项通过，记录实际结果。

## Task 2: RBAC and pages

Files: app/services/permission_service.py, app/admin/routes.py, app/students/routes.py, app/dashboard/routes.py, templates/auth/*, templates/dashboard/*, layout.html, css；tests/test_rbac.py / test_object_permissions.py。
Interfaces: role_required(*roles)；can_access_student_resource(user,student_id,*,action='read_profile') -> bool；require_student_access 同签名；角色工作台与本人资料。

- [x] 角色矩阵及学生越权测试先红后绿。
- [x] 实现默认拒绝的权限接口、最小资料读取与真实角色页面。
- [x] 验证未知 action、未登录、动态角色 ID、伪造参数及对象不存在响应。

## Task 3: Password management

Files: app/services/password_service.py, app/auth/routes.py, app/admin/routes.py, forms/templates；tests/test_auth_passwords.py。
Interfaces: change_own_password(actor,current_password,new_password)；reset_user_password(actor,target_user_id,actor_password,new_password)；服务不提交，路由统一事务。

- [x] 本人旧密码、管理员二次验证、越权、审计脱敏与回滚测试先红后绿。
- [x] 实现改密及重置，旧会话 HMAC 失效；不更改状态或档案。
- [x] 专项与完整 156 项回归通过。

## Task 4: Integration, design and delivery

Files: README.md, specs/requirements/architecture/assumptions, docs/uml, docs/reports/stage3_*, output/playwright, output/delivery。

- [x] 临时迁移库真实运行浏览器登录/退出、三角色与 403；保存截图与结果。
- [x] 更新设计及 UML，检查全部语法；独立审查并处理实质问题。
- [x] 最终全量 pytest / pip check / db check / 结构和哈希核验。
- [x] 完成交付报告、目录树、重要修改说明 ZIP 并检验内容与 SHA-256。

## Ledger / Rulings

- 2026-11-17 Baseline: 156 passed in 29.26s; db check no new upgrade operations.
- 无 Git 仓库，按用户指定当前目录直接实施，不初始化 Git/分支；以阶段前 SHA-256 清单和本计划记录替代 Git diff/commit。
- 用户完整指令已给出栈、实现顺序及安全最小化授权，不增加重复审批；未决业务范围采用默认拒绝。
- Task 1→2: current_user + get_id 为统一身份接口；Task 1→3: session credential HMAC 使密码变化失效；Task 2→3: role_required('admin') 保护重置路由，服务仍校验 actor。无接口冲突。
- 原架构建议 /auth/login 与阶段1旧测试404冲突：使用本次建议 /login，保持旧 /auth/login 不暴露。
- 原 Word 明确阶段3本人改密/管理员重置，本次附件未列完整密码管理任务但未禁止；最小实现并审计，其他用户 CRUD 保持未实现。

- Task 1/2: 初始6个路由契约失败后实现认证/权限；首次专项75通过1失败（新测试先拆档案再查Role触发autoflush，调整查询顺序后通过，未改旧测试）。
- Task 3: 密码路由404红测后实现；31项密码/会话测试通过。非ASCII版本TypeError及管理员查找页404红测后修复；审计标记采用changed/operation，保留原脱敏规则。
- Tasks 1–3 integration: 247 passed in67.60s。
- Final review: Important旧Cookie+未初始化库导致公共页异常；2项Minor为超大ID与事务文案。4个复现测试先4failed再4passed in1.91s；处理所有发现，未保留未修审查项。
- Final full suite: 251 passed in71.85s；pip check无冲突；db check无新升级操作。
- 浏览器：独立真实迁移临时库，三角色工作台、登录/POST退出、403、学生本人200与他人403、移动端无溢出通过；无page/console/server错误。6截图逐张查看。
- UML：7源文件含9图语法通过，认证顺序/活动/类图已渲染查看；源Word/迁移/旧测试/开发库冻结及ZIP清单另见最终验证报告。
- Review Declined rulings: 密码复杂度、教师业务范围、集中Cookie撤销及未来UC-02不扩展，属于明确范围边界，风险与待决记录已保留；主执行者负责浏览器/UML/ZIP/开发库最终核验，另存实际证据。当前项目无Git，保留计划与报告作为进度账，不删除记录。

- Delivery complete: 55份说明材料ZIP已通过CRC、逐项解压SHA-256、独立Markdown链接及临时凭据排除检查；打包核验见docs/reports/stage3_package_validation.json。临时浏览器已关闭，5063端口无监听。
