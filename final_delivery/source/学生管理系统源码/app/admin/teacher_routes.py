from flask import render_template,url_for
from flask_login import current_user
from app.services import teacher_service as service,archive_references
from app.services.permission_service import role_required
from . import bp
from .archive_forms import TeacherForm
from .archive_views import editor,list_params,load,payload,read_int


@bp.get("/teachers")
@role_required("admin")
def teachers_list():
    result=load(service.list_teachers,**list_params())
    rows=[{"cells":[t.teacher_no,t.name,t.phone or "—",t.email or "—"],"detail":url_for("admin.teacher_detail",teacher_id=t.teacher_id),"edit":url_for("admin.teacher_edit",teacher_id=t.teacher_id)} for t in result.items]
    return render_template("admin/list.html",title="教师管理",headers=["教师编号","姓名","联系电话","邮箱"],rows=rows,result=result,new_url=url_for("admin.teacher_new"))


@bp.route("/teachers/new",methods=["GET","POST"])
@role_required("admin")
def teacher_new():
    form=TeacherForm()
    return editor(form,title="新增教师",operation=lambda:service.create_teacher(current_user,payload(form,service.FIELDS)),success_url=lambda t:url_for("admin.teacher_detail",teacher_id=t.teacher_id),back_url=url_for("admin.teachers_list"),note="本操作只创建教师档案，不自动创建登录账号。")


@bp.get("/teachers/<int:teacher_id>")
@role_required("admin")
def teacher_detail(teacher_id):
    teacher=load(service.get_teacher,teacher_id)
    classes,courses=load(archive_references.teacher_relations,teacher_id,class_page=read_int("class_page",1),course_page=read_int("course_page",1))
    return render_template("admin/teacher_detail.html",teacher=teacher,classes=classes,courses=courses)


@bp.route("/teachers/<int:teacher_id>/edit",methods=["GET","POST"])
@role_required("admin")
def teacher_edit(teacher_id):
    teacher=load(service.get_teacher,teacher_id);form=TeacherForm(obj=teacher)
    return editor(form,title="编辑教师",operation=lambda:service.update_teacher(current_user,teacher_id,payload(form,service.FIELDS)),success_url=lambda t:url_for("admin.teacher_detail",teacher_id=t.teacher_id),back_url=url_for("admin.teacher_detail",teacher_id=teacher_id))
