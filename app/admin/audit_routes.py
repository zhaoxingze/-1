from flask import render_template, request

from app.services import audit_query_service as service
from app.services.permission_service import role_required
from . import bp
from .archive_views import load, read_id, read_int


@bp.get("/audit")
@role_required("admin")
def audit_list():
    actor_id = "system" if request.args.get("actor_user_id") == "system" else read_id("actor_user_id")
    filters = {key: request.args.get(key) for key in ("entity_type", "action", "start", "end")}
    filters.update(actor_user_id=actor_id, entity_id=read_id("entity_id"))
    page = load(service.list_audit, **filters, page=read_int("page", 1), per_page=read_int("per_page", 20))
    actors, entities = load(service.audit_options)
    return render_template("admin/audit_list.html", page=page, filters=filters, actors=actors,
                           entities=entities, actions=service.ACTION_LABELS)


@bp.get("/audit/<int:audit_id>")
@role_required("admin")
def audit_detail(audit_id):
    row, before, after = load(service.audit_detail, audit_id)
    return render_template("admin/audit_detail.html", row=row, before=before, after=after,
                           actions=service.ACTION_LABELS)
