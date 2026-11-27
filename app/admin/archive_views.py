"""Thin shared view helpers: transactions, form errors, paging and references."""

from flask import abort, current_app, flash, redirect, render_template, request, url_for
from flask_login import current_user
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from wtforms.fields import SelectChoice

from app.extensions import db
from app.services.archive_common import ArchiveValidationError
from app.services.archive_common import MAX_ID
from app.services import archive_references
from . import bp

STATUS_LABELS={"enrolled":"在读","suspended":"休学","graduated":"毕业","withdrawn":"退学"}
RELATIONSHIP_LABELS={"father":"父亲","mother":"母亲","guardian":"监护人","other":"其他"}


@bp.context_processor
def archive_template_helpers():
    def page_url(page,page_name="page"):
        allowed={"q","page","per_page","class_id","archived","student_id","parents_page","class_page","course_page",
                 "role","active","actor_user_id","entity_type","entity_id","action","start","end","semester"}
        values={key:value for key,value in request.args.items() if key in allowed}
        values.update(request.view_args or {});values[page_name]=page
        return url_for(request.endpoint,**values)
    return {"page_url":page_url}


def read_int(name, default=None):
    raw=request.args.get(name)
    if raw is None or raw=="":return default
    if not raw.isascii() or not raw.isdecimal() or len(raw)>10 or not 0<int(raw)<=2147483647:
        abort(400)
    return int(raw)


def read_id(name):
    raw=request.args.get(name)
    if raw is None or raw=="":return None
    if not raw.isascii() or not raw.isdecimal() or len(raw)>19 or not 0<int(raw)<=MAX_ID:
        abort(400)
    return int(raw)


def list_params():
    return {"q":request.args.get("q",""),"page":read_int("page",1),"per_page":read_int("per_page",20)}


def load(callable_,*args,**kwargs):
    try:return callable_(current_user,*args,**kwargs)
    except LookupError:abort(404)
    except PermissionError:abort(403)
    except ArchiveValidationError:abort(400)


def payload(form,fields):
    data={field:form[field].data for field in fields}
    for field in ("class_id","homeroom_teacher_id"):
        if field in data and data[field]==0:data[field]=None
    return data


def strict_form(*fields):
    if request.method == "POST":
        allowed = {*fields, "csrf_token", "submit"}
        if request.files or any(key not in allowed or len(values) != 1 for key, values in request.form.lists()):
            abort(400)


def editor(form,*,title,operation,success_url,back_url,note=None):
    error=None;status=200
    if form.validate_on_submit():
        try:
            result=operation()
            db.session.commit()
        except ArchiveValidationError as exc:
            db.session.rollback()
            if exc.field and exc.field in form:
                form[exc.field].errors=list(form[exc.field].errors)+[str(exc)]
            else:error=str(exc)
        except LookupError:
            db.session.rollback();abort(404)
        except PermissionError:
            db.session.rollback();abort(403)
        except IntegrityError:
            db.session.rollback();status=409
            current_app.logger.warning("archives.write_conflict")
            error="保存失败，数据存在冲突；本次修改已回滚，请核对后重试。"
        except (SQLAlchemyError,ValueError):
            db.session.rollback();status=503
            current_app.logger.error("archives.write_failed")
            error="保存失败，本次修改已回滚，请稍后重试。"
        else:
            flash("保存成功。","success")
            return redirect(success_url(result),code=303)
    return render_template("admin/form.html",form=form,title=title,error=error,back_url=back_url,note=note),status


def references(kind):
    return {kind:load(archive_references.reference_options,kind)}


def set_choices(form,field,choices):
    form[field].choices=[SelectChoice(value=value,label=label) for value,label in [(0,"暂不指定")]+choices]
    if request.method=="GET" and form[field].data is None:form[field].data=0
