# 阶段 3 交付报告：用户认证与 RBAC

日期：2026-11-17。范围：用户阶段3完整任务、原Word阶段3、阶段2冻结决策。当前完成认证及权限基础设施，不进入完整业务CRUD。

## 1 阶段目标与开始前审查

已阅读README、配置/启动/依赖、工厂与扩展、CLI、认证/管理员/工作台、模型、现有服务及测试、设计基线、历史报告、七类UML和原Word。原Word明确阶段3还包含本人改密与管理员重置，因此在认证范围内一并实施；本次没有实现其他用户管理CRUD。原架构建议/auth/login与阶段1保留的404测试有差异，采用本次建议/login，不增加旧地址别名。

先在项目Python3.12.10虚拟环境执行依赖安装、db check和pytest，真实基线 **156 passed in29.26s**，无结构升级差异。原始Word、迁移、历史报告、旧测试及开发库摘要在开发前保留；项目无Git仓库，使用阶段前副本、SHA-256及实施计划记录变更，不初始化Git或重建项目。

复用User/Role/Student/Teacher、角色档案验证、Flask-Login、Werkzeug哈希、Flask-WTF、追加审计及现有模板。13领域表/94字段/20个RESTRICT外键、7个SQLite触发器与初始revision `fab16ef0dd6f`保持。

## 2 实际完成内容

| 功能 | 实际结果与边界 |
| --- | --- |
| 登录 | GET/POST `/login`；精确用户名、Werkzeug哈希、统一失败提示、停用/无效档案拒绝、真实CSRF、安全next |
| 退出 | `/logout`仅POST；CSRF校验；清会话后返回登录，GET返回405 |
| 会话 | 每请求当前账号、角色及绑定检查；绝对30分钟、不滑动、无remember-me；改密/停用/删除/角色绑定变化失效；登录清旧状态 |
| RBAC | `role_required(*roles)`支持多角色、按角色名称，未登录302、无权403，拒绝URL及参数伪造 |
| 对象权限 | `can_access_student_resource` / `require_student_access`；学生本人、管理员按原矩阵、教师未决范围与未知action拒绝 |
| 三角色入口 | `/dashboard`分流至管理员`/admin/`、教师`/dashboard/teacher`、学生`/dashboard/student`；跨角色403 |
| 本人资料 | `/profile`按服务端身份展示；最小学生资料`/students/<id>/profile`仅姓名/学号/学籍/归档，不暴露家长或住址等 |
| 本人改密 | `/password/change`验证旧密码、确认新密码、哈希替换、update审计、成功后退出 |
| 管理员重置 | 从工作台进入`/admin/password-reset`按用户名查找，再进入目标表单；验证管理员本人密码；目标旧会话失效，不联动停用/学籍/归档 |
| 页面与错误 | 沿用Bootstrap和403/404/500；导航显示本人/POST退出；未开发卡片标明待开发；认证/私有响应no-store |

密码重置目标表单为`/admin/users/<user_id>/reset-password`。这些是认证操作，不提供账号列表、创建/改角色/停用Web管理。管理员对未找到的授权对象404；学生访问他人或无权且不存在的ID统一403。超过SQLite整数范围的管理员资源ID404。

## 3 代码变更与文件作用

