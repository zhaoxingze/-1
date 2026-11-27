# StudentManagementSystem 重要修改说明

日期：2026-11-17。覆盖阶段0–3，重点记录当前认证与权限变更。ZIP为说明材料包，运行代码保留在原项目；包内没有开发数据库、虚拟环境或可登录凭据。

## 1 各阶段主要成果

| 阶段 | 重要修改 | 验证与边界 |
| --- | --- | --- |
| 0 设计基线 | Word整理为需求、架构、数据库、假设及审查报告；七类PlantUML源 | 原11表73字段16FK，未决规则明确登记 |
| 1 Flask骨架 | Python3.12.10独立.venv、工厂、七Blueprint、公共页/health、模板/错误页、SQLAlchemy/Login/CSRF、配置日志 | 19项历史测试；Word安全移动至specs/source，SHA-256不变 |
| 2 数据层 | 13表94字段20RESTRICT外键、SQLAlchemy2模型、初始迁移、审计/模拟通知、完整性服务、显式CLI | 156项历史测试；无默认账号、无真实通知 |
| 3 认证/RBAC | 真实登录/POST退出、绝对时限会话、三角色入口、本人资料、角色与对象授权、本人改密/管理员重置 | 最终251项全过（旧156+新95）；三角色浏览器验证通过；数据库结构与数据保持 |

阶段2新增：Student.is_archived独立于学籍及账号启停；ParentContactLog增加联系人姓名/电话；AuditLog和NotificationLog各9字段。7个SQLite触发器保护审计追加及家长归属，所有外键RESTRICT，无历史删除级联。

## 2 阶段3实际可用入口

| 入口 | 功能与权限 |
| --- | --- |
| `/login` | 公开登录页及CSRF保护的登录提交 |
| `/logout` | 仅带CSRF的POST，退出当前浏览器 |
| `/dashboard` | 按数据库角色分流，拒绝前端伪造身份 |
| `/admin/` | 管理员工作台，教师/学生403 |
| `/dashboard/teacher`、`/dashboard/student` | 对应角色工作台，跨角色403 |
| `/profile` | 本人基础资料，从认证会话取身份 |
| `/students/<id>/profile` | 管理员已授权读取/学生本人最小资料；教师默认拒绝 |
| `/password/change` | 本人验证旧密码后改密；成功后重新登录 |
| `/admin/password-reset` | 管理员按用户名查找，下一步二次验证管理员密码后重置目标 |

管理员不因拥有管理角色自动进入教师/学生专属工作台。课程、成绩、考勤等action仅预留授权接口，没有相应业务页面。未开发卡片均标记“待开发”。

## 3 安全与修复重点

- 复用Werkzeug哈希；统一认证失败提示；不存在账号也做随机虚拟哈希校验；密码/哈希不回填HTML、不进普通日志。
- 登录清旧会话，最长30分钟、不续期、无remember-me。每请求核对启停、绑定和HMAC凭据版本，改密/角色变化使旧会话失效。
- Cookie为HttpOnly、SameSite=Lax；production启用Secure并要求环境密钥。状态变更持续启用CSRF，私有响应no-store。
- next多次解码后仍须为安全站内路径，拒绝开放重定向；用户角色、登记身份和student_id归属不由前端声明。
- 密码变更与追加审计同事务，子服务不commit；不扩展审计Action，不存密码/哈希。
- 独立审查复现的旧Cookie+空库首页错误、超大ID异常已先红测再修复；事务文档统一。最终四项修复回归及完整251项均通过。

## 4 关键文件

认证：`app/auth/session.py`、`forms.py`、`routes.py`；授权：`app/services/permission_service.py`；密码事务：`password_service.py`；角色/最小资料入口：`app/admin/routes.py`、`app/dashboard/routes.py`、`app/students/routes.py`。

User仅增加Flask-Login协议方法，不改原8字段。config.py新增生产Cookie配置；工厂启用真实current_user。新增七个认证/权限测试文件；旧测试不删、不跳过、不降低断言。设计与UML同步，原Word/迁移/历史报告保留。

## 5 验证材料与后续边界

详见 [阶段3报告](stage3_report.md)、[认证设计](../specs/stage3_auth_rbac_design.md)、[最终测试](stage3_pytest.txt)、[浏览器结果](stage3_browser.json)、[冻结核验](stage3_final_validation.json)。历史成果见 [阶段1报告](stage1_report.md)、[阶段2报告](stage2_report.md)。

未实现业务CRUD、审计查询、统计、真实通知和未确认教师范围。复制Cookie的中心即时撤销需后续服务端会话设计；当前退出清本浏览器，改密会使旧凭据版本失效。下一阶段先落实教师业务范围，再开发基础档案CRUD；本次停止于阶段3。
