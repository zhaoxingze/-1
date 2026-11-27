# 阶段 4B 交付报告

2026-11-19。教师工作台已开放负责班级和授课课程名单。全量实测 **366 项通过**，包含阶段 0–4A 的 335 项和本阶段 31 项。

## 教师权限与范围

| 操作 | 班主任 | 任课教师 |
| --- | --- | --- |
| 查看学生 | 当前本班学号、姓名、班级、电话、住址 | 当前所授课程的选课学生，仅学号和姓名 |
| 编辑学生 | 当前本班限电话和住址 | 无编辑权限 |
| 查看家长 | 当前本班家长姓名、关系、电话、邮箱、主要联系人标记 | 无家长查看权限 |
| 新增学生、删除学生、改学号/分班/学籍/归档/账号、修改家长 | 禁止 | 禁止 |

阶段 3 学生本人最小资料与阶段 4A 管理员全局档案接口沿用各自授权。详细矩阵和 A-04、A-05、A-10、A-21、A-22 的新增决策见[教师权限设计](../specs/stage4b_permissions.md)。

## 算法和代码

每次请求从 Flask-Login 当前 User 取绑定的 Teacher。PermissionService 再核对数据库账号有效、角色为 teacher 及当前绑定。从 `SchoolClass.homeroom_teacher_id` 和 `Student.class_id` 求本班范围，从 `Course.teacher_id` 和既有 `Enrollment` 求所授课程名单。列表在分页前过滤，课程名单投影学号和姓名，同一学生跨学期的重复登记只显示一次。控制器把路径 ID 当作候选对象，表单身份字段和未知 action 都无法授权。

| 文件 | 变更 |
| --- | --- |
| `app/services/permission_service.py` | 新增 TeacherScope 和五个教师权限接口，按 action 检查各自关系 |
| `app/services/teacher_student_service.py` | 班级及课程列表、本班详情、有限字段投影、本班家长只读和有限编辑 |
| `app/services/archive_common.py` | 提取原 SQLite 写锁函数，管理员和教师写入共用 |
| `app/dashboard/teacher_routes.py`、`app/dashboard/__init__.py` | 在原 Blueprint 加载教师页面、后端检查及 CSRF 表单 |
| `app/dashboard/routes.py`、`app/templates/dashboard/workbench.html`、`app/templates/layout.html` | 教师工作台入口及阶段标记 |
| `app/templates/teacher/` | 教师范围列表与本班最小详情 |
| `tests/test_teacher_scope.py`、`test_teacher_student_read.py`、`test_teacher_limited_edit.py`、`test_teacher_parent_read.py`、`test_stage4b_permissions.py` | 五个测试模块，配套虚构档案在 `teacher_scope_support.py` |

## 验证记录

| 批次 | 实际结果 |
| --- | --- |
| 开始前全量 | 335 passed in 204.87s。 [日志](stage4b_baseline_pytest.txt) |
| 实现前红测 | 2 failed，原因是两个教师入口尚未注册。 [日志](stage4b_red.txt) |
| 初次教师专项 | 30 passed in 25.63s。 [日志](stage4b_targeted_pytest.txt) |
| 补测分页 | 1 failed，发现分页宏传入的第二个参数未被接收。修复后纳入最终全量。 [日志](stage4b_pagination_red.txt) |
| 最终全量 | **366 passed in 214.60s**，旧测试文件逐项 SHA-256 一致。 [日志](stage4b_pytest.txt) |

测试验证本班 200、越权学生和家长 403、跨课程 403、匿名跳转登录、学生本人最小资料及管理员新增档案。伪造表单字段、重复键和缺失 CSRF 返回 400。转班、班主任换人和课程换教师会改变下一次授权。双 Session 测试验证缓存学生对象无法继续写入转班后的档案。

有限编辑先校验字段和身份，再取得 SQLite 写锁并重新授权。业务 flush 后追加审计，外层一次提交。真实 SQLite 触发器阻断审计 INSERT 时，业务变更完整回滚。审计保存真实 User 主键、Student ID、update、时间及电话/住址前后快照。浏览器成功写入后也直接核对了临时库的审核字段。

`pip check` 通过，`db check` 无新升级操作。原迁移 `fab16ef0dd6f`、13 领域表、94 字段、20 个 RESTRICT 外键和 7 个触发器均经核对。57 项受保护文件的 SHA-256 一致，包含开发库、原设计 Word、旧测试、模型、认证模块及迁移。 [依赖检查](stage4b_pip_check.txt) · [迁移检查](stage4b_migration_check.txt) · [冻结核验](stage4b_final_validation.json)

## 浏览器与 UML

真实 Flask 服务使用临时迁移库、虚构学生和临时教师账号。浏览器实际登录、进入班级、编辑并保存电话和住址、查看本班家长及任课名单。14 项浏览器断言通过，包括跨班、跨课和管理员入口拒绝、匿名跳转及 390px 移动表单无横向溢出。审计读取核验通过，无浏览器页面异常。 [浏览器记录](stage4b_browser.json)

- [教师工作台](../../output/playwright/stage4b-workbench.png) · [本班学生](../../output/playwright/stage4b-class-roster.png)
- [填写联系方式](../../output/playwright/stage4b-contact-edit.png) · [保存结果](../../output/playwright/stage4b-contact-saved.png)
- [家长只读](../../output/playwright/stage4b-parent-read.png) · [课程身份名单](../../output/playwright/stage4b-course-roster.png) · [移动端编辑](../../output/playwright/stage4b-mobile-contact.png)

用例图拆出班主任和任课教师对应权限。类图补上 TeacherScope 和教师档案服务。顺序图与通信图增加联系编辑的范围检查、锁内再授权、审计、提交和回滚。七类源、十二图块通过 PlantUML 语法检查，四个受影响文件渲染成功。 [UML 索引](../uml/README.md) · [语法](stage4b_uml.txt) · [渲染](stage4b_uml_render.txt)

## 阶段 5 前置条件

4B 技术验收通过，已具备进入阶段 5 设计和开发的认证、关系模型及权限基础。开放选课写入和成绩流程前，需明确 A-22 教师新增选课候选范围、当前学期选取，以及 A-02/A-06 成绩权重、舍入和缺分策略。历史转班和任教、成绩历史访问及其它教师业务权限仍待决。当前名单按已有选课跨学期去重，仅授予最小身份查询。

完整源码 ZIP 包含运行代码、迁移、依赖声明、测试、设计、报告和虚构数据截图。运行库、虚拟环境、缓存、私人配置、密钥和临时教师凭据排除。阶段 4B 到此结束。
