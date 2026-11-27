import pytest
from sqlalchemy import select
from archive_support import PARENT_DATA,submit,actor


def test_multiple_parents_switch_primary_and_clear_primary(auth):
    from app.extensions import db
    from app.models import Parent
    auth.login();base=f'/admin/students/{auth.student_ids[0]}/parents'
    assert submit(auth,base+'/new',{**PARENT_DATA,'is_primary':'y'}).status_code==303
    assert submit(auth,base+'/new',{**PARENT_DATA,'name':'第二位虚构监护人'}).status_code==303
    with auth.app.app_context():
        rows=db.session.scalars(select(Parent).order_by(Parent.parent_id)).all();first,second=[p.parent_id for p in rows]
    assert submit(auth,base+f'/{second}/primary',{'confirm':'y'}).status_code==303
    with auth.app.app_context():
        assert not db.session.get(Parent,first).is_primary and db.session.get(Parent,second).is_primary
    assert submit(auth,base+f'/{second}/edit',PARENT_DATA).status_code==303
    with auth.app.app_context():assert not any(p.is_primary for p in db.session.scalars(select(Parent)))
    assert '第二位' not in auth.client.get(base+f'/{second}').text
    assert '虚构监护人' in auth.client.get(f'/admin/students/{auth.student_ids[0]}').text


def test_scoped_parent_cannot_be_reassigned_or_read_under_other_student(auth):
    from app.extensions import db
    from app.models import Parent
    auth.login();base=f'/admin/students/{auth.student_ids[0]}/parents'
    response=submit(auth,base+'/new',PARENT_DATA);assert response.status_code==303
    with auth.app.app_context():identity=db.session.scalar(select(Parent.parent_id))
    wrong=f'/admin/students/{auth.student_ids[1]}/parents/{identity}'
    assert auth.client.get(wrong).status_code==404
    # Use a valid token from an owned admin form, not the nonexistent scoped page.
    assert auth.client.post(wrong+'/edit',data={'csrf_token':auth.token(base+f'/{identity}/edit'),**PARENT_DATA}).status_code==404
    assert submit(auth,base+f'/{identity}/edit',{**PARENT_DATA,'student_id':str(auth.student_ids[1])}).status_code==303
    with auth.app.app_context():assert db.session.get(Parent,identity).student_id==auth.student_ids[0]


@pytest.mark.parametrize('override',[{'name':''},{'phone':''},{'relationship':'unknown'},{'email':'broken address'}])
def test_parent_invalid_data(auth,override):
    from app.extensions import db
    from app.models import Parent
    auth.login();base=f'/admin/students/{auth.student_ids[0]}/parents/new'
    assert submit(auth,base,{**PARENT_DATA,**override}).status_code==200
    with auth.app.app_context():assert db.session.scalar(select(Parent)) is None


def test_creating_and_editing_primary_parents_replaces_previous_without_conflict(auth):
    from app.extensions import db
    from app.models import Parent
    auth.login();base=f'/admin/students/{auth.student_ids[0]}/parents'
    for name in ('第一位','第二位'):
        assert submit(auth,base+'/new',{**PARENT_DATA,'name':name,'is_primary':'y'}).status_code==303
    with auth.app.app_context():
        rows=db.session.scalars(select(Parent).order_by(Parent.parent_id)).all()
        first,second=[p.parent_id for p in rows]
        assert [p.is_primary for p in rows]==[False,True]
    assert submit(auth,base+f'/{first}/edit',{**PARENT_DATA,'is_primary':'y'}).status_code==303
    with auth.app.app_context():assert db.session.get(Parent,first).is_primary and not db.session.get(Parent,second).is_primary


def test_global_parent_search_retains_student_selector_and_scope(auth):
    from app.extensions import db
    from app.services.parent_service import create_parent
    with auth.app.app_context():
        for sid in auth.student_ids:create_parent(actor(auth),sid,{**PARENT_DATA,'name':'同名监护人'})
        db.session.commit()
    auth.login();sid=auth.student_ids[0]
    response=auth.client.get(f'/admin/parents?student_id={sid}&q=同名')
    assert response.status_code==200
    assert 'name="student_id"' in response.text
    assert f'value="{sid}" selected' in response.text
    assert 'AUTH-S2</td>' not in response.text
