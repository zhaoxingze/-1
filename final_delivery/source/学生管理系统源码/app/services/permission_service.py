"""Shared role and object authorization; unspecified actions are denied."""

from functools import wraps
from dataclasses import dataclass

from flask import abort, current_app
from flask_login import current_user
from sqlalchemy import and_, select, true

from app.auth.session import account_is_usable
from app.extensions import db, login_manager
from app.models import Course, Enrollment, Role, SchoolClass, Student, User

ROLE_NAMES = {"admin", "teacher", "student"}
STUDENT_READ_ACTIONS = {"read_profile", "read_courses", "read_grades", "read_attendance"}


def has_role(user, *roles: str) -> bool:
    return (getattr(user, "is_authenticated", False) and account_is_usable(user)
            and user.role.name in roles)


def role_required(*roles: str):
    if not roles or not set(roles) <= ROLE_NAMES:
        raise ValueError("Explicit supported role names are required")
    def decorate(view):
        @wraps(view)
        def guarded(*args, **kwargs):
            if not current_user.is_authenticated:
                return login_manager.unauthorized()
            if not has_role(current_user, *roles):
                abort(403)
            return view(*args, **kwargs)
        return guarded
    return decorate


def can_access_student_resource(user, student_id: int, *, action: str = "read_profile") -> bool:
    if (isinstance(student_id, bool) or not isinstance(student_id, int) or student_id <= 0
            or not isinstance(action, str) or action not in STUDENT_READ_ACTIONS):
        return False
    if has_role(user, "admin"):
        return True
    return bool(has_role(user, "student") and user.student_id == student_id)


def require_student_access(user, student_id: int, *, action: str = "read_profile") -> None:
    if not can_access_student_resource(user, student_id, action=action):
        abort(403)


HOMEROOM_PROFILE = "homeroom_profile"
COURSE_IDENTITY = "course_identity"
EDIT_CONTACT = "edit_contact"
PARENT_CONTACT = "parent_contact"


def valid_scope_id(value):
    return type(value) is int and 0 < value <= 2**63 - 1


@dataclass(frozen=True)
class TeacherScope:
    user_id: int
    teacher_id: int

    def _current_binding(self):
        return select(User.teacher_id).join(Role).where(
            User.user_id == self.user_id,
            User.teacher_id == self.teacher_id,
            User.is_active.is_(True),
            User.student_id.is_(None),
            Role.name == "teacher",
        )

    @property
    def class_ids(self):
        return select(SchoolClass.class_id).where(
            SchoolClass.homeroom_teacher_id.in_(self._current_binding())
        )

    @property
    def course_ids(self):
        return select(Course.course_id).where(Course.teacher_id.in_(self._current_binding()))

    def student_filter(self, action, *, course_id=None):
        if action in (HOMEROOM_PROFILE, EDIT_CONTACT, PARENT_CONTACT) and course_id is None:
            return Student.class_id.in_(self.class_ids)
        if action == COURSE_IDENTITY and valid_scope_id(course_id):
            candidates = select(Enrollment.student_id).where(
                Enrollment.course_id == course_id, Enrollment.course_id.in_(self.course_ids)
            )
            return Student.student_id.in_(candidates)
        raise PermissionError("Unsupported teacher access action")


def get_teacher_scope(user) -> TeacherScope:
    """Resolve the persisted binding of an authenticated teacher account."""
    with db.session.no_autoflush:
        if not has_role(user, "teacher") or not valid_scope_id(user.user_id):
            raise PermissionError("Teacher account required")
        teacher_id = user.teacher.teacher_id
        scope = TeacherScope(user.user_id, teacher_id)
        if db.session.scalar(scope._current_binding()) is None:
            raise PermissionError("Teacher binding is no longer valid")
    return scope


def require_teacher_student_access(user, student_id, *, action, course_id=None) -> TeacherScope:
    if not valid_scope_id(student_id):
        raise PermissionError("Student outside teacher scope")
    scope = get_teacher_scope(user)
    statement = select(Student.student_id).where(
        Student.student_id == student_id, scope.student_filter(action, course_id=course_id)
    )
    with db.session.no_autoflush:
        if db.session.scalar(statement) is None:
            raise PermissionError("Student outside teacher scope")
    return scope


def _can_access(user, student_id, *, action, course_id=None):
    try:
        require_teacher_student_access(user, student_id, action=action, course_id=course_id)
    except PermissionError:
        return False
    return True


def can_view_student(user, student_id, *, course_id=None):
    action = HOMEROOM_PROFILE if course_id is None else COURSE_IDENTITY
    return _can_access(user, student_id, action=action, course_id=course_id)


def can_edit_student_contact(user, student_id):
    return _can_access(user, student_id, action=EDIT_CONTACT)


def can_view_parent_contact(user, student_id):
    return _can_access(user, student_id, action=PARENT_CONTACT)


