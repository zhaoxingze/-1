"""Administrator student archives; existing student self-service is separate."""

from flask import render_template, request, url_for
from flask_login import current_user
from wtforms.fields import SelectChoice
from app.services import parent_service, student_service as service
from app.services.permission_service import require_student_access,role_required
from . import bp
from .archive_forms import ConfirmForm,StatusForm,StudentForm
from .archive_views import STATUS_LABELS,editor,list_params,load,payload,read_id,read_int,references,set_choices


def _student(student_id):
    require_student_access(current_user,student_id)
    return load(service.get_student,student_id)


@bp.get("/students")
@role_required("admin")
def students_list():
    params=list_params();archived=request.args.get("archived","active");class_id=read_id("class_id")
    result=load(service.list_students,**params,class_id=class_id,archived=archived)
    rows=[{"cells":[s.student_no,s.name,s.school_class.class_name if s.school_class else "未分班",STATUS_LABELS[s.status],"已归档" if s.is_archived else "未归档"],
           "detail":url_for("admin.student_detail",student_id=s.student_id),"edit":url_for("admin.student_edit",student_id=s.student_id)} for s in result.items]
    return render_template("admin/list.html",title="学生管理",result=result,rows=rows,headers=["学号","姓名","班级","学籍","档案"],
        new_url=url_for("admin.student_new"),filters="students",options=references("classes"),selected_class=class_id,archived=archived)


@bp.route("/students/new",methods=["GET","POST"])
@role_required("admin")
def student_new():
    form=StudentForm();set_choices(form,"class_id",references("classes")["classes"])
    return editor(form,title="新增学生",operation=lambda:service.create_student(current_user,payload(form,service.EDIT_FIELDS)),
        success_url=lambda s:url_for("admin.student_detail",student_id=s.student_id),back_url=url_for("admin.students_list"),note="新建学籍为在读。档案与登录账号分别管理。")


@bp.get("/students/<int:student_id>")
@role_required("admin")
def student_detail(student_id):
    row=_student(student_id)
    parents=load(parent_service.list_parents,student_id=student_id,page=read_int("parents_page",1))
    return render_template("admin/student_detail.html",student=row,parents=parents,age=service.calculate_age(row.birth_date),status_labels=STATUS_LABELS)


@bp.route("/students/<int:student_id>/edit",methods=["GET","POST"])
@role_required("admin")
def student_edit(student_id):
    row=_student(student_id);form=StudentForm(obj=row);set_choices(form,"class_id",references("classes")["classes"])
    return editor(form,title="编辑学生",operation=lambda:service.update_student(current_user,student_id,payload(form,service.EDIT_FIELDS)),
        success_url=lambda s:url_for("admin.student_detail",student_id=s.student_id),back_url=url_for("admin.student_detail",student_id=student_id))


@bp.route("/students/<int:student_id>/status",methods=["GET","POST"])
@role_required("admin")
def student_status(student_id):
    row=_student(student_id);form=StatusForm()
    form.status.choices=[SelectChoice(value=code,label=STATUS_LABELS[code]) for code in STATUS_LABELS if code in service.STATE_TRANSITIONS[row.status]]
    return editor(form,title="变更学籍状态",operation=lambda:service.change_student_status(current_user,student_id,form.status.data),
        success_url=lambda s:url_for("admin.student_detail",student_id=s.student_id),back_url=url_for("admin.student_detail",student_id=student_id),
        note=f"{row.student_no} · {row.name}，当前学籍：{STATUS_LABELS[row.status]}。"+("无常规后续状态。" if not form.status.choices else "仅可选择现有状态图允许的迁移。"))


def _archive(student_id,archived):
    row=_student(student_id);form=ConfirmForm()
    return editor(form,title="归档学生" if archived else "恢复学生档案",operation=lambda:service.set_student_archived(current_user,student_id,archived),
        success_url=lambda s:url_for("admin.student_detail",student_id=s.student_id),back_url=url_for("admin.student_detail",student_id=student_id),
        note=f"请核对：{row.student_no} · {row.name}。本操作只改变档案归档标记，保留历史记录，不改变学籍或账号启停。")


@bp.route("/students/<int:student_id>/archive",methods=["GET","POST"])
@role_required("admin")
def student_archive(student_id):return _archive(student_id,True)


@bp.route("/students/<int:student_id>/restore",methods=["GET","POST"])
@role_required("admin")
def student_restore(student_id):return _archive(student_id,False)
