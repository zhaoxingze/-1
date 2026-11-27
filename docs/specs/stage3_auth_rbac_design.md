# 阶段 3 认证与 RBAC 设计

日期：2026-11-17。依据用户阶段 3 完整任务、原 Word 阶段 3、阶段 2 决策及现有需求矩阵。本文件中的技术默认值是本阶段最小实现选择，不替代待决业务规则。

## 范围与复用

复用 User/Role/Student/Teacher、Flask-Login、Werkzeug、Flask-WTF、角色档案校验及追加式审计。实现登录、POST 退出、会话失效、三角色工作台、本人基础资料、统一角色和对象授权。原 Word 还明确要求本人改密及管理员重置密码，故纳入认证范围；不增加账号列表、账号创建或停用 Web CRUD。

13 表、94 字段、20 外键、7 触发器、初始 revision 均保持；开发数据库只读检查。所有账号交互验证使用独立临时库。原 156 项测试文件保留，公共首页及 health 不要求数据库已初始化。

## 技术选择与替代方案

使用已经安装的 Flask-Login + Flask 签名 Cookie 会话，沿用 Jinja2 页面。自行实现认证重复框架能力；新增服务端会话表或外部 Redis 超出当前结构与单机范围，因此不采用。当前选择依据用户指定栈和“最小化、可测试”的授权，无需新增依赖。

- `/login` GET/POST，`/logout` 仅 POST。auth Blueprint 使用根前缀，旧 `/auth/login` 仍不存在，以保留旧测试及本阶段建议地址；架构原地址是建议而非既有功能。
- 用户名按原始大小写精确匹配，不自行 trim/casefold；与现有数据存储语义一致。表单长度 1–50，密码输入 1–1024，保留密码空格，不发明复杂度规则。
- 所有认证失败统一“用户名或密码错误，或账号不可用。”；不存在的账号也执行随机虚拟哈希校验。日志只记录固定事件代码和成功后的用户主键，不含输入用户名、密码、哈希、Cookie 或 next。
- 仅接受以单个 `/` 开始的站内 next，拒绝 scheme、netloc、反斜杠、控制字符及其百分号编码变体；拒绝登录/退出回环。无效值回到 `/dashboard`。请求 Host 不用于决定可信重定向目标。
- 登录成功先清空旧会话，再建立新认证状态；不启用 remember-me。会话绝对上限 30 分钟，不因访问续期。签名内仅存身份 ID、认证时间及 HMAC 凭据版本，不存角色授权结果或密码哈希。
- 每次认证加载读取数据库中的账号启停、角色和档案绑定。停用、删除、密码变化、角色/绑定变化、无效会话时间立即拒绝。HMAC 版本由服务端密钥与当前数据库字段计算，无新增字段。毕业、休学、归档不影响有效账号登录。
- 旧Cookie指向未初始化/不可用身份库时按匿名处理并清会话，不让公共首页因身份恢复失败而崩溃；SQLite文件不存在时不打开连接建空库。超出SQLite整数范围的管理员资源URL按不存在返回404。
- HttpOnly、SameSite=Lax；开发/测试允许 HTTP，production 强制 Secure 且要求环境 SECRET_KEY。测试密钥不用于生产。保持 CSRF 启用；认证和私有响应使用 no-store。
- 签名 Cookie 不能单独撤销一份已被复制的旧 Cookie；退出清理当前浏览器会话，改密使既有凭据版本失效。跨设备即时退出及中心会话撤销不在本阶段实现，生产多实例需共享稳定密钥，后续如要求中心撤销需单独设计。

## 权限与最小资料范围

`role_required(*roles)` 同时检查认证与角色名，支持多角色，未登录跳转登录、已登录无权 403。工作台为各角色专属，管理员不自动进入教师/学生工作台。`/dashboard` 分流；`/profile` 从 current_user 取本人。

`can_access_student_resource(user, student_id, *, action)` / `require_student_access(...)` 为统一对象授权接口。只认明确 action；管理员可读取学生 profile/courses/grades/attendance（原需求已经授权），学生可读本人；教师与未知 action 默认拒绝。保留课程/成绩/考勤 action 只是权限基础设施，无对应 CRUD 或查询页面。

最小示例 `GET /students/<student_id>/profile` 只展示姓名、学号、学籍和归档状态；管理员可看、学生限本人、教师默认拒绝。先授权再查对象，外部/无权限 ID（含不存在 ID）统一 403，获授权且对象不存在返回 404。不暴露电话、住址、家长、成绩或密码哈希。

教师跨班/跨课、历史范围、可编辑字段、家长/奖惩范围和教师新增选课仍按 A-04/A-05/A-10/A-12/A-21/A-22 待决。角色入口不是业务授权。用户管理、审计查询、真实通知与统计均未实现，页面明确“待开发”。

## 密码与审计事务

本人改密须验证旧密码；管理员重置须重新验证管理员自己的密码，并检查目标真实存在、角色档案合法。新密码及确认由表单检查，服务再次校验非空及长度。只更新 password_hash，绝不联动账号启停、学籍或归档。

密码服务 `change_own_password(actor, current_password, new_password)` / `reset_user_password(actor, target_user_id, actor_password, new_password)` 只修改对象和 add 审计，不 commit。路由统一 commit/rollback。审计 action=update，快照只有 changed=true、operation=self_change/admin_reset，不含密码或哈希；现有脱敏器会移除所有含 password 的键，故不采用 password_changed 键。登录/失败/退出不扩展数据库 action，使用固定安全日志。本人改密或重置自己后退出，其他会话因 HMAC 版本变化而失效。管理员从工作台进入 `/admin/password-reset` 按用户名查找，再进入目标密码表单，无账号列表或账户 CRUD。

## 验证要求

先保留安装、db check、156 项基线；新测试先红后绿，覆盖登录/退出、真实 CSRF、重定向编码、会话伪造/过期/停用/改密、三角色及对象越权、密码审计同事务回滚。最终完整回归、迁移对照、Word/旧测试/迁移/开发库哈希比对、真实浏览器三角色与截图、PlantUML 语法验证和报告。重要修改说明 ZIP 只收文档、图和验证证据，不收虚拟环境、数据库或凭据。

参考：[Flask 会话安全](https://flask.palletsprojects.com/en/stable/web-security/)、[Flask 配置](https://flask.palletsprojects.com/en/stable/config/)、[Flask-Login](https://flask-login.readthedocs.io/en/0.6.3/)。实现以项目已安装 0.6.3 的接口和实测为准。
