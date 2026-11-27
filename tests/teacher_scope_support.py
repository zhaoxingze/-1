"""Fictional records for the 4B permission tests."""

from datetime import date
from types import SimpleNamespace

import pytest

from app.extensions import db
from app.models import Course, Enrollment, Parent, SchoolClass, Student, Teacher, User


@pytest.fixture
def scoped_teacher(auth):
    with auth.app.app_context():
        account = db.session.get(User, auth.ids["auth_teacher"])
        own = db.session.get(Student, auth.student_ids[0])
        course_only = db.session.get(Student, auth.student_ids[1])
        other = Teacher(teacher_no="SCOPE-T2", name="外班虚构教师")
        own_class = SchoolClass(class_name="负责班级", grade="G1", homeroom_teacher=account.teacher)
        other_class = SchoolClass(class_name="外部班级", grade="G1", homeroom_teacher=other)
        own.school_class = own_class
        own.phone, own.address = "000-4001", "虚构本班地址"
        course_only.school_class = other_class
        course_only.phone, course_only.address = "000-4002", "虚构任课学生私有地址"
        unrelated = Student(student_no="SCOPE-OTHER", name="范围外学生", gender="未指定",
                            enrollment_date=date(2026, 9, 1), school_class=other_class)
        own_course = Course(course_code="SCOPE-C1", course_name="本教师课程", credit=1, teacher=account.teacher)
        other_course = Course(course_code="SCOPE-C2", course_name="其他教师课程", credit=1, teacher=other)
        db.session.add_all([
            Enrollment(student=course_only, course=own_course, semester="T1", total_score=98.75),
            Enrollment(student=course_only, course=own_course, semester="T2"),
            Enrollment(student=own, course=own_course, semester="T1"),
            Enrollment(student=unrelated, course=other_course, semester="T1"),
            Parent(student=own, name="本班虚构家长", phone="000-4011", email="own@example.invalid", relationship="guardian"),
            Parent(student=course_only, name="外班虚构家长", phone="000-4012", relationship="guardian"),
        ])
        db.session.commit()
        ids = SimpleNamespace(teacher=account.teacher_id, other_teacher=other.teacher_id,
                              own_class=own_class.class_id, other_class=other_class.class_id,
                              own=own.student_id, course_only=course_only.student_id,
                              unrelated=unrelated.student_id, own_course=own_course.course_id,
                              other_course=other_course.course_id)
    assert auth.login("auth_teacher").status_code == 303
    return auth, ids
