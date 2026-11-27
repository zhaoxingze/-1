# 阶段 5 验收报告

验收日期 2026-11-19，使用项目虚拟环境中的 Python 3.12.10、Flask、SQLAlchemy 和 SQLite。阶段 5 完成，阶段 6 留待单独指令。

## 实现范围

| 操作者 | 已验证功能 |
| --- | --- |
| 管理员 | 新增、搜索、分页、查看和修改课程，指派已有教师，按学期统计选课人数，按课程或学生查询选课与成绩，跨学期新增选课、录入和修改成绩 |
| 教师 | 查看本人当前授课课程及分学期选课名单，为本班学生新增配置学期的本人授课课程，录入和修改本人课程在配置学期的成绩 |
| 学生 | 查询已选课程、本人选课和各学期本人成绩。课程详情显示本人所选学期的选课状态 |

所有页面通过工作台或详情页可达。三个角色共用现有 Jinja2 和 Bootstrap。写操作表单启用 CSRF，保留既有登录、改密、工作台和教师档案入口。

## 规则与权限

- **A-02** 平时占 30%，考试占 70%。`grade_service` 用 Decimal 计算，按 ROUND_HALF_UP 将总评舍入到两位小数，再写入原有 Float 字段。输入 80 和 90，显示 87.00。
- **A-06** 新选课三项分数为 NULL。正式录入须同时提交两项 0–100 的有限数值。页面分别显示未评分与 0.00。
- **A-10** 以现任授课教师和 `ACTIVE_SEMESTER` 限制教师成绩读取和修改，管理员可跨学期维护。现任教师仍可查该课程分学期的选课身份名单。课程换教师保留原选课和分数。
- **A-22** 教师新增选课时，服务验证登录账号绑定的 Teacher、当前授课关系、学生当前班主任关系和配置学期。候选依据学生当前班级生成，可以为从未选过该课程的本班学生新增记录。

配置学期默认 `2026-Fall`，开发和生产可覆盖环境变量 `ACTIVE_SEMESTER`。成绩与选课列表默认显示配置学期，逐行标明学期。管理员和学生可选择全部学期。[业务决策及权限矩阵](../specs/stage5_decisions.md)

## 代码及数据库

| 修改位置 | 职责 |
| --- | --- |
| `app/academics/` | 课程、选课、成绩路由，WTForms 和过滤参数解析 |
| `app/services/permission_service.py` | 六项显式学业动作及对象授权，复用 TeacherScope 子查询 |
| `app/services/course_service.py` | 课程读取、编辑、教师外键核验和分学期人数 |
| `app/services/enrollment_service.py` | 选课查询、候选范围和重复选课核验 |
| `app/services/grade_service.py` | 分数校验、加权计算、锁内授权和审计快照 |
| `app/templates/academics/`、管理端和工作台模板 | 角色入口、列表、详情和筛选。表单复用原有编辑模板 |
| `config.py`、`app/__init__.py` | 配置学期校验与环境覆盖 |
| `tests/academics_support.py` 和六个阶段 5 测试文件 | 独立临时 SQLite 上的课程、选课、成绩、权限、审计与路由验证 |

现有模型和迁移文件的 SHA-256 保持一致。开发库仍为 **13 张领域表、94 个字段、20 个 RESTRICT 外键、7 个触发器**，Alembic 版本 `fab16ef0dd6f`。选课三元组 `(student_id, course_id, semester)` 唯一，SQLite 完整性检查通过，外键违规为 0。开发库文件与阶段开始时 SHA-256 一致。使用阶段 4B 包清单及本地数据库快照核对 266 个文件，248 个字节一致，另外 18 个为本阶段预期更新。原 33 个测试文件和辅助文件字节一致。[保留情况及数据库证据](stage5_database_and_preservation.json)

## 测试与审计

