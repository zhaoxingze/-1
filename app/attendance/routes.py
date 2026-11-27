from flask import render_template, url_for
from flask_login import current_user

from app.admin.archive_views import editor, load
from app.record_views import (
    can_manage_records, filter_values, form_values, page_params, prepare_form, query_filters, record_detail, record_list,
)
from app.services import attendance_service as service
from app.services.permission_service import ATTENDANCE_READ, ATTENDANCE_WRITE, role_required
from app.services.student_record_service import record_options
from . import bp
from .forms import AttendanceForm, NewAttendanceForm


@bp.get("/")
@role_required("admin", "teacher", "student")
def index():
    filters = query_filters(classes=True)
    page = load(service.list_attendance, **filters, **page_params())
    rows = [
        ((row.student.student_no, row.student.name, row.attendance_date, row.period, service.STATUSES[row.status]),
         url_for("attendance.detail", attendance_id=row.attendance_id))
        for row in page.items
    ]
    new_url = url_for("attendance.new", student_id=filters["student_id"]) if can_manage_records() else None
    return record_list("考勤记录", page, ("学号", "姓名", "日期", "节次或时段", "状态"), rows,
                       ATTENDANCE_READ, filters, new_url=new_url,
                       links=(("考勤统计", url_for("attendance.statistics", **filter_values(filters))),))


@bp.get("/statistics")
@role_required("admin", "teacher", "student")
def statistics():
    filters = query_filters(classes=True)
    counts, rate = load(service.attendance_statistics, **filters)
    options = load(record_options, ATTENDANCE_READ, include_classes=True, class_id=filters["class_id"])
    return render_template("attendance/statistics.html", filters=filters, options=options,
                           entries=[(label, counts[status]) for status, label in service.STATUSES.items()],
                           rate=rate, back_url=url_for("attendance.index", **filter_values(filters)))


@bp.get("/<int:attendance_id>")
@role_required("admin", "teacher", "student")
def detail(attendance_id):
    row = load(service.get_attendance, attendance_id)
    facts = [("学生", f"{row.student.student_no} · {row.student.name}"),
             ("考勤日期", row.attendance_date), ("节次或时段", row.period),
             ("考勤状态", service.STATUSES[row.status]), ("备注", row.note)]
    edit_url = url_for("attendance.edit", attendance_id=attendance_id) if can_manage_records() else None
    return record_detail("考勤详情", facts, url_for("attendance.index", student_id=row.student_id), edit_url=edit_url)


@bp.route("/new", methods=["GET", "POST"])
@role_required("admin", "teacher")
def new():
    form = prepare_form(NewAttendanceForm(), service.FIELDS, action=ATTENDANCE_WRITE)
    return editor(form, title="登记考勤",
                  operation=lambda: service.create_attendance(current_user, form.student_id.data,
                                                              form_values(form, service.FIELDS)),
                  success_url=lambda row: url_for("attendance.detail", attendance_id=row.attendance_id),
                  back_url=url_for("attendance.index"))


@bp.route("/<int:attendance_id>/edit", methods=["GET", "POST"])
@role_required("admin", "teacher")
def edit(attendance_id):
    row = load(service.get_attendance, attendance_id, write=True)
    form = prepare_form(AttendanceForm(obj=row), service.FIELDS)
    back_url = url_for("attendance.detail", attendance_id=attendance_id)
    return editor(form, title="编辑考勤", note=f"{row.student.student_no} · {row.student.name}",
                  operation=lambda: service.update_attendance(current_user, attendance_id, form_values(form, service.FIELDS)),
                  success_url=lambda _: back_url, back_url=back_url)