COURSE_READ = "course_read"
COURSE_MANAGE = "course_manage"
ENROLLMENT_READ = "enrollment_read"
ENROLLMENT_CREATE = "enrollment_create"
GRADE_READ = "grade_read"
GRADE_WRITE = "grade_write"

_ACADEMIC_ROLES = {
    COURSE_READ: ROLE_NAMES,
    COURSE_MANAGE: {"admin"},
    ENROLLMENT_READ: ROLE_NAMES,
    ENROLLMENT_CREATE: {"admin", "teacher"},
    GRADE_READ: ROLE_NAMES,
    GRADE_WRITE: {"admin", "teacher"},
}


@dataclass(frozen=True)
class AcademicScope:
    action: str
    role: str
    active_semester: str
    teacher: TeacherScope | None = None
    student_id: int | None = None

    def courses(self):
        if self.teacher:
            return Course.course_id.in_(self.teacher.course_ids)
        if self.student_id is not None:
            return Course.course_id.in_(
                select(Enrollment.course_id).where(Enrollment.student_id == self.student_id)
            )
        return true()

    def enrollments(self):
        if self.action not in (ENROLLMENT_READ, GRADE_READ, GRADE_WRITE):
            raise PermissionError("Enrollment query action required")
        if self.teacher:
            owns_course = Enrollment.course_id.in_(self.teacher.course_ids)
            if self.action in (GRADE_READ, GRADE_WRITE):
                return and_(owns_course, Enrollment.semester == self.active_semester)
            return owns_course
        if self.student_id is not None:
            return Enrollment.student_id == self.student_id
        return true()

    def enrollment_candidates(self):
        if self.action != ENROLLMENT_CREATE:
            raise PermissionError("Enrollment create action required")
        return Student.class_id.in_(self.teacher.class_ids) if self.teacher else true()


def _require_bound_account(actor, allowed_roles):
    with db.session.no_autoflush:
        if not allowed_roles or not has_role(actor, *allowed_roles) or not valid_scope_id(actor.user_id):
            raise PermissionError("Action denied")
        role = actor.role.name
        if role == "teacher":
            return role, get_teacher_scope(actor)
        binding = select(User.user_id).join(Role).where(
            User.user_id == actor.user_id, User.is_active.is_(True), Role.name == role,
            User.teacher_id.is_(None), User.student_id == actor.student_id,
        )
        if db.session.scalar(binding) is None:
            raise PermissionError("Account binding no longer valid")
        return role, None


def academic_access(actor, action) -> AcademicScope:
    """Authorize a named action against the account's current persisted role."""
    allowed_roles = _ACADEMIC_ROLES.get(action, ()) if isinstance(action, str) else ()
    role, teacher = _require_bound_account(actor, allowed_roles)
    return AcademicScope(action, role, current_app.config["ACTIVE_SEMESTER"],
                         teacher=teacher, student_id=actor.student_id)


def require_current_admin(actor):
    _require_bound_account(actor, {"admin"})


ATTENDANCE_READ = "attendance_read"
ATTENDANCE_WRITE = "attendance_write"
REWARD_READ = "reward_read"
REWARD_WRITE = "reward_write"
PARENT_CONTACT_READ = "parent_contact_read"
PARENT_CONTACT_WRITE = "parent_contact_write"
NOTIFICATION_CREATE = "notification_create"
NOTIFICATION_READ = "notification_read"

_STUDENT_RECORD_ROLES = {
    ATTENDANCE_READ: ROLE_NAMES,
    ATTENDANCE_WRITE: {"admin", "teacher"},
    REWARD_READ: {"admin", "teacher"},
    REWARD_WRITE: {"admin", "teacher"},
    PARENT_CONTACT_READ: {"admin", "teacher"},
    PARENT_CONTACT_WRITE: {"admin", "teacher"},
    NOTIFICATION_CREATE: {"admin", "teacher"},
    NOTIFICATION_READ: {"admin", "teacher"},
}


@dataclass(frozen=True)
class StudentRecordScope:
    role: str
    teacher: TeacherScope | None
    student_id: int | None

    def students(self):
        if self.teacher is not None:
            return self.teacher.student_filter(HOMEROOM_PROFILE)
        if self.role == "student":
            return Student.student_id == self.student_id
        return true()

    def classes(self):
        if self.teacher is not None:
            return SchoolClass.class_id.in_(self.teacher.class_ids)
        if self.role == "student":
            return SchoolClass.class_id.in_(select(Student.class_id).where(self.students()))
        return true()


def student_record_access(actor, action) -> StudentRecordScope:
    """Apply the explicit record policy and require a current homeroom for teachers."""
    allowed_roles = _STUDENT_RECORD_ROLES.get(action, ()) if isinstance(action, str) else ()
    role, teacher = _require_bound_account(actor, allowed_roles)
    if teacher is not None and db.session.scalar(teacher.class_ids.limit(1)) is None:
        raise PermissionError("Homeroom assignment required")
    return StudentRecordScope(role, teacher, actor.student_id)
