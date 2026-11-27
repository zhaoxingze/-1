from flask import render_template,request,url_for
from flask_login import current_user
from app.services import parent_service as service,student_service
from app.services.permission_service import role_required
from . import bp
from .archive_forms import ConfirmForm,ParentForm
from .archive_views import RELATIONSHIP_LABELS,editor,list_params,load,payload,read_id,references


def _list(student_id=None):
    student=load(student_service.get_student,student_id) if student_id is not None else None
    result=load(service.list_parents,student_id=student_id,**list_params())
    rows=[{"cells":[p.student.student_no,p.student.name,p.name,RELATIONSHIP_LABELS[p.relationship],p.phone,p.email or "—","是" if p.is_primary else "否"],"detail":url_for("admin.parent_detail",student_id=p.student_id,parent_id=p.parent_id),"edit":url_for("admin.parent_edit",student_id=p.student_id,parent_id=p.parent_id)} for p in result.items]
    global_list=request.endpoint=="admin.parents_list"
    return render_template("admin/list.html",title=f"{student.name}的家长档案" if student else "家长管理",headers=["学号","学生","家长","关系","电话","邮箱","主要"],rows=rows,result=result,
        new_url=url_for("admin.parent_new",student_id=student_id) if student_id else None,filters="parents" if global_list else None,options=references("students") if global_list else {},selected_student=student_id,
        note="请先选择学生查询，即可新增该学生的家长档案。" if student is None else None)


@bp.get("/parents")
@role_required("admin")
def parents_list():return _list(read_id("student_id"))


@bp.get("/students/<int:student_id>/parents")
@role_required("admin")
def student_parents(student_id):return _list(student_id)


@bp.route("/students/<int:student_id>/parents/new",methods=["GET","POST"])
@role_required("admin")
def parent_new(student_id):
    student=load(student_service.get_student,student_id);form=ParentForm()
    return editor(form,title="新增家长",operation=lambda:service.create_parent(current_user,student_id,payload(form,service.EDIT_FIELDS)),success_url=lambda p:url_for("admin.parent_detail",student_id=student_id,parent_id=p.parent_id),back_url=url_for("admin.student_parents",student_id=student_id),note=f"所属学生：{student.student_no} · {student.name}。主要联系人替换将在同一事务内完成。")


@bp.get("/students/<int:student_id>/parents/<int:parent_id>")
@role_required("admin")
def parent_detail(student_id,parent_id):
    row=load(service.get_parent,student_id,parent_id)
    return render_template("admin/parent_detail.html",parent=row,relationship_labels=RELATIONSHIP_LABELS)


@bp.route("/students/<int:student_id>/parents/<int:parent_id>/edit",methods=["GET","POST"])
@role_required("admin")
def parent_edit(student_id,parent_id):
    row=load(service.get_parent,student_id,parent_id);form=ParentForm(obj=row)
    return editor(form,title="编辑家长",operation=lambda:service.update_parent(current_user,student_id,parent_id,payload(form,service.EDIT_FIELDS)),success_url=lambda p:url_for("admin.parent_detail",student_id=student_id,parent_id=parent_id),back_url=url_for("admin.parent_detail",student_id=student_id,parent_id=parent_id),note=f"所属学生：{row.student.student_no} · {row.student.name}，不能通过本表单改变归属。")


@bp.route("/students/<int:student_id>/parents/<int:parent_id>/primary",methods=["GET","POST"])
@role_required("admin")
def parent_primary(student_id,parent_id):
    row=load(service.get_parent,student_id,parent_id);form=ConfirmForm()
    return editor(form,title="设置主要联系人",operation=lambda:service.set_primary_parent(current_user,student_id,parent_id),success_url=lambda p:url_for("admin.parent_detail",student_id=student_id,parent_id=parent_id),back_url=url_for("admin.parent_detail",student_id=student_id,parent_id=parent_id),note=f"将{row.name}设为{row.student.name}的主要联系人，原主要联系人将取消主要标记，档案仍保留。")
