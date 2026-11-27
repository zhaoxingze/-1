from flask import url_for
from flask_login import current_user

from app.admin.archive_views import editor, load
from app.record_views import form_values, page_params, prepare_form, query_filters, record_detail, record_list
from app.services import parent_contact_service as service
from app.services.permission_service import NOTIFICATION_CREATE, NOTIFICATION_READ, role_required
from . import bp
from .forms import NotificationForm


_SIMULATION_NOTICE = "模拟通知，未实际发送"
_STATUSES = {"simulated": "已创建模拟记录", "prepared": "已准备", "cancelled": "已取消"}


@bp.get("/notifications")
@role_required("admin", "teacher")
def notifications():
    filters = query_filters(parents=True)
    page = load(service.list_notifications, **filters, **page_params())
    rows = [
        ((row.student.student_no, row.student.name, service.CHANNELS[row.channel], _STATUSES[row.status],
          row.created_at.isoformat(sep=" ", timespec="seconds")),
         url_for("records.notification_detail", notification_id=row.notification_id))
        for row in page.items
    ]
    return record_list("模拟通知历史", page, ("学号", "姓名", "渠道", "状态", "创建时间（UTC）"), rows,
                       NOTIFICATION_READ, filters, note=_SIMULATION_NOTICE,
                       new_url=url_for("records.notification_new", student_id=filters["student_id"]))


@bp.get("/notifications/<int:notification_id>")
@role_required("admin", "teacher")
def notification_detail(notification_id):
    row = load(service.get_notification, notification_id)
    recipient = row.recipient_snapshot if isinstance(row.recipient_snapshot, dict) else {}
    address = recipient.get("phone" if row.channel == "sms" else "email")
    facts = [("学生", f"{row.student.student_no} · {row.student.name}"), ("家长档案 ID", row.parent_id),
             ("渠道", service.CHANNELS[row.channel]), ("状态", _STATUSES[row.status]),
             ("收件人（历史）", recipient.get("name")), ("接收地址（历史）", address),
             ("通知内容", row.content), ("创建时间（UTC）", row.created_at.isoformat(sep=" ", timespec="seconds"))]
    return record_detail("模拟通知详情", facts, url_for("records.notifications", student_id=row.student_id),
                         note=_SIMULATION_NOTICE)


@bp.route("/notifications/new", methods=["GET", "POST"])
@role_required("admin", "teacher")
def notification_new():
    form = prepare_form(NotificationForm(), service.NOTIFICATION_FIELDS, action=NOTIFICATION_CREATE)
    return editor(
        form, title="新增模拟通知",
        note=f"{_SIMULATION_NOTICE}。未关联家长时，填写临时收件人姓名及所选渠道对应的手机号或邮箱。",
        operation=lambda: service.simulate_notification(current_user, form.student_id.data,
                                                        form_values(form, service.NOTIFICATION_FIELDS)),
        success_url=lambda row: url_for("records.notification_detail", notification_id=row.notification_id),
        back_url=url_for("records.notifications"),
    )