| 新增/修改 | 文件 | 作用 |
| --- | --- | --- |
| 新增 | `app/auth/session.py` | 加载有效用户、绝对期限/HMAC版本、站内重定向、缓存限制及空库旧Cookie处理 |
| 新增 | `app/auth/forms.py` | 登录、改密、管理员查找和重置表单，服务端校验与CSRF |
| 新增 | `app/auth/routes.py` | 登录/POST退出/本人改密；密码事务提交和回滚 |
| 新增 | `app/services/permission_service.py` | 统一角色装饰器、角色及学生资源action授权 |
| 新增 | `app/services/password_service.py` | 改密/重置与同事务审计，只改对象及add、不commit |
| 新增 | `app/admin/routes.py` | 管理员工作台、账号查找及二次验证重置 |
| 新增 | `app/students/routes.py` | 最小授权学生资料读取，无CRUD |
| 修改 | `app/models/user.py` | 复用原8字段，接入UserMixin并用user_id实现get_id，不改DDL |
| 修改 | `app/__init__.py`, `config.py` | 注册真实认证加载/上下文，开发/测试/production会话配置 |
| 修改 | `app/auth/__init__.py`, `app/admin/__init__.py`, `app/students/__init__.py` | 导入路由，auth使用根路径 |
| 修改 | `app/dashboard/routes.py` | 保留公共页/health，新增角色分流及本人资料 |
| 新增/修改 | `app/templates/auth/`, `app/templates/dashboard/`, `layout.html`, `app/static/css/app.css` | 登录/改密/重置/角色页面及响应式导航 |
| 新增 | `tests/test_auth_login.py`, `test_auth_logout.py`, `test_auth_session.py`, `test_auth_security.py`, `test_auth_passwords.py`, `test_rbac.py`, `test_object_permissions.py` | 95项认证、越权、密码与安全回归 |
| 修改 | `tests/conftest.py` | 仅增加隔离认证fixtures；原fixture及旧测试断言保留 |
| 更新 | `README.md`, 需求/架构/假设、认证设计、4类UML及UML索引 | 与实际接口、权限和完成范围一致 |

没有修改requirements固定版本、数据库字段、外键/唯一约束、初始迁移、审计Action枚举或真实通知能力。[完整项目树](stage3_project_tree.txt)；[认证设计](../specs/stage3_auth_rbac_design.md)；[实施计划与记录](../superpowers/plans/2026-11-17-phase3-auth-rbac.md)。

## 4 安全与事务设计

密码使用现有Werkzeug哈希机制，密码输入不回填HTML、不记录到普通日志，Cookie不含密码、哈希或可作为授权依据的角色参数。不存在用户执行随机虚拟哈希校验，失败文本统一。next只允许经多次解码后仍安全的站内路径，拒绝外部主机、反斜杠、控制字符及登录/退出回环，不信任Host头生成目标。

会话签名、fresh状态、浏览器身份、绝对时间、当前User.is_active与角色档案校验、HMAC凭据版本同时约束恢复。本人改密或管理员重置改变版本，旧Cookie不能继续认证；归档/毕业仍可按有效账号登录。开发/测试HttpOnly+SameSite=Lax，production额外Secure且必需环境SECRET_KEY；保持各环境CSRF启用，测试密钥不用于生产。

角色授权取数据库名称，测试使用17/29/43等非固定ID。学生资源只认绑定student_id；教师不默认获得全校数据。最小路由先授权再查询，避免外部对象存在性探测。SQLAlchemy参数化查询、已有角色档案ORM约束及数据库触发器继续生效。

密码服务与现有审计均无内部commit；路由一次提交/失败回滚。审计只记录action=update及`operation=self_change/admin_reset, changed=true`，不含旧/新密码或哈希。原脱敏器会清理含password的键，故使用不含凭据的操作标记，不削弱原规则。登录/失败/退出只使用固定安全日志，不扩大审计事件枚举。

## 5 自动化测试与审查修复

| 验证 | 真实结果 | 证据 |
| --- | --- | --- |
| 开始前阶段2基线 | 156 passed in29.26s | [基线日志](stage3_baseline_pytest.txt) |
| 首次完整集成 | 247 passed in67.60s | [集成日志](stage3_integration_first.txt) |
| 独立审查问题复现 | 4 failed（按预期复现） | [修复前](stage3_review_red.txt) |
| 同组修复后 | 4 passed in1.91s | [修复后](stage3_review_green.txt) |
| 最终完整回归 | **251 passed in71.85s**，含旧156与新增95，无跳过 | [完整日志](stage3_pytest.txt) |
| 依赖检查 | No broken requirements found | [pip check](stage3_pip_check.txt) |
| 迁移对照 | No new upgrade operations detected | [db check](stage3_migration_check.txt) |
| 七源/九图PlantUML | 语法通过，认证顺序/活动/类图渲染并目视查看 | [语法结果](stage3_uml_validation.txt)、[渲染结果](stage3_uml_render.txt) |

