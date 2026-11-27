"""Forms, filters and navigation shared by the student record Blueprints."""

from flask import request, render_template, url_for
from flask_login import current_user
from flask_wtf import FlaskForm
from wtforms import SelectField, SubmitField
from wtforms.fields import SelectChoice
from wtforms.validators import InputRequired, NumberRange

from app.admin.archive_views import load, read_id, read_int, set_choices, strict_form
from app.services.archive_common import MAX_ID
from app.services.student_record_service import record_options


class RecordForm(FlaskForm):
    submit = SubmitField("保存")


class StudentRecordForm(RecordForm):
    student_id = SelectField("学生", default=0, coerce=int, validate_choice=False,
                             validators=[InputRequired(), NumberRange(min=1, max=MAX_ID, message="请选择学生。")])


def form_choices(labels):
    return [SelectChoice(value=key, label=label) for key, label in labels.items()]


def query_filters(*, classes=False, parents=False):
    filters = {"student_id": read_id("student_id"), "start": request.args.get("start"),
               "end": request.args.get("end")}
    if classes:
        filters["class_id"] = read_id("class_id")
    if parents:
        filters["parent_id"] = read_id("parent_id")
    return filters


def page_params():
    return {"page": read_int("page", 1), "per_page": read_int("per_page", 20)}


def filter_values(filters, **extra):
    return {key: value for key, value in {**filters, **extra}.items() if value not in (None, "")}


def record_list(title, page, headers, rows, action, filters, *, new_url=None, links=(), note=None, types=None):
    options = load(record_options, action, include_classes="class_id" in filters,
                   include_parents="parent_id" in filters, class_id=filters.get("class_id"))
    choices = filter_values(filters, per_page=page.per_page)

    def page_url(number, page_name):
        return url_for(request.endpoint, **choices, **{page_name: number})

    return render_template("records/list.html", title=title, page=page, headers=headers, rows=rows,
                           filters=filters, options=options, types=types, new_url=new_url,
                           links=links, note=note, page_url=page_url)


def record_detail(title, facts, back_url, *, edit_url=None, note=None):
    return render_template("records/detail.html", title=title, facts=facts, back_url=back_url,
                           edit_url=edit_url, note=note)


def prepare_form(form, fields, *, action=None):
    selection = ("student_id",) if "student_id" in form else ()
    strict_form(*selection, *fields)
    if not selection:
        return form
    options = load(record_options, action, include_parents="parent_id" in form)
    form.student_id.choices = [SelectChoice(value=0, label="请选择学生")] + [
        SelectChoice(value=key, label=label) for key, label in options["students"]
    ]
    if request.method == "GET":
        target = read_id("student_id")
        if target in dict(options["students"]):
            form.student_id.data = target
    if "parent_id" in form:
        set_choices(form, "parent_id", options["parents"])
    return form


def form_values(form, fields):
    data = {field: form[field].data for field in fields}
    if data.get("parent_id") == 0:
        data["parent_id"] = None
    return data


def can_manage_records():
    return current_user.role.name in {"admin", "teacher"}
