from flask import render_template,request,url_for
from flask_login import current_user
from app.services import class_service as service,student_service
from app.services.permission_service import role_required
from . import bp
from .archive_forms import ClassForm
from .archive_views import STATUS_LABELS,editor,list_params,load,payload,read_int,references,set_choices


@bp.get("/classes")
@role_required("admin")
def classes_list():
    result=load(service.list_classes,**list_params());counts=load(service.student_counts,[c.class_id for c in result.items])
    rows=[{"cells":[c.class_name,c.grade,c.homeroom_teacher.name if c.homeroom_teacher else "未指定",counts.get(c.class_id,0)],"detail":url_for("admin.class_detail",class_id=c.class_id),"edit":url_for("admin.class_edit",class_id=c.class_id)} for c in result.items]
    return render_template("admin/list.html",title="班级管理",headers=["班级名称","年级","班主任","当前关联学生数"],rows=rows,result=result,new_url=url_for("admin.class_new"))


@bp.route("/classes/new",methods=["GET","POST"])
@role_required("admin")
def class_new():
    form=ClassForm();set_choices(form,"homeroom_teacher_id",references("teachers")["teachers"])
    return editor(form,title="新增班级",operation=lambda:service.create_class(current_user,payload(form,service.FIELDS)),success_url=lambda c:url_for("admin.class_detail",class_id=c.class_id),back_url=url_for("admin.classes_list"))


@bp.get("/classes/<int:class_id>")
@role_required("admin")
def class_detail(class_id):
    row=load(service.get_class,class_id)
    students=load(student_service.list_students,class_id=class_id,archived="all",**list_params())
    count=load(service.student_counts,[class_id]).get(class_id,0)
    return render_template("admin/class_detail.html",school_class=row,students=students,student_count=count,status_labels=STATUS_LABELS)


@bp.route("/classes/<int:class_id>/edit",methods=["GET","POST"])
@role_required("admin")
def class_edit(class_id):
    row=load(service.get_class,class_id);form=ClassForm(obj=row);set_choices(form,"homeroom_teacher_id",references("teachers")["teachers"])
    return editor(form,title="编辑班级",operation=lambda:service.update_class(current_user,class_id,payload(form,service.FIELDS)),success_url=lambda c:url_for("admin.class_detail",class_id=c.class_id),back_url=url_for("admin.class_detail",class_id=class_id))