新增测试覆盖正确/错误/不存在/停用账号、CSRF、登录清旧会话、30分钟及异常时间/身份/版本、Cookie篡改、浏览器身份变化、停用/删除/改密/角色变化失效、编码重定向、动态角色ID、多角色装饰器、参数伪造、学生越权、教师默认拒绝、对象不存在、密码确认、二次验证、脱敏与同事务回滚。

[独立审查](stage3_independent_review.md) 原结论With fixes：1项Important是旧有效Cookie加未初始化身份库使公共首页异常；已先复现后修复为匿名回退，缺失SQLite文件不打开连接建库。另2项Minor为超大ID异常及通用架构事务文案；已处理为404并统一“外层编排方一次提交”。审查报告保留当时发现，后续修复证据在本报告，不冒称独立复审已给出新结论。

开发中的首次失败日志保留，包括缺路由红测、测试先拆绑定触发autoflush、非ASCII版本比较异常；均定位并修复，没有删减旧测试。最终结果以stage3_pytest为准。[最终结构、文件摘要及链接核验](stage3_final_validation.json) 记录所有冻结比对。

## 6 真实运行与截图

使用项目.venv实际启动Flask，监听本机5063，DEBUG关闭；验证库位于临时目录，执行原迁移后创建虚构三角色账号、随机临时密码及同事务审计。没有向默认开发库写入账号，也没有交付可登录密码。

Playwright真实填写表单、点击登录/退出、查看三角色工作台和个人资料，管理员账号查找进入重置表单。三角色非本人工作台403，学生本人资料200、其他对象403，退出后受限页302登录；首页、登录页和health200。移动端390宽无横向溢出；浏览器page errors、console errors、服务端500均为空，服务器日志无未处理异常。见 [浏览器结构化结果](stage3_browser.json) 和 [脱敏交互记录](stage3_browser.txt)。

六张实际截图均已查看：

- [系统首页](../../output/playwright/stage3-homepage.png)
- [桌面登录页](../../output/playwright/stage3-login.png)
- [移动登录页](../../output/playwright/stage3-login-mobile.png)
- [管理员工作台](../../output/playwright/stage3-admin-dashboard.png)
- [教师工作台](../../output/playwright/stage3-teacher-dashboard.png)
- [学生工作台](../../output/playwright/stage3-student-dashboard.png)

验收后关闭本次临时服务器及浏览器；用户按README启动本地项目，不依赖临时验证库。

## 7 遗留事项与明确未实现

本阶段验收项已满足，无已知阻断问题。以下仍是范围边界：

- 教师跨班/跨课、历史权限、可编辑字段、家长/奖惩访问及新增选课范围待A-04/A-05/A-10/A-12/A-21/A-22决定，当前默认拒绝。
- 学生/教师/班级/家长CRUD、课程/成绩/考勤/奖惩/沟通CRUD、账号列表/停用/改角色、审计查询、首页统计、真实短信邮件均未实现。
- 成绩权重/缺分、统计口径、用户名归一、密码复杂度/强制首次改密等业务政策没有擅自决定。
- 签名Cookie退出清当前浏览器；复制Cookie的中心即时撤销不具备，后续如要求跨设备撤销需服务端会话方案；密码变化能使旧凭据版本失效。30分钟上限、无remember-me的选择详见认证设计。
- 阶段1记录的同进程app.logger级别共享仍为非阻断限制；生产WSGI/HTTPS部署、限流及集中会话不属于已交付功能。

## 8 下一阶段与交付

建议下一阶段先明确教师档案字段/数据范围，再从管理员学生、班级、教师基础档案CRUD开始；每项接入现有权限服务、字段白名单、关联校验、同事务审计和越权回归。未确认教师范围前继续拒绝对应操作。成绩模块实施前先确定权重、缺分和舍入策略。

重要修改说明见 [important_changes.md](important_changes.md)，ZIP含说明、当前设计、UML、最终证据及截图，排除虚拟环境、缓存、数据库和凭据。停止于阶段3，等待下一阶段指令。
