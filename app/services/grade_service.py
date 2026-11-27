"""Validate and calculate grades in Decimal before writing existing Float fields."""

from decimal import Decimal, ROUND_HALF_UP, localcontext

from sqlalchemy import select

from app.extensions import db
from app.models import Enrollment
from .archive_common import ArchiveValidationError, audit, begin_archive_write, get_record, snapshot
from .permission_service import GRADE_WRITE, academic_access, valid_scope_id

GRADE_FIELDS = ("usual_score", "exam_score", "total_score")


def _score(value, field):
    if type(value) not in (Decimal, int, float):
        raise ArchiveValidationError(field, "必须填写有效的分数。")
    score = value if isinstance(value, Decimal) else Decimal(str(value))
    if not score.is_finite() or not Decimal(0) <= score <= Decimal(100):
        raise ArchiveValidationError(field, "分数须为 0 到 100 之间的有限数值。")
    return score


def _weighted_total(usual, exam):
    with localcontext() as context:
        context.prec = max(28, len(usual.as_tuple().digits) + 6, len(exam.as_tuple().digits) + 6)
        total = usual * Decimal("0.30") + exam * Decimal("0.70")
        return total.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP).copy_abs()


def calculate_total(usual_score, exam_score):
    return _weighted_total(_score(usual_score, "usual_score"), _score(exam_score, "exam_score"))


def _get_grade_target(scope, enrollment_id, *, fresh=False):
    if scope.role == "admin":
        return get_record(Enrollment, enrollment_id, fresh=fresh)
    if not valid_scope_id(enrollment_id):
        raise PermissionError("Grade outside teacher scope")
    statement = select(Enrollment).where(Enrollment.enrollment_id == enrollment_id, scope.enrollments())
    row = db.session.scalar(statement.execution_options(populate_existing=fresh))
    if row is None:
        raise PermissionError("Grade outside teacher scope")
    return row


def get_grade_for_edit(actor, enrollment_id):
    return _get_grade_target(academic_access(actor, GRADE_WRITE), enrollment_id)


def save_grades(actor, enrollment_id, usual_score, exam_score):
    academic_access(actor, GRADE_WRITE)
    usual = _score(usual_score, "usual_score")
    exam = _score(exam_score, "exam_score")
    total = _weighted_total(usual, exam)
    begin_archive_write()
    scope = academic_access(actor, GRADE_WRITE)
    row = _get_grade_target(scope, enrollment_id, fresh=True)
    before = snapshot(row, GRADE_FIELDS)
    row.usual_score = float(usual.copy_abs())
    row.exam_score = float(exam.copy_abs())
    row.total_score = float(total)
    db.session.flush()
    audit(actor, row, GRADE_FIELDS, before=before)
    return row
