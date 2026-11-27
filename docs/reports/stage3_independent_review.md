# 阶段 3 独立代码审查

日期：2026-11-17。审查范围：当前认证、RBAC、对象授权、密码管理、工厂与配置、相关模板、7 个新增测试文件，以及当前需求、架构、假设和认证 UML。依据用户完整阶段 3 附件、`stage3_auth_rbac_design.md`、实施计划的 Review Focus / Rulings，以及阶段前副本生成的 diff。审查仅新建本报告，未修改实现、测试或配置，未访问 instance 开发库，未派生代理。

## Strengths

- 身份由 Flask-Login 会话及数据库当前账号恢复；角色名而非固定主键决定授权。账号启停、角色、档案绑定和凭据版本都在加载时验证。教师未决范围默认拒绝，学生对象授权在数据库对象查询前执行。
- next 先进行有界递归解码，再拒绝外部地址、反斜杠、控制字符和登录/退出回环；未使用请求 Host 决定可信目标。
- 密码更新和追加式审计共享调用方事务；错误分支不记录 SQL 异常参数。独立故障注入确认：即使 commit 前已 flush，路由 rollback 仍撤销密码及审计。
- 原 12 个测试模块、初始迁移、迁移 env、原 Word、阶段 1/2 报告均与阶段前 SHA-256 清单一致；conftest 只在原 fixture 后追加认证 fixture。当前 ORM metadata 为 13 表、94 字段、20 FK，全部 FK 为 RESTRICT。初始迁移文件未变化，未新增迁移。
- 已读取实施者完整回归日志：247 passed in 67.60s。该结果是实施者证据，本审查没有重复运行全套。

## Issues

### Critical (Must Fix)

无。此次审查未发现成功的角色提升、学生跨对象读取、教师全局读取或明文凭据泄露。

### Important (Should Fix)

1. **携带仍有效旧会话的公共首页依赖已初始化数据库。**
   - 位置：`app/auth/session.py:84-88`；触发点 `app/templates/layout.html:24`，公共首页 `app/dashboard/routes.py:11-13`。
   - 问题：公共首页模板读取 current_user，loader 无条件查询 users。若使用稳定 SECRET_KEY 切换到尚未初始化的新库，浏览器保留的有效旧 Cookie 会让本应可用的 `/` 抛出 OperationalError（生产为 500），而无 Cookie 首页仍为 200。`/health` 为 200。
   - 影响：认证上下文使公共首页的无数据库启动契约只对全新浏览器成立。设计“公共首页及 health 不要求数据库已初始化”未限定无会话；README 第 85 行后来增加了“无账号会话时”的限定，不能替代原公共页面契约。
   - 独立复现：pytest `auth` 临时库登录，复制真实签名 Cookie；创建相同 testing SECRET_KEY、全新内存 SQLite 的第二 app，不 create_all；第二 client GET `/` 无 Cookie 为 200，设置复制的 Cookie 后 GET `/` 抛 `(sqlite3.OperationalError) no such table: users`。不需要伪造签名、修改开发库或修改会话内容。
   - 建议：明确公共页面在身份存储尚未就绪时的匿名退化行为，并避免错误页再次触发同一失败加载；私有路由保持失败关闭。增加保留旧 Cookie 的空库首页回归，不要依赖清理浏览器 Cookie 解决。

### Minor (Nice to Have)

1. **超出 SQLite 整数范围的资源 ID 导致未处理异常。**
   - 位置：`app/students/routes.py:14`、`app/admin/routes.py:38`；授权入口 `app/services/permission_service.py:35-40` 只检查正整数，没有限制 SQLite INTEGER 范围。
   - 独立复现：管理员登录后 GET `/students/9223372036854775808/profile` 和 `/admin/users/9223372036854775808/reset-password`，均抛 `OverflowError: Python int too large to convert to SQLite INTEGER`。生产返回 500，而不是该范围内不存在对象应得到的 404。
   - 影响：错误输入处理不完整；未构成越权，学生及教师仍在查询前被拒绝，因此不作为高危安全漏洞。
   - 建议：数据库查询前将不可能持久化的主键作为不存在资源处理；学生对象路由继续维持先授权、再决定不存在响应的策略。

2. **当前架构文档对事务拥有者给出两套表述。**
   - 位置：`docs/specs/architecture.md:107` 与 `docs/specs/architecture.md:172`；代码为 `app/auth/routes.py:68-75`、`app/admin/routes.py:45-52`。
   - 第 5 节称 Service 组织提交与回滚，第 11 节和实际阶段 3 代码为路由统一 commit/rollback、服务只 add。阶段 3 的同事务实现本身正确，但面向后续业务开发的通用架构规则容易被误读。
   - 建议：说明当前阶段调用方统一事务原则，或明确区分未来完整业务服务的事务拥有者；保留“不可分段提交”的约束。未来 UC-02 图已明确标注为尚未实现，不应为了消除差异擅自修改业务实现。

## 独立验证证据

所有额外运行通过 stdin 启动 Python，使用内存定义的 pytest collection plugin 注入探测函数；调用现有 `auth`、`tmp_path` fixture，禁用 pytest cache 与 Python 字节码写入。没有新增测试文件。

| 批次 | 内容 | 真实结果 |
| --- | --- | --- |
| 1 | 两个大整数 URL 确认异常；旧签名 Cookie + 未初始化库首页确认异常 | 2 passed in 1.23s（断言异常存在，不代表功能通过） |
| 2 | commit 在 flush 后故障时密码/审计同时回滚；第二工厂创建后原 app 认证与 CSRF 继续有效 | 2 passed in 1.46s |
| 只读比对 | 原测试模块、迁移、Word、历史报告 SHA-256；ORM metadata 数量/FK | 均与上述 Strengths 一致 |

现有 7 个测试文件已覆盖真实 CSRF、账号不存在/停用、三角色矩阵、恶意 next、绝对过期和未来时间、异常身份/版本、改密及角色绑定变化失效、对象默认拒绝、审计回滚。未将这些静态阅读结果冒充本审查全套重跑。

## Recommendations

优先处理公共首页空库且保留会话的回归，补上两个可复现输入边界及对应回归，再运行受影响专项与最终全套。文档事务拥有者统一为实际行为。最终浏览器、UML 编译、交付包和开发库冻结核验由主执行者继续完成。

## Declined to judge

- 密码复杂度、强制定期更换、首次改密、用户名大小写归一：用户未确定这些业务规则，设计明确只做最小非空和技术上限；不以个人偏好报缺陷。
- 教师跨班/跨课、奖惩和家长数据范围、业务 CRUD 与统计：本阶段明确不开放；默认拒绝是要求，不是遗漏。
- 复制签名 Cookie 的单会话中心撤销、跨设备退出：设计明确记录无服务端会话表时的限制，本审查不将未承诺的中心撤销要求视为实现缺陷。
- 未来 UC-02 Service 自主管理事务与当前密码路由拥有事务的实现差异：未来流程尚未实现，不判断其代码正确性；只报告当前通用架构文案需要澄清。
- 最终真实浏览器视觉、控制台、PlantUML 编译、最终交付 ZIP、开发库是否保持冻结：主执行者仍在收尾；本审查未操作开发库，也未把这些未独立验证事项写成通过。

## Assessment

**Ready to merge? With fixes.**

核心认证与权限实现符合范围，暂未发现越权或事务分裂；建议在阶段 3 最终验收前修复公共首页旧会话回归。两项 Minor 问题可直接补齐，不需要扩展权限范围或数据库结构。以上结论针对本报告生成时读取的实现，后续修复应由执行者记录复核结果。