| 验收项 | 实测结果 |
| --- | --- |
| 阶段 4B 基线 | 366 项通过，231.01 秒 |
| 阶段 5 全量 pytest | **409 项通过**，含原 366 项及新增 **43 项**，155.09 秒 |
| 角色与对象范围 | 未登录 GET 跳转登录，教师跨课程、跨班新增选课及访问历史成绩被拒绝。学生访问其他学生成绩或写入被拒绝。篡改 URL、对象、学期及身份字段未能扩权 |
| 查询范围 | 课程、选课、成绩及选课人数按权限先过滤。测试检查分页总数与筛选参数保留 |
| 旧授课关系 | 原教师打开的成绩表单在课程改派后提交返回 403 |
| 成功事务 | 课程创建和修改、选课创建、首次录分和修改均追加审计。分数快照包含真实操作者、Enrollment ID、三项前后值及时间 |
| 失败事务 | 临时库触发器拒绝插入审计时，课程、选课和成绩三类写入均返回冲突且整体回滚 |
| pip check | 无依赖冲突 |
| Flask 与迁移 | 临时库升级到原有版本后启动，现有库 `flask --app run db check` 无新迁移操作 |

最初两项定向测试确认学业路由和计算服务尚缺。接入后首次定向验证为 39 通过、2 失败，原因是选课表单空占位项进入整数转换。改为整数占位项并增加所选 ID 范围校验后，全量 409 项通过。

[基线日志](stage5_baseline_pytest.txt) · [全量测试日志](stage5_pytest.txt) · [依赖检查](stage5_pip_check.txt) · [迁移检查](stage5_migration_check.txt)

## 真实浏览器验收

在本机 Flask 服务、Edge 和独立临时 SQLite 上，以三种真实登录会话执行 22 条浏览器断言，并从临时数据库核对三条操作审计和历史分数。演示身份、课程及选课均为虚构数据。手机端以 390 × 844 像素视口核对成绩编辑表单可用且页面无横向溢出。[浏览器断言及数据库审计结果](stage5_browser.json)

| 操作 | 截图 |
| --- | --- |
| 管理员新建课程，搜索和重复校验 | [创建表单](../../output/playwright/stage5-admin-course-form.png)、[搜索结果](../../output/playwright/stage5-admin-course-search.png)、[重复课程提示](../../output/playwright/stage5-admin-course-duplicate.png) |
| 教师新增选课并录分 | [限本班候选](../../output/playwright/stage5-teacher-enrollment-form.png)、[成绩表单](../../output/playwright/stage5-teacher-grade-form.png)、[保存后总评 87.00](../../output/playwright/stage5-teacher-grade-result.png) |
| 学生分学期读取本人数据 | [本人各学期成绩](../../output/playwright/stage5-student-grades.png)、[访问他人成绩被拒绝](../../output/playwright/stage5-student-forbidden.png) |
| 移动端 | [390 像素成绩编辑表单](../../output/playwright/stage5-teacher-grade-mobile.png) |

## UML 与后续衔接

- 用例图区分课程维护、选课查询与新增、成绩录入与读取。类图新增学业权限值对象及三个服务模块，保留持久化实体和外键。
- 顺序图与通信图记录成绩校验、Decimal 计算、写锁、重验、审计和返回。活动图覆盖重复选课、非法分数、越权、提交及回滚。
- 本地 PlantUML 检查 7 份源文件并渲染 16 个图块。用例图初检定位到拆分本人查询用例时别名重复，修正后全量通过。[UML 索引](../uml/README.md) · [语法检查](stage5_uml_syntax.txt) · [渲染清单](stage5_uml_render.txt)

阶段 5 已达到进入阶段 6 的工程条件。阶段 6 开始前仍需确认考勤时段与统计口径、奖惩与家长联系的教师和学生权限。历史任教授权、成绩草稿及清空、权重调整后是否重算均留待后续。源码交付包附 SHA-256、文件清单及解包验证记录。开发库、虚拟环境、缓存、密钥、临时登录凭据及真实个人数据均排除。
