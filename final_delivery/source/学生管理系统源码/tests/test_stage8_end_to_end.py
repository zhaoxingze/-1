from datetime import date

from app.extensions import db
from app.models import Enrollment
from archive_support import submit
from academics_support import TERM, academic, scoped_teacher
from student_records_support import sign_in


def test_teacher_entry_is_readable_by_the_same_student_after_term_filtered_grade_save(academic):
    auth, ids = academic.auth, academic.ids
    response = submit(auth, "/academics/enrollments/new",
                      {"student_id": ids.own, "course_id": ids.own_course, "semester": TERM})
    assert response.status_code == 303
    with auth.app.app_context():
        row = db.session.query(Enrollment).filter_by(student_id=ids.own, course_id=ids.own_course, semester=TERM).one()
        target = f"/academics/grades/{row.enrollment_id}/edit"
    saved = submit(auth, target, {"usual_score": "80", "exam_score": "90"})
    assert saved.status_code == 303
    sign_in(auth, "auth_student")
    grades = auth.client.get(f"/academics/grades?semester={TERM}")
    assert grades.status_code == 200 and "87.00" in grades.text and "AUTH-S2" not in grades.text
    assert auth.client.get(target).status_code == 403


def test_attendance_write_audit_and_student_summary_cross_module(scoped_teacher):
    auth, ids = scoped_teacher
    form = {"student_id": ids.own, "attendance_date": date(2026, 11, 19).isoformat(),
            "period": "端到端示例", "status": "present", "note": "测试备注"}
    response = submit(auth, "/attendance/new", form)
    assert response.status_code == 303
    sign_in(auth, "auth_admin")
    audit = auth.client.get("/admin/audit?entity_type=AttendanceRecord&action=create")
    assert audit.status_code == 200 and "共 1 条" in audit.text
    sign_in(auth, "auth_student")
    result = auth.client.get("/attendance/")
    assert result.status_code == 200 and "端到端示例" in result.text
    assert auth.client.get("/admin/audit").status_code == 403
