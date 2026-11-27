from flask import request, url_for
from flask_login import current_user

from app.admin.archive_views import editor, load
from app.record_views import form_values, page_params, prepare_form, query_filters, record_detail, record_list
from app.services import reward_service as service
from app.services.permission_service import REWARD_READ, REWARD_WRITE, role_required
from . import bp
from .forms import NewRewardForm, RewardForm


@bp.get("/rewards")
@role_required("admin", "teacher")
def rewards():
    filters = query_filters()
    record_type, category = request.args.get("record_type"), request.args.get("category")
    page = load(service.list_rewards, **filters, **page_params(), record_type=record_type, category=category)
    rows = [
        ((row.student.student_no, row.student.name, service.RECORD_TYPES[row.record_type], row.category, row.occurred_on),
         url_for("records.reward_detail", record_id=row.record_id))
        for row in page.items
    ]
    return record_list("奖励与处分", page, ("学号", "姓名", "类型", "类别", "发生日期"), rows, REWARD_READ,
                       {**filters, "record_type": record_type, "category": category}, types=service.RECORD_TYPES,
                       new_url=url_for("records.reward_new", student_id=filters["student_id"]))


@bp.get("/rewards/<int:record_id>")
@role_required("admin", "teacher")
def reward_detail(record_id):
    row = load(service.get_reward, record_id)
    facts = [("学生", f"{row.student.student_no} · {row.student.name}"),
             ("类型", service.RECORD_TYPES[row.record_type]), ("类别", row.category),
             ("发生日期", row.occurred_on), ("事由", row.description)]
    return record_detail("奖惩详情", facts, url_for("records.rewards", student_id=row.student_id),
                         edit_url=url_for("records.reward_edit", record_id=record_id))


@bp.route("/rewards/new", methods=["GET", "POST"])
@role_required("admin", "teacher")
def reward_new():
    form = prepare_form(NewRewardForm(), service.FIELDS, action=REWARD_WRITE)
    return editor(form, title="新增奖惩",
                  operation=lambda: service.create_reward(current_user, form.student_id.data, form_values(form, service.FIELDS)),
                  success_url=lambda row: url_for("records.reward_detail", record_id=row.record_id),
                  back_url=url_for("records.rewards"))


@bp.route("/rewards/<int:record_id>/edit", methods=["GET", "POST"])
@role_required("admin", "teacher")
def reward_edit(record_id):
    row = load(service.get_reward, record_id, write=True)
    form = prepare_form(RewardForm(obj=row), service.FIELDS)
    back_url = url_for("records.reward_detail", record_id=record_id)
    return editor(form, title="编辑奖惩", note=f"{row.student.student_no} · {row.student.name}",
                  operation=lambda: service.update_reward(current_user, record_id, form_values(form, service.FIELDS)),
                  success_url=lambda _: back_url, back_url=back_url)
