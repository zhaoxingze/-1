from flask import url_for
from flask_login import current_user

from app.admin.archive_views import editor, load
from app.record_views import form_values, page_params, prepare_form, query_filters, record_detail, record_list
from app.services import parent_contact_service as service
from app.services.permission_service import PARENT_CONTACT_READ, PARENT_CONTACT_WRITE, role_required
from . import bp
from .forms import ContactForm, NewContactForm


@bp.get("/contacts")
@role_required("admin", "teacher")
def contacts():
    filters = query_filters(parents=True)
    page = load(service.list_contacts, **filters, **page_params())
    rows = [
        ((row.student.student_no, row.student.name, row.contact_person_name or "未保存姓名快照",
          service.METHODS[row.method], row.contacted_at.isoformat(sep=" ", timespec="seconds")),
         url_for("records.contact_detail", contact_id=row.contact_id))
        for row in page.items
    ]
    return record_list("家长联系", page, ("学号", "姓名", "联系人", "联系方法", "联系时间（UTC）"), rows,
                       PARENT_CONTACT_READ, filters,
                       new_url=url_for("records.contact_new", student_id=filters["student_id"]),
                       links=(("模拟通知", url_for("records.notifications", student_id=filters["student_id"])),))


@bp.get("/contacts/<int:contact_id>")
@role_required("admin", "teacher")
def contact_detail(contact_id):
    row = load(service.get_contact, contact_id)
    facts = [("学生", f"{row.student.student_no} · {row.student.name}"),
             ("家长档案 ID", row.parent_id), ("联系人姓名（历史）", row.contact_person_name or "未保存"),
             ("联系人电话（历史）", row.contact_person_phone or "未保存"),
             ("联系方法", service.METHODS[row.method]),
             ("联系时间（UTC）", row.contacted_at.isoformat(sep=" ", timespec="seconds")),
             ("联系内容", row.content), ("联系结果", row.result)]
    return record_detail("家长联系详情", facts, url_for("records.contacts", student_id=row.student_id),
                         edit_url=url_for("records.contact_edit", contact_id=contact_id))


@bp.route("/contacts/new", methods=["GET", "POST"])
@role_required("admin", "teacher")
def contact_new():
    form = prepare_form(NewContactForm(), service.CONTACT_CREATE_FIELDS, action=PARENT_CONTACT_WRITE)
    return editor(
        form, title="新增家长联系", note="可选该学生的家长档案。未关联家长时填写临时联系人姓名。",
        operation=lambda: service.create_contact(current_user, form.student_id.data,
                                                form_values(form, service.CONTACT_CREATE_FIELDS)),
        success_url=lambda row: url_for("records.contact_detail", contact_id=row.contact_id),
        back_url=url_for("records.contacts"),
    )


@bp.route("/contacts/<int:contact_id>/edit", methods=["GET", "POST"])
@role_required("admin", "teacher")
def contact_edit(contact_id):
    row = load(service.get_contact, contact_id, write=True)
    form = prepare_form(ContactForm(obj=row), service.FIELDS)
    back_url = url_for("records.contact_detail", contact_id=contact_id)
    return editor(form, title="编辑家长联系", note=f"{row.student.student_no} · {row.student.name}",
                  operation=lambda: service.update_contact(current_user, contact_id, form_values(form, service.FIELDS)),
                  success_url=lambda _: back_url, back_url=back_url)
