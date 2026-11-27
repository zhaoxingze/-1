"""Teacher pages on the existing dashboard Blueprint."""

from flask import abort, render_template, request, url_for
from flask_login import current_user
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, TextAreaField
from wtforms.validators import Length, Optional

from app.admin.archive_views import RELATIONSHIP_LABELS, editor, list_params, load, read_int
from app.services import teacher_student_service as service
from app.services.permission_service import EDIT_CONTACT, PARENT_CONTACT, role_required

from . import bp


class ContactForm(FlaskForm):
    phone = StringField("联系电话", validators=[Optional(), Length(max=30)])
    address = TextAreaField("家庭住址", validators=[Optional(), Length(max=255)])
    submit = SubmitField("保存联系方式")


def _paging():
    return {"page": read_int("page", 1), "per_page": read_int("per_page", 20)}


def _table(title, headers, page, rows, back_url, *, search=False, note=None):
    def page_url(number, page_name):
        return url_for(request.endpoint, per_page=page.per_page,
                       q=request.args.get("q") if search else None,
                       **request.view_args, **{page_name: number})

    return render_template(
        "teacher/table.html", title=title, headers=headers, page=page, rows=rows,
        back_url=back_url, search=search, note=note, page_url=page_url,
    )


@bp.get("/teacher/classes")
@role_required("teacher")
def teacher_classes():
    page = load(service.list_owned_classes, **_paging())
    rows = [
        ((row.class_name, row.grade), url_for("dashboard.teacher_class_students", class_id=row.class_id))
        for row in page.items
    ]
    return _table("负责班级", ("班级", "年级"), page, rows, url_for("dashboard.teacher"))


@bp.get("/teacher/classes/<int:class_id>/students")
@role_required("teacher")
def teacher_class_students(class_id):
    school_class, page = load(service.list_class_students, class_id, **list_params())
    rows = [
        ((row.student_no, row.name), url_for("dashboard.teacher_student", student_id=row.student_id))
        for row in page.items
    ]
    return _table(f"{school_class.class_name} · 学生", ("学号", "姓名"), page, rows,
                  url_for("dashboard.teacher_classes"), search=True)


@bp.get("/teacher/courses")
@role_required("teacher")
def teacher_courses():
    page = load(service.list_owned_courses, **_paging())
    rows = [
        ((row.course_code, row.course_name), url_for("dashboard.teacher_course_students", course_id=row.course_id))
        for row in page.items
    ]
    return _table("授课课程", ("课程编号", "课程名称"), page, rows, url_for("dashboard.teacher"))


@bp.get("/teacher/courses/<int:course_id>/students")
@role_required("teacher")
def teacher_course_students(course_id):
    course, page = load(service.list_course_students, course_id, **list_params())
    rows = [((row.student_no, row.name), None) for row in page.items]
    return _table(f"{course.course_name} · 学生名单", ("学号", "姓名"), page, rows,
                  url_for("dashboard.teacher_courses"), search=True, note="按该课程已有选课记录去重。")


@bp.get("/teacher/students/<int:student_id>")
@role_required("teacher")
def teacher_student(student_id):
    student = load(service.get_homeroom_student, student_id)
    return render_template("teacher/student.html", student=student)


@bp.route("/teacher/students/<int:student_id>/contact", methods=["GET", "POST"])
@role_required("teacher")
def teacher_edit_contact(student_id):
    student = load(service.get_homeroom_student, student_id, action=EDIT_CONTACT)
    if request.method == "POST":
        allowed = {*service.CONTACT_FIELDS, "csrf_token", "submit"}
        if request.files or set(request.form) - allowed:
            abort(400, "表单只接受联系电话和家庭住址。")
        if any(len(request.form.getlist(key)) != 1 for key in request.form):
            abort(400, "表单包含重复字段。")

    form = ContactForm(obj=student)

    def save():
        data = {field: form[field].data for field in service.CONTACT_FIELDS if field in request.form}
        return service.update_student_contact(current_user, student_id, data)

    back_url = url_for("dashboard.teacher_student", student_id=student_id)
    return editor(
        form, title="编辑学生联系方式", operation=save,
        success_url=lambda _: back_url, back_url=back_url,
        note=f"{student.student_no} · {student.name}。联系方式留空可清除。",
    )


@bp.get("/teacher/students/<int:student_id>/parents")
@role_required("teacher")
def teacher_parents(student_id):
    student = load(service.get_homeroom_student, student_id, action=PARENT_CONTACT)
    page = load(service.list_parent_contacts, student_id, **_paging())
    rows = [
        ((row.name, RELATIONSHIP_LABELS[row.relationship], row.phone, row.email or "—",
          "是" if row.is_primary else "否"), None)
        for row in page.items
    ]
    return _table(
        f"{student.name} · 家长联系方式", ("姓名", "关系", "电话", "邮箱", "主要联系人"),
        page, rows, url_for("dashboard.teacher_student", student_id=student_id), note="只读。",
    )
