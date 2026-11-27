"""Fictional form data and real-CSRF helpers for stage4A only."""

STUDENT_DATA = {"student_no":"CRUD-S1","name":"虚构档案学生","gender":"未指定",
                "birth_date":"2008-02-29","enrollment_date":"2026-09-01","class_id":"0",
                "phone":"000-0000","address":"虚构地址"}
TEACHER_DATA = {"teacher_no":"CRUD-T1","name":"虚构档案教师","phone":"000-0001","email":"teacher@example.invalid"}
CLASS_DATA = {"class_name":"虚构档案班","grade":"演示年级","homeroom_teacher_id":"0"}
PARENT_DATA = {"name":"虚构监护人","relationship":"guardian","phone":"000-0002","email":"parent@example.invalid"}


def submit(auth,path,data):
    return auth.client.post(path,data={"csrf_token":auth.token(path),**data})


def actor(auth):
    from app.extensions import db
    from app.models import User
    return db.session.get(User,auth.ids['auth_admin'])
