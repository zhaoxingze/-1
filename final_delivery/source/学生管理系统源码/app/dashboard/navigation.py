"""Role-scoped links shared by the sidebar and workbench."""

from flask_login import current_user

from app.services.permission_service import ATTENDANCE_READ, student_record_access
from . import bp

_RECORDS = (
    ("考勤管理", "attendance.index"), ("奖励与处分", "records.rewards"),
    ("家长联系", "records.contacts"), ("模拟通知", "records.notifications"),
)
_ADMIN = (
    ("档案管理", (("学生管理", "admin.students_list"), ("教师管理", "admin.teachers_list"),
                  ("班级管理", "admin.classes_list"), ("家长管理", "admin.parents_list"))),
    ("教务管理", (("课程管理", "academics.courses"), ("选课管理", "academics.enrollments"),
                  ("成绩管理", "academics.grades"))),
    ("成长与沟通", _RECORDS),
    ("系统管理", (("用户管理", "admin.users"), ("审计日志", "admin.audit_list"))),
)
_TEACHER = (
    ("教师业务", (("负责班级", "dashboard.teacher_classes"), ("授课课程学生", "dashboard.teacher_courses"),
                 ("本人授课课程", "academics.courses"), ("选课管理", "academics.enrollments"),
                 ("成绩管理", "academics.grades"))),
)
_STUDENT = (
    ("本人资料", (("本人课程", "academics.courses"), ("本人选课", "academics.enrollments"),
                 ("本人成绩", "academics.grades"), ("本人考勤", "attendance.index"))),
)
WORKBENCH = {"admin": "admin.index", "teacher": "dashboard.teacher", "student": "dashboard.student"}


@bp.app_context_processor
def navigation_links():
    public = (("系统首页", "dashboard.index"), ("健康检查", "dashboard.health"))
    if not current_user.is_authenticated:
        return {"navigation_home": (*public, ("用户登录", "auth.login")), "navigation_groups": ()}
    role = current_user.role.name
    groups = {"admin": _ADMIN, "teacher": _TEACHER, "student": _STUDENT}[role]
    if role == "teacher":
        try:
            student_record_access(current_user, ATTENDANCE_READ)
        except PermissionError:
            pass
        else:
            groups += (("本班管理", _RECORDS),)
    home = (("首页统计", WORKBENCH[role]), ("个人资料", "dashboard.profile"), *public)
    return {"navigation_home": home, "navigation_groups": groups}
